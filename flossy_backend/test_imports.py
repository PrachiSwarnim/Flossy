try:
    from app.main import app
    print("SUCCESS: app.main.app imported")
except ImportError as e:
    print(f"IMPORT ERROR: {e}")
except Exception as e:
    print(f"OTHER ERROR: {e}")
