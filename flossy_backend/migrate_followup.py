from database import engine
from sqlalchemy import text

def migrate():
    print("Attempting to add follow_up_reason column (PostgreSQL)...")
    with engine.connect() as connection:
        try:
            # PostgreSQL safe column addition
            query = text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='appointments' AND column_name='follow_up_reason') THEN
                    ALTER TABLE appointments ADD COLUMN follow_up_reason TEXT;
                END IF;
            END
            $$;
            """)
            connection.execute(query)
            print("✅ Verified/Added 'follow_up_reason' column to 'appointments'.")
            
        except Exception as e:
            print(f"⚠️ Migration Error: {e}")
            # Fallback for SQLite just in case
            try:
                connection.execute(text("ALTER TABLE appointments ADD COLUMN follow_up_reason TEXT"))
            except:
                pass

        try:
            connection.commit()
        except:
            pass

if __name__ == "__main__":
    migrate()
