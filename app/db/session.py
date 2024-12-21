from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Define connection parameters directly
USERNAME = "username"
PASSWORD = "your_password"
HOST = "localhost"
PORT = "5432"
DBNAME = "cluster_management"

DATABASE_URL = f"postgresql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}"

# Create the engine and session
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
