from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password using bcrypt.
    
    Design decisions:
    - Use passlib's CryptContext for password hashing and verification.
    - Ensure bcrypt is used as the hashing scheme.
    
    Edge cases:
    - Handle invalid or malformed hashed passwords.
    - Ensure the function returns a boolean indicating the verification result.
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        # Handle the case where the hashed password is invalid or malformed
        return False

def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Design decisions:
    - Use passlib's CryptContext for password hashing.
    - Ensure bcrypt is used as the hashing scheme.
    
    Edge cases:
    - Handle potential errors during the hashing process.
    """
    try:
        return pwd_context.hash(password)
    except Exception as e:
        # Handle any unexpected errors during hashing
        raise ValueError("An error occurred while hashing the password.") from e