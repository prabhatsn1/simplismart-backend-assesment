from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core import deps
from app.schemas.cluster import Cluster, ClusterCreate
from app.models.user import User
from app.models.cluster import Cluster as ClusterModel

router = APIRouter()

@router.post("/", response_model=Cluster)
def create_cluster(
    *,
    db: Session = Depends(deps.get_db),
    cluster_in: ClusterCreate,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Create a new cluster.
    
    Design Decisions:
    - Ensure the user is part of an organization before creating a cluster.
    - Initialize available resources to the limits provided.
    - Use appropriate error handling to manage edge cases.
    """
    # Check if the user belongs to an organization
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization to create a cluster.")
    
    # Check if the organization ID in the request matches the user's organization
    if cluster_in.organization_id != current_user.organization_id:
        raise HTTPException(status_code=400, detail="Organization ID mismatch.")
    
    # Create the cluster
    try:
        cluster = ClusterModel(
            name=cluster_in.name,
            cpu_limit=cluster_in.cpu_limit,
            ram_limit=cluster_in.ram_limit,
            gpu_limit=cluster_in.gpu_limit,
            cpu_available=cluster_in.cpu_limit,
            ram_available=cluster_in.ram_limit,
            gpu_available=cluster_in.gpu_limit,
            organization_id=cluster_in.organization_id
        )
        db.add(cluster)
        db.commit()
        db.refresh(cluster)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred while creating the cluster: {str(e)}")
    
    return cluster

@router.get("/", response_model=List[Cluster])
def read_clusters(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Retrieve clusters.
    
    Design Decisions:
    - Only retrieve clusters that belong to the user's organization.
    - Implement pagination with skip and limit parameters.
    """
    try:
        clusters = db.query(ClusterModel).filter(ClusterModel.organization_id == current_user.organization_id).offset(skip).limit(limit).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while retrieving clusters: {str(e)}")
    
    return clusters