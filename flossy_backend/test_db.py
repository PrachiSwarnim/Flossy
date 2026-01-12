import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL").replace("postgresql+psycopg2://", "postgresql://")
print(f"Testing connection to {db_url}")
try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'invoice_items'")
    cols = [r[0] for r in cur.fetchall()]
    print(f"Columns: {cols}")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
