"""
Migration script to fix user names in the database.
Corrects first_name and last_name fields for users and patients.

Run this script from the flossy_backend directory:
    python fix_user_names.py
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection - use environment variable or default
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Try to load from .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
        DATABASE_URL = os.getenv("DATABASE_URL")
    except:
        pass

if not DATABASE_URL:
    print("❌ DATABASE_URL not set! Please set the environment variable.")
    print("   Example: set DATABASE_URL=postgresql://user:pass@host:port/db")
    sys.exit(1)

# Known users with correct names
KNOWN_USERS = {
    "prachi.swarnim@gmail.com": {"first_name": "Prachi", "last_name": "Swarnim"},
    "choudhary.shruti01@gmail.com": {"first_name": "Shruti", "last_name": "Choudhary"},
    "prachiswarnim03@gmail.com": {"first_name": "Prachi", "last_name": "Swarnim"},
    "shaguftajawaid1@gmail.com": {"first_name": "Shagufta", "last_name": "Jawaid"},
}

def fix_user_names():
    """Fix user and patient names in the database."""
    print("=" * 60)
    print("  FIX USER NAMES MIGRATION SCRIPT")
    print("=" * 60)
    print()
    
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("📊 Connecting to database...")
        
        # Get all users
        result = session.execute(text("SELECT id, email, first_name, last_name FROM users"))
        users = result.fetchall()
        
        print(f"📋 Found {len(users)} users in database\n")
        
        fixed_users = 0
        fixed_patients = 0
        
        for user in users:
            user_id, email, current_fname, current_lname = user
            email_lower = email.lower().strip() if email else ""
            
            if email_lower in KNOWN_USERS:
                correct_fname = KNOWN_USERS[email_lower]["first_name"]
                correct_lname = KNOWN_USERS[email_lower]["last_name"]
                
                # Check if update needed
                if current_fname != correct_fname or current_lname != correct_lname:
                    print(f"🔧 User ID {user_id}: {email}")
                    print(f"   Current: first_name='{current_fname}', last_name='{current_lname}'")
                    print(f"   Fixing:  first_name='{correct_fname}', last_name='{correct_lname}'")
                    
                    # Update User table
                    session.execute(
                        text("""
                            UPDATE users 
                            SET first_name = :fname, last_name = :lname 
                            WHERE id = :user_id
                        """),
                        {"fname": correct_fname, "lname": correct_lname, "user_id": user_id}
                    )
                    fixed_users += 1
                    
                    # Update Patient table (if linked)
                    full_name = f"{correct_fname} {correct_lname}".strip()
                    patient_result = session.execute(
                        text("SELECT id, name FROM patients WHERE user_id = :user_id"),
                        {"user_id": user_id}
                    )
                    patient = patient_result.fetchone()
                    
                    if patient:
                        patient_id, patient_name = patient
                        print(f"   → Also updating Patient ID {patient_id}: '{patient_name}' → '{full_name}'")
                        session.execute(
                            text("""
                                UPDATE patients 
                                SET name = :name, first_name = :fname, last_name = :lname 
                                WHERE id = :patient_id
                            """),
                            {"name": full_name, "fname": correct_fname, "lname": correct_lname, "patient_id": patient_id}
                        )
                        fixed_patients += 1
                    
                    print()
                else:
                    print(f"✅ User ID {user_id}: {email} - Already correct ({correct_fname} {correct_lname})")
        
        # Commit changes
        session.commit()
        
        print()
        print("=" * 60)
        print(f"  MIGRATION COMPLETE!")
        print(f"  - Fixed {fixed_users} user(s)")
        print(f"  - Fixed {fixed_patients} patient(s)")
        print("=" * 60)
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error during migration: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    fix_user_names()
