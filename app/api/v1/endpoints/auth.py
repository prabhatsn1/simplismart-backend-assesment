from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from app.core import deps, security
from app.schemas.user import UserCreate, User
from app.models.user import User as UserModel

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

    # Extract hashed_password value
    hashed_password = user.hashed_password

    # Verify password
    if not verify_password(password, hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    # Set user_id in session
    request.session['user_id'] = user.id

    return {"msg": "Login successful"}

@router.post("/register", response_model=User)
async def register(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserCreate
):
    """
    Register a new user.
    
    Design Decisions:
    - Check if username/email already exists.
    - Hash the password.
    - Create the user in the database.
    - Return the user data.
    """
    # Check if username or email already exists
    if db.query(UserModel).filter(UserModel.username == user_in.username).first() or db.query(UserModel).filter(UserModel.email == user_in.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already registered")

    # Hash the password
    hashed_password = get_password_hash(user_in.password)

    # Create the user in the database
    user = UserModel(
        email=user_in.email,
        username=user_in.username,
        hashed_password=hashed_password,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user

@router.post("/logout")
async def logout(request: Request):
    """
    Logout endpoint to clear the session.
    
    Design Decisions:
    - Clear the user_id from the session.
    """
    request.session.pop('user_id', None)
    return {"msg": "Logout successful"}
