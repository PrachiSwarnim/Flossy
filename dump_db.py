import sqlite3
import os

db_path = r"c:\Users\Prachi Swarnim\Desktop\Flossy\flossy_backend\sql_app.db"

if not os.path.exists(db_path):
    print(f"DB NOT FOUND at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Tables: {tables}")
        
        if ('users',) in tables:
            cursor.execute("SELECT * FROM users")
            users = cursor.fetchall()
            print(f"Users found: {len(users)}")
            for u in users:
                print(f"USER: {u}")
        else:
            print("No users table found.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
