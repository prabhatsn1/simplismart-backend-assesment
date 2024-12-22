from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from app.core import deps
from app.schemas.deployment import Deployment, DeploymentCreate
from app.models.user import User
from app.models.deployment import Deployment as DeploymentModel, DeploymentStatus
from app.models.cluster import Cluster as ClusterModel
from sqlalchemy import and_

router = APIRouter()

def check_resource_availability(cluster: ClusterModel, deployment: DeploymentCreate) -> bool:
    """Check if cluster has enough resources for deployment."""
    return all([
        cluster.cpu_available >= deployment.cpu_required,
        cluster.ram_available >= deployment.ram_required,
        cluster.gpu_available >= deployment.gpu_required
    ])

def allocate_resources(db: Session, cluster: ClusterModel, deployment: DeploymentCreate) -> bool:
    """Allocate resources from cluster for deployment."""
    cluster.cpu_available -= deployment.cpu_required
    cluster.ram_available -= deployment.ram_required
    cluster.gpu_available -= deployment.gpu_required
    db.add(cluster)
    return True

def deallocate_resources(db: Session, deployment: DeploymentModel):
    """Return resources back to the cluster."""
    cluster = deployment.cluster
    cluster.cpu_available += deployment.cpu_required
    cluster.ram_available += deployment.ram_required
    cluster.gpu_available += deployment.gpu_required
    db.add(cluster)

def find_preemptible_deployments(
    db: Session,
    cluster: ClusterModel,
    required_resources: DeploymentCreate,
    new_priority: int
) -> List[DeploymentModel]:
    """Find lower priority deployments that could be preempted."""
    running_deployments = db.query(DeploymentModel).filter(
        and_(
            DeploymentModel.cluster_id == cluster.id,
            DeploymentModel.status == DeploymentStatus.RUNNING,
            DeploymentModel.priority < new_priority
        )
    ).order_by(DeploymentModel.priority).all()
    
    # Calculate total resources that could be freed
    cpu_available = cluster.cpu_available
    ram_available = cluster.ram_available
    gpu_available = cluster.gpu_available
    to_preempt = []
    
    for deployment in running_deployments:
        cpu_available += deployment.cpu_required
        ram_available += deployment.ram_required
        gpu_available += deployment.gpu_required
        to_preempt.append(deployment)
        
        if all([
            cpu_available >= required_resources.cpu_required,
            ram_available >= required_resources.ram_required,
            gpu_available >= required_resources.gpu_required
        ]):
            return to_preempt
    
    return []

async def preempt_deployments(
    db: Session,
    deployments: List[DeploymentModel]
):
    """Preempt running deployments and free their resources."""
    for deployment in deployments:
        deployment.status = DeploymentStatus.FAILED
        deallocate_resources(db, deployment)
        db.add(deployment)

@router.post("/", response_model=Deployment)
async def create_deployment(
    *,
    db: Session = Depends(deps.get_db),
    deployment_in: DeploymentCreate,
    current_user: User = Depends(deps.get_current_user),
    background_tasks: BackgroundTasks
):
    """
    Create a new deployment with preemption-based scheduling.
    """
    # Verify user's organization owns the cluster
    cluster = db.query(ClusterModel).filter(
        and_(
            ClusterModel.id == deployment_in.cluster_id,
            ClusterModel.organization_id == current_user.organization_id
        )
    ).first()
    
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found or access denied")
    
    # Validate resource requirements
    if any(value < 0 for value in [
        deployment_in.cpu_required,
        deployment_in.ram_required,
        deployment_in.gpu_required
    ]):
        raise HTTPException(status_code=400, detail="Resource requirements cannot be negative")
    
    try:
        # Check resource availability
        if check_resource_availability(cluster, deployment_in):
            # Create deployment with available resources
            deployment = DeploymentModel(
                name=deployment_in.name,
                cluster_id=deployment_in.cluster_id,
                docker_image=deployment_in.docker_image,
                cpu_required=deployment_in.cpu_required,
                ram_required=deployment_in.ram_required,
                gpu_required=deployment_in.gpu_required,
                priority=deployment_in.priority,
                status=DeploymentStatus.PENDING
            )
            
            # Allocate resources and start deployment
            allocate_resources(db, cluster, deployment_in)
            deployment.status = DeploymentStatus.RUNNING
            
            db.add(deployment)
            db.commit()
            db.refresh(deployment)
            return deployment
        
        # If resources unavailable, check for preemption possibilities
        if deployment_in.priority > 0:
            preemptible = find_preemptible_deployments(
                db, cluster, deployment_in, deployment_in.priority
            )
            
            if preemptible:
                # Create new deployment
                deployment = DeploymentModel(
                    name=deployment_in.name,
                    cluster_id=deployment_in.cluster_id,
                    docker_image=deployment_in.docker_image,
                    cpu_required=deployment_in.cpu_required,
                    ram_required=deployment_in.ram_required,
                    gpu_required=deployment_in.gpu_required,
                    priority=deployment_in.priority,
                    status=DeploymentStatus.PENDING
                )
                
                # Preempt lower priority deployments
                await preempt_deployments(db, preemptible)
                
                # Allocate resources and start deployment
                allocate_resources(db, cluster, deployment_in)
                deployment.status = DeploymentStatus.RUNNING
                
                db.add(deployment)
                db.commit()
                db.refresh(deployment)
                return deployment
        
        # If no preemption possible, set to pending
        deployment = DeploymentModel(
            name=deployment_in.name,
            cluster_id=deployment_in.cluster_id,
            docker_image=deployment_in.docker_image,
            cpu_required=deployment_in.cpu_required,
            ram_required=deployment_in.ram_required,
            gpu_required=deployment_in.gpu_required,
            priority=deployment_in.priority,
            status=DeploymentStatus.PENDING
        )
        
        db.add(deployment)
        db.commit()
        db.refresh(deployment)
        return deployment
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating deployment: {str(e)}")

@router.get("/", response_model=List[Deployment])
def list_deployments(
    *,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_user)
):
    """
    List deployments for user's organization.
    """
    try:
        deployments = (
            db.query(DeploymentModel)
            .join(ClusterModel)
            .filter(ClusterModel.organization_id == current_user.organization_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
        return deployments
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving deployments: {str(e)}"
        )

@router.get("/{deployment_id}", response_model=Deployment)
def get_deployment(
    *,
    db: Session = Depends(deps.get_db),
    deployment_id: int,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Get detailed deployment information.
    """
    try:
        deployment = (
            db.query(DeploymentModel)
            .join(ClusterModel)
            .filter(
                and_(
                    DeploymentModel.id == deployment_id,
                    ClusterModel.organization_id == current_user.organization_id
                )
            )
            .first()
        )
        
        if not deployment:
            raise HTTPException(status_code=404, detail="Deployment not found")
            
        return deployment
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving deployment: {str(e)}"
        )
