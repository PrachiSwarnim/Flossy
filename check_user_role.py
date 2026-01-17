import sys
import os

# Add the backend directory to sys.path
sys.path.append(r"c:\Users\Prachi Swarnim\Desktop\Flossy\flossy_backend")

try:
    from app.core.database import SessionLocal
    from app.models import User
    
    def check_user():
        db = SessionLocal()
        try:
            print("Checking DB for prachi.swarnim@gmail.com...")
            user = db.query(User).filter(User.email.ilike("prachi.swarnim@gmail.com")).first()
            if user:
                print(f"RESULT: User found: ID={user.id}, Email={user.email}, Role={user.role}")
            else:
                print("RESULT: User not found.")
        except Exception as db_e:
            print(f"Database error: {db_e}")
        finally:
            db.close()

    if __name__ == "__main__":
        check_user()
except Exception as e:
    print(f"Script setup error: {e}")
