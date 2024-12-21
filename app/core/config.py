from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Cluster Management API"
    API_V1_STR: str = "/api/v1"
    
    # Database configuration
    POSTGRES_SERVER: str = os.getenv("PGHOST", "localhost")
    POSTGRES_USER: str = os.getenv("PGUSER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("PGPASSWORD", "")
    POSTGRES_DB: str = os.getenv("PGDATABASE", "cluster_management")
    POSTGRES_PORT: str = os.getenv("PGPORT", "5432")
    
    # Session configuration
    SECRET_KEY: str = "TODO_CHANGE_THIS_SECRET_KEY"  # TODO: Change in production
    SESSION_COOKIE_NAME: str = "session"
    SESSION_MAX_AGE: int = 1800  # 30 minutes in seconds
    
    # Database URL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )

settings = Settings()
