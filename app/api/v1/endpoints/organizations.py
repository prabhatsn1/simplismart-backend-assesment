from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core import deps
from app.schemas.organization import Organization, OrganizationCreate
from app.models.organization import Organization as OrganizationModel
from app.models.user import User
import secrets

router = APIRouter()

@router.post("/", response_model=Organization)
def create_organization(
    *,
    db: Session = Depends(deps.get_db),
    organization_in: OrganizationCreate,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Create a new organization and set the current user as a member.
    """
    # Check if user is already in an organization
    if current_user.organization_id:
        raise HTTPException(
            status_code=400,
            detail="User already belongs to an organization"
        )
    
    # Generate a unique invite code
    while True:
        invite_code = secrets.token_urlsafe(8)
        exists = db.query(OrganizationModel).filter(
            OrganizationModel.invite_code == invite_code
        ).first()
        if not exists:
            break
    
    # Create new organization
    db_organization = OrganizationModel(
        name=organization_in.name,
        invite_code=invite_code
    )
    db.add(db_organization)
    db.commit()
    db.refresh(db_organization)
    
    # Add current user to organization
    current_user.organization_id = db_organization.id
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return db_organization
    

@router.post("/{invite_code}/join")
def join_organization(
    *,
    db: Session = Depends(deps.get_db),
    invite_code: str,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Allow a user to join an organization using an invite code.
    """
    # Check if user is already in an organization
    if current_user.organization_id:
        raise HTTPException(
            status_code=400,
            detail="User already belongs to an organization"
        )
    
    # Find organization by invite code
    organization = db.query(OrganizationModel).filter(
        OrganizationModel.invite_code == invite_code
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found"
        )
    
    # Add user to organization
    current_user.organization_id = organization.id
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    
    return {"message": "Successfully joined organization"}
