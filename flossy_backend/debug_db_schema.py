from database import engine
import sqlalchemy

def check_schema():
    insp = sqlalchemy.inspect(engine)
    columns = insp.get_columns("appointments")
    col_names = [c["name"] for c in columns]
    print(f"Columns in 'appointments': {col_names}")
    
    if "reminder_level" in col_names:
        print("✅ 'reminder_level' exists.")
    else:
        print("❌ 'reminder_level' is MISSING.")

if __name__ == "__main__":
    check_schema()
