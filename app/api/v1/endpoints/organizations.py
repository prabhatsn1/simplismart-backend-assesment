from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core import deps
from app.schemas.organization import Organization, OrganizationCreate
from app.models.user import User
from app.models.organization import Organization as OrganizationModel, OrganizationMember

router = APIRouter()

@router.post("/", response_model=Organization)
def create_organization(
    *,
    db: Session = Depends(deps.get_db),
    organization_in: OrganizationCreate,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Create a new organization.
    
    Design decisions:
    - Ensure that organization names are unique.
    - Validate the input data and handle potential conflicts.
    - Return the created organization object upon success.
    """
    # Check if an organization with the same name already exists
    existing_organization = db.query(OrganizationModel).filter(
        OrganizationModel.name == organization_in.name
    ).first()
    if existing_organization:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An organization with this name already exists."
        )

    # Create the new organization
    organization = OrganizationModel(
        name=organization_in.name,
        description=organization_in.description,
        owner_id=current_user.id
    )
    try:
        db.add(organization)
        db.commit()
        db.refresh(organization)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the organization."
        ) from e

    return organization

@router.post("/{invite_code}/join")
def join_organization(
    *,
    db: Session = Depends(deps.get_db),
    invite_code: str,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Join an organization using an invite code.
    
    Design decisions:
    - Ensure that the invite code is valid.
    - Check if the user is already a member of the organization.
    - Add the user to the organization if the invite code is valid.
    """
    # Find the organization by invite code
    organization = db.query(OrganizationModel).filter(
        OrganizationModel.invite_code == invite_code
    ).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invite code."
        )

    # Check if the user is already a member of the organization
    existing_member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization.id,
        OrganizationMember.user_id == current_user.id
    ).first()
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of the organization."
        )

    # Add the user to the organization
    new_member = OrganizationMember(
        organization_id=organization.id,
        user_id=current_user.id
    )
    try:
        db.add(new_member)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while joining the organization."
        ) from e

    return {"message": "Successfully joined the organization."}