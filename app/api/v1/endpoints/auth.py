from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from app.core import deps, security
from app.schemas.user import UserCreate, User
from app.models.user import User as UserModel
from app.core.security import verify_password

router = APIRouter()

@router.post("/login")
async def login(
    request: Request,
    response: Response,
    username: str,
    password: str,
    db: Session = Depends(deps.get_db)
):
    """
    Login endpoint using session.
    
    Design Decisions:
    - Find user by username.
    - Verify the provided password against the stored hashed password.
    - Set user_id in session if authentication is successful.
    - Use appropriate error handling to manage edge cases.
    """
    # Find user by username
    user = db.query(UserModel).filter(UserModel.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    # Verify password
    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    # Set user_id in session
    request.session['user_id'] = user.id

    return {"msg": "Login successful"}