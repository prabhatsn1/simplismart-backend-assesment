from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core import deps
from app.schemas.deployment import Deployment, DeploymentCreate
from app.models.user import User
from app.models.deployment import Deployment as DeploymentModel
from app.models.cluster import Cluster

router = APIRouter()

@router.post("/", response_model=Deployment)
def create_deployment(
    *,
    db: Session = Depends(deps.get_db),
    deployment_in: DeploymentCreate,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Create a new deployment and schedule it.
    
    Design Decisions:
    - Ensure the user is part of an organization before creating a deployment.
    - Check if the cluster has sufficient resources for the deployment.
    - Use appropriate error handling to manage edge cases.
    """
    # Check if the user belongs to an organization
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization to create a deployment.")
    
    # Check if the cluster exists and belongs to the user's organization
    cluster = db.query(Cluster).filter(Cluster.id == deployment_in.cluster_id, Cluster.organization_id == current_user.organization_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found or does not belong to the user's organization.")
    
    # Check if the cluster has sufficient resources
    if (cluster.cpu_available < deployment_in.cpu_required or
        cluster.ram_available < deployment_in.ram_required or
        cluster.gpu_available < deployment_in.gpu_required):
        raise HTTPException(status_code=400, detail="Insufficient resources in the cluster.")
    
    # Create the deployment
    try:
        deployment = DeploymentModel(
            name=deployment_in.name,
            docker_image=deployment_in.docker_image,
            cpu_required=deployment_in.cpu_required,
            ram_required=deployment_in.ram_required,
            gpu_required=deployment_in.gpu_required,
            priority=deployment_in.priority,
            cluster_id=deployment_in.cluster_id,
            status=DeploymentStatus.PENDING
        )
        db.add(deployment)
        db.commit()
        db.refresh(deployment)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred while creating the deployment: {str(e)}")
    
    return deployment

@router.get("/", response_model=List[Deployment])
def read_deployments(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Retrieve deployments.
    
    Design Decisions:
    - Only retrieve deployments that belong to the user's organization.
    - Implement pagination with skip and limit parameters.
    """
    try:
        deployments = db.query(DeploymentModel).filter(DeploymentModel.cluster.has(organization_id=current_user.organization_id)).offset(skip).limit(limit).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while retrieving deployments: {str(e)}")
    
    return deployments