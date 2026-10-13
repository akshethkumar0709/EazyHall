import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load environment variables from .env file
load_dotenv()

# FIX: DATABASE_URL is now loaded from the environment variable, not hardcoded.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./campus_booking.db")

# connect_args={"check_same_thread": False} is required for SQLite in
# multithreaded environments like FastAPI.
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
