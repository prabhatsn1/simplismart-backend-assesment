from typing import Generator, Optional, Annotated
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.db.session import SessionLocal
from app.models.user import User
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db() -> Generator:
    """
    Dependency to get a database session with proper error handling.
    """
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    finally:
        db.close()

class SessionManager:
    """
    Manages user sessions with timeout and validation.
    """
    def __init__(self):
        self.session_timeout = timedelta(hours=24)
        self._sessions = {}

    def validate_session(self, user_id: int) -> bool:
        """Check if session is valid and not expired."""
        if user_id not in self._sessions:
            return False
        
        last_active = self._sessions[user_id]
        if datetime.utcnow() - last_active > self.session_timeout:
            del self._sessions[user_id]
            return False
        
        return True

    def update_session(self, user_id: int):
        """Update session last activity time."""
        self._sessions[user_id] = datetime.utcnow()

    def clear_session(self, user_id: int):
        """Clear user session."""
        if user_id in self._sessions:
            del self._sessions[user_id]

# Initialize session manager
session_manager = SessionManager()

async def validate_auth(request: Request) -> int:
    """
    Validate authentication and return user ID.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    if not session_manager.validate_session(user_id):
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired"
        )
    
    return user_id

async def get_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[int, Depends(validate_auth)]
) -> User:
    """
    Get and validate current user with proper error handling.
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            session_manager.clear_session(user_id)
            request.session.clear()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user.is_active:
            session_manager.clear_session(user_id)
            request.session.clear()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is inactive"
            )
        
        session_manager.update_session(user_id)
        return user
        
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_current_user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Additional dependency to ensure user is active.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user

async def get_organization_member(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Ensure user belongs to an organization.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to an organization"
        )
    return current_user
