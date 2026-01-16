from fastapi import APIRouter
import requests
from app.core import config

router = APIRouter()

@router.get("/health")
def health_check():
    clerk_reachable = False
    try:
        res = requests.get(config.JWKS_URL, timeout=5)
        if res.status_code == 200:
            clerk_reachable = True
    except Exception as e:
        print(f"Connectivity check failed: {e}")

    return {
        "status": "ok",
        "clerk_reachable": clerk_reachable,
        "jwks_url": config.JWKS_URL
    }
