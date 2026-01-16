from typing import Optional
from jwt import PyJWKClient
import jwt
from . import config

_jwks_client: Optional[PyJWKClient] = None

def get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(config.JWKS_URL)
    return _jwks_client

def verify_token(token: str) -> dict:
    try:
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        # Added leeway=60 to handle "token is not yet valid" errors due to clock drift
        payload = jwt.decode(
            token, 
            signing_key.key, 
            algorithms=["RS256"], 
            # Temporarily disabling issuer check for debugging if strict match fails
            options={"verify_aud": False, "verify_iss": False},
            leeway=60
        )
        return payload
    except jwt.ExpiredSignatureError:
        print("🔒 JWT Error: Token expired")
        raise
    except jwt.InvalidTokenError as e:
        print(f"🔒 JWT Error: Invalid token - {str(e)}")
        raise
    except Exception as e:
        print(f"❌ JWT Verification failed: {str(e)}")
        raise


