
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from models import User

# Load env variables from .env file
load_dotenv()

# Get DB URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not found in environment!")
    sys.exit(1)

print(f"Connecting to DB: {DATABASE_URL}")

try:
    engine = create_engine(DATABASE_URL)
    SessionLimit = sessionmaker(bind=engine)
    db = SessionLimit()
    
    users = db.query(User).all()
    print(f"Found {len(users)} users:")
    for u in users:
        print(f"ID: {u.id}, Name: {u.full_name}, Email: {u.email}, Role: {u.role}")
        
    db.close()
except Exception as e:
    print(f"Error accessing DB: {e}")
