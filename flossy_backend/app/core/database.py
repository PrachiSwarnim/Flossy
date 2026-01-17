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
        print(f"⚠️ Warning: Could not connect to database.")
        print(f"Error: {e}")
        print("💡 Falling back to SQLite for stability.")
        return create_engine("sqlite:///./sql_app.db", connect_args={"check_same_thread": False})
    
    # If already sqlite or fallback
    connect_args = {"check_same_thread": False} if "sqlite" in url else {}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)

# Global session and engine holders
_engine = None
_SessionLocal = None
_DB_INITIALIZED = False

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_resilient_engine(DATABASE_URL)
    return _engine

def get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal

Base = declarative_base()

def get_db():
    global _DB_INITIALIZED
    if not _DB_INITIALIZED:
        try:
            init_db()
            _DB_INITIALIZED = True
        except Exception as e:
            print(f"⚠️ Lazy DB init error: {e}")
            
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()

def init_db():
    global _DB_INITIALIZED
    """
    Lightweight DB initialization with auto-migrations.
    """
    print("🛠️ Starting DB initialization and migrations...")
    try:
        from app import models as _ 
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        
        inspector = inspect(engine)
        
        with engine.connect() as conn:
            # 1. Check 'patients' table
            try:
                if inspector.has_table('patients'):
                    columns = [c['name'].lower() for c in inspector.get_columns('patients')]
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
                if inspector.has_table('appointments'):
                    columns = [c['name'].lower() for c in inspector.get_columns('appointments')]
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
                if inspector.has_table('prescriptions'):
                    columns = [c['name'].lower() for c in inspector.get_columns('prescriptions')]
                    if "diagnosis" not in columns:
                        conn.execute(text("ALTER TABLE prescriptions ADD COLUMN diagnosis TEXT;"))
                        conn.execute(text("ALTER TABLE prescriptions ADD COLUMN treatment_plan TEXT;"))
                        conn.execute(text("ALTER TABLE prescriptions ADD COLUMN recommendations TEXT;"))
                    try: conn.execute(text("ALTER TABLE prescriptions ALTER COLUMN details DROP NOT NULL;"))
                    except: pass 
            except Exception as e: print(f"Migration error (prescriptions): {e}")
            
            # 4. Check 'invoice_items' table for 'discount'
            try:
                if inspector.has_table('invoice_items'):
                    columns = [c['name'].lower() for c in inspector.get_columns('invoice_items')]
                    if "discount" not in columns:
                        conn.execute(text("ALTER TABLE invoice_items ADD COLUMN discount FLOAT DEFAULT 0.0;"))
            except Exception as e: print(f"Migration error (invoice_items discount): {e}")
            
            # 5. Check 'invoices' table
            try:
                if inspector.has_table('invoices'):
                    columns = [c['name'].lower() for c in inspector.get_columns('invoices')]
                    if "currency" not in columns:
                        conn.execute(text("ALTER TABLE invoices ADD COLUMN currency VARCHAR(10) DEFAULT 'INR';"))
            except Exception as e: print(f"Migration error (invoices): {e}")

            # 6. Seed Treatment Catalog
            try:
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
                        conn.execute(text("UPDATE treatment_catalog SET default_cost = 500 WHERE name = 'Root Canal Treatment (RCT)'"))
                        conn.execute(text("UPDATE treatment_catalog SET default_cost = 800 WHERE name = 'Tooth Extraction (Simple)'"))
            except Exception as e:
                print(f"Migration/Seed error (catalog): {e}")

            conn.commit()
            print("✅ DB Schema auto-migration check complete.")
            
    except Exception as e:
        print(f"(!) init_db migration error: {e}")
