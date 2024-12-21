from typing import Generator, Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User

def get_db() -> Generator:
    """
    Dependency to get a database session.
    
    Design decisions:
    - Use a generator to ensure the session is properly closed after use.
    - Handle any potential exceptions during session creation and closing.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Validate the current user from the session.
    
    Design decisions:
    - Extract user_id from the session to identify the current user.
    - Raise appropriate HTTP exceptions for authentication and authorization errors.
    - Ensure the user exists in the database.
    
    Edge cases:
    - Session does not contain user_id.
    - User_id in session does not correspond to any user in the database.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user