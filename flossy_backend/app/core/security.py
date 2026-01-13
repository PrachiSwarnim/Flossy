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
    jwks_client = get_jwks_client()
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    # Added leeway=60 to handle "token is not yet valid" errors due to clock drift
    return jwt.decode(
        token, 
        signing_key.key, 
        algorithms=["RS256"], 
        issuer=config.CLERK_ISSUER, 
        options={"verify_aud": False},
        leeway=60
    )
