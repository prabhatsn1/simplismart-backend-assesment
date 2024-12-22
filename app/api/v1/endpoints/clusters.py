from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core import deps
from app.schemas.cluster import Cluster, ClusterCreate
from app.models.user import User
from app.models.cluster import Cluster as ClusterModel

router = APIRouter()

def validate_resource_limits(cluster_in: ClusterCreate):
    """
    Validate resource limits are non-negative and reasonable.
    """
    if any(value < 0 for value in [cluster_in.cpu_limit, cluster_in.ram_limit, cluster_in.gpu_limit]):
        raise HTTPException(
            status_code=400,
            detail="Resource limits cannot be negative"
        )
    
    # Add reasonable upper limits to prevent errors
    if cluster_in.cpu_limit > 1000:  # Example max 1000 CPU cores
        raise HTTPException(
            status_code=400,
            detail="CPU limit exceeds maximum allowed value"
        )
    
    if cluster_in.ram_limit > 10000:  # Example max 10000 GB RAM
        raise HTTPException(
            status_code=400,
            detail="RAM limit exceeds maximum allowed value"
        )
    
    if cluster_in.gpu_limit > 100:  # Example max 100 GPUs
        raise HTTPException(
            status_code=400,
            detail="GPU limit exceeds maximum allowed value"
        )

@router.post("/", response_model=Cluster)
def create_cluster(
    *,
    db: Session = Depends(deps.get_db),
    cluster_in: ClusterCreate,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Create a new cluster with resource limits.
    """
    # Check if user belongs to an organization
    if not current_user.organization_id:
        raise HTTPException(
            status_code=400,
            detail="User must belong to an organization to create a cluster"
        )
    
    # Verify organization ID matches user's organization
    if cluster_in.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=400,
            detail="Organization ID mismatch"
        )
    
    # Validate resource limits
    validate_resource_limits(cluster_in)
    
    try:
        # Create new cluster with full resource availability
        cluster = ClusterModel(
            name=cluster_in.name,
            organization_id=cluster_in.organization_id,
            cpu_limit=cluster_in.cpu_limit,
            ram_limit=cluster_in.ram_limit,
            gpu_limit=cluster_in.gpu_limit,
            # Initialize available resources equal to limits
            cpu_available=cluster_in.cpu_limit,
            ram_available=cluster_in.ram_limit,
            gpu_available=cluster_in.gpu_limit
        )
        
        db.add(cluster)
        db.commit()
        db.refresh(cluster)
        return cluster
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating cluster: {str(e)}"
        )

@router.get("/", response_model=List[Cluster])
def list_clusters(
    *,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_user)
):
    """
    List all clusters for the user's organization with pagination.
    """
    # Check if user belongs to an organization
    if not current_user.organization_id:
        raise HTTPException(
            status_code=400,
            detail="User must belong to an organization to list clusters"
        )
    
    try:
        clusters = (
            db.query(ClusterModel)
            .filter(ClusterModel.organization_id == current_user.organization_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
        return clusters
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving clusters: {str(e)}"
        )

@router.get("/{cluster_id}", response_model=Cluster)
def get_cluster(
    *,
    db: Session = Depends(deps.get_db),
    cluster_id: int,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Get detailed information about a specific cluster.
    """
    # Check if user belongs to an organization
    if not current_user.organization_id:
        raise HTTPException(
            status_code=400,
            detail="User must belong to an organization to access clusters"
        )
    
    try:
        cluster = db.query(ClusterModel).filter(
            ClusterModel.id == cluster_id,
            ClusterModel.organization_id == current_user.organization_id
        ).first()
        
        if not cluster:
            raise HTTPException(
                status_code=404,
                detail="Cluster not found"
            )
        
        return cluster
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving cluster: {str(e)}"
        )
