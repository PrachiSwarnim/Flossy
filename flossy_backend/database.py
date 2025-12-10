from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

# --- Load environment variables ---
load_dotenv()

# --- Database Configuration ---
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("❌ DATABASE_URL is not set in your .env file")

# --- SQLAlchemy Engine Setup ---
# For SQLite, add `connect_args={"check_same_thread": False}`
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

# --- Session Factory ---
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Metadata and Base ---
metadata = MetaData()
Base = declarative_base(metadata=metadata)


def get_db():
    """Dependency to provide a clean session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize the database and create tables if they don't exist."""
    from models import Base  # imported here to avoid circular import
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized and tables created (if not existing).")
