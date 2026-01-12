import os
import psycopg2
from dotenv import load_dotenv

def migrate():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not found in .env")
        return

    db_url = db_url.replace("postgresql+psycopg2://", "postgresql://")
    print(f"Connecting to {db_url}...")
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Check if discount column exists
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'invoice_items' AND column_name = 'discount'")
        if cur.fetchone():
            print("Column 'discount' already exists in 'invoice_items'.")
        else:
            print("Adding 'discount' column to 'invoice_items'...")
            cur.execute("ALTER TABLE invoice_items ADD COLUMN discount FLOAT DEFAULT 0.0")
            conn.commit()
            print("Column added successfully.")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    migrate()
