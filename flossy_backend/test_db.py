import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")
print(f"Testing connection to: {db_url}")

try:
    # Set a 5-second timeout
    engine = create_engine(db_url, connect_args={"connect_timeout": 5} if "postgresql" in db_url else {})
    with engine.connect() as conn:
        res = conn.execute(text("SELECT 1"))
        print("SUCCESS: Connection successful!")
except Exception as e:
    print(f"ERROR: Connection failed: {e}")
