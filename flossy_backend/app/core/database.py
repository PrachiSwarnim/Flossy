import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Render provides DATABASE_URL as env var
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Use SQLite for local dev if not set
    DATABASE_URL = "sqlite:///./sql_app.db"

# Required fix for PostgreSQL SSL on Render
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

def create_resilient_engine(url):
    try:
        # Test connection for Postgres/MySQL to avoid startup crash
        if "sqlite" not in url:
            temp_engine = create_engine(url, connect_args={"connect_timeout": 5})
            with temp_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return temp_engine
    except Exception as e:
        print(f"⚠️ Warning: Could not connect to {url.split('@')[-1] if '@' in url else url}")
        print(f"Error: {e}")
        print("💡 Falling back to SQLite for stability.")
        return create_engine("sqlite:///./sql_app.db", connect_args={"check_same_thread": False})
    
    # If already sqlite or fallback
    connect_args = {"check_same_thread": False} if "sqlite" in url else {}
    return create_engine(url, connect_args=connect_args)

engine = create_resilient_engine(DATABASE_URL)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Lightweight DB initialization. This is safe to run on low-memory platforms.
    Avoid heavy operations here.
    """
    try:
        # Import models here to ensure they are registered with Base
        from app import models as _ # Trigger registration

        
        Base.metadata.create_all(bind=engine)
        
        inspector = inspect(engine)
        
        with engine.connect() as conn:
            # 1. Check 'patients' table
            try:
                columns = [c['name'].lower() for c in inspector.get_columns('patients')]
                if columns:
                    if "age" not in columns:
                        conn.execute(text("ALTER TABLE patients ADD COLUMN age INTEGER;"))
                    if "source" not in columns:
                        conn.execute(text("ALTER TABLE patients ADD COLUMN source VARCHAR(50) DEFAULT 'website';"))
                    if "is_archived" not in columns:
                        conn.execute(text("ALTER TABLE patients ADD COLUMN is_archived INTEGER DEFAULT 0;"))
                    if "sex" not in columns:
                        conn.execute(text("ALTER TABLE patients ADD COLUMN sex VARCHAR(10);"))
            except Exception as e: print(f"Migration error (patients): {e}")
            
            # 2. Check 'appointments' table
            try:
                columns = [c['name'].lower() for c in inspector.get_columns('appointments')]
                if columns:
                    if "reminder_level" not in columns:
                        conn.execute(text("ALTER TABLE appointments ADD COLUMN reminder_level INTEGER DEFAULT 0;"))
                    if "follow_up_reason" not in columns:
                        conn.execute(text("ALTER TABLE appointments ADD COLUMN follow_up_reason TEXT;"))
                    if "follow_up_status" not in columns:
                        conn.execute(text("ALTER TABLE appointments ADD COLUMN follow_up_status VARCHAR(50);"))
                    if "denial_reason" not in columns:
                        conn.execute(text("ALTER TABLE appointments ADD COLUMN denial_reason TEXT;"))
            except Exception as e: print(f"Migration error (appointments): {e}")

            # 3. Check 'prescriptions' table
            try:
                columns = [c['name'].lower() for c in inspector.get_columns('prescriptions')]
                if columns:
                    if "diagnosis" not in columns:
                        conn.execute(text("ALTER TABLE prescriptions ADD COLUMN diagnosis TEXT;"))
                        conn.execute(text("ALTER TABLE prescriptions ADD COLUMN treatment_plan TEXT;"))
                        conn.execute(text("ALTER TABLE prescriptions ADD COLUMN recommendations TEXT;"))
                    # SQLite doesn't support DROP NOT NULL well, but we can try or skip
                    try: conn.execute(text("ALTER TABLE prescriptions ALTER COLUMN details DROP NOT NULL;"))
                    except: pass 
            except Exception as e: print(f"Migration error (prescriptions): {e}")
            
            # 4. Ensure Prescription IDs start from 1000
            try:
                # Check if table is empty
                res = conn.execute(text("SELECT COUNT(*) FROM prescriptions")).scalar()
                if res == 0:
                    # Insert dummy row with ID 999 so next is 1000
                    p_res = conn.execute(text("SELECT id FROM patients LIMIT 1")).scalar()
                    pid = p_res
                    if not pid:
                        # Create dummy patient
                        conn.execute(text("INSERT INTO patients (name, phone, source) VALUES ('System', '0000000000', 'system')"))
                        pid = conn.execute(text("SELECT id FROM patients WHERE phone='0000000000'")).scalar()
                    
                    if pid:
                        conn.execute(text(f"INSERT INTO prescriptions (id, patient_id, details) VALUES (999, {pid}, 'System Offset');"))
                        print("Initialized Prescription ID sequence to start from 1000.")
            except Exception as e: print(f"Sequence init error: {e}")

            # 4. Check 'invoice_items' table for 'discount'
            try:
                columns = [c['name'].lower() for c in inspector.get_columns('invoice_items')]
                if columns and "discount" not in columns:
                    conn.execute(text("ALTER TABLE invoice_items ADD COLUMN discount FLOAT DEFAULT 0.0;"))
            except Exception as e: print(f"Migration error (invoice_items discount): {e}")
            
            # 4. Check 'invoices' table
            try:
                columns = [c['name'].lower() for c in inspector.get_columns('invoices')]
                if columns and "currency" not in columns:
                    conn.execute(text("ALTER TABLE invoices ADD COLUMN currency VARCHAR(10) DEFAULT 'INR';"))
            except Exception as e: print(f"Migration error (invoices): {e}")

            # 5. Seed Treatment Catalog
            try:
                # Check if table exists (it should due to create_all)
                if inspector.has_table("treatment_catalog"):
                    res_tc = conn.execute(text("SELECT count(*) FROM treatment_catalog")).fetchone()
                    if res_tc and res_tc[0] == 0:
                        print("🌱 Seeding Treatment Catalog...")
                        treatments = [
                            ("Dental Scaling & Polishing", 1500, "Preventive"),
                            ("Root Canal Treatment (RCT)", 500, "Endodontic"),
                            ("Dental Filling (Composite)", 2500, "Restorative"),
                            ("Tooth Extraction (Simple)", 800, "Surgical"),
                            ("Dental Crown (PFM)", 5500, "Restorative"),
                            ("Dental Crown (Zirconia)", 12000, "Restorative"),
                            ("Teeth Whitening", 8000, "Cosmetic"),
                            ("Dental Implant", 35000, "Surgical"),
                            ("Deep Cleaning (Scaling \u0026 Root Planing)", 3000, "Preventive")
                        ]
                        for name, cost, cat in treatments:
                            conn.execute(text("INSERT INTO treatment_catalog (name, default_cost, category) VALUES (:n, :c, :cat)"), {"n": name, "c": cost, "cat": cat})
                    else:
                        # Force update for specific requested prices
                        conn.execute(text("UPDATE treatment_catalog SET default_cost = 500 WHERE name = 'Root Canal Treatment (RCT)'"))
                        conn.execute(text("UPDATE treatment_catalog SET default_cost = 800 WHERE name = 'Tooth Extraction (Simple)'"))
            except Exception as e:
                print(f"Migration/Seed error (catalog): {e}")

            conn.commit()
            print("(OK) DB Schema auto-migration check complete.")
            
    except Exception as e:
        print(f"(!) init_db migration error: {e}")
        # At minimum ensure tables exist
        try:
             Base.metadata.create_all(bind=engine)
             print("DB tables ensured (basic init_db).")
        except: pass
