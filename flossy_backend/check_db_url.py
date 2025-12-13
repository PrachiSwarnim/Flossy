from dotenv import load_dotenv
import os

load_dotenv()
# Write to file to avoid stdout buffering issues
with open("db_url.txt", "w") as f:
    f.write(os.getenv("DATABASE_URL") or "NOT_SET")
