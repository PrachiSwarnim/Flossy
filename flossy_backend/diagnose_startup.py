import sys
import os

print("--- DIAGNOSTIC START ---")
try:
    # Add current dir to path just in case
    sys.path.append(os.getcwd())
    
    print("Attempting to import app.main...")
    from app.main import app
    print("✅ Import app.main Successful")
    
    from app.api.v1.api_router import api_router
    print("✅ Import api_router Successful")

except Exception as e:
    print(f"❌ Import Failed: {e}")
    import traceback
    traceback.print_exc()

print("--- DIAGNOSTIC END ---")
