import sys
import os
import traceback

print(f"CWD: {os.getcwd()}")
print(f"Path: {sys.path}")

try:
    import app
    print("✅ 'import app' successful")
    print(f"App pkg: {app}")
except ImportError:
    print("❌ 'import app' FAILED")
    traceback.print_exc()

try:
    from app.main import app as fastapi_app
    print("✅ 'from app.main import app' successful")
except ImportError:
    print("❌ 'from app.main import app' FAILED")
    traceback.print_exc()
except Exception as e:
    print(f"❌ Other error importing app: {e}")
    traceback.print_exc()
