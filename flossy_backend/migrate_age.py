import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not found in .env")
    exit(1)

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    print("Checking for 'age' column in 'patients' table...")
    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='patients' AND column_name='age';"))
    if not result.fetchone():
        print("Column 'age' missing. Adding it now...")
        conn.execute(text("ALTER TABLE patients ADD COLUMN age INTEGER;"))
        conn.commit()
        print("Column 'age' added successfully.")
    else:
        print("Column 'age' already exists.")
