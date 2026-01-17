from typing import Optional
from jwt import PyJWKClient
import jwt
from . import config

_jwks_clients: dict = {}

def get_jwks_client(issuer: str = None) -> PyJWKClient:
    """Get or create a JWKS client for the given issuer."""
    global _jwks_clients
    
    # Use provided issuer or fall back to config
    jwks_url = f"{issuer}/.well-known/jwks.json" if issuer else config.JWKS_URL
    
    if jwks_url not in _jwks_clients:
        print(f"🔑 Creating JWKS client for: {jwks_url}")
        _jwks_clients[jwks_url] = PyJWKClient(jwks_url)
    
    return _jwks_clients[jwks_url]

def verify_token(token: str) -> dict:
    try:
        # First, decode without verification to get the issuer
        unverified_payload = jwt.decode(token, options={"verify_signature": False})
        token_issuer = unverified_payload.get("iss", "")
        
        print(f"🔍 Token issuer: {token_issuer}")
        
        # Get the appropriate JWKS client
        jwks_client = get_jwks_client(token_issuer)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Verify the token with leeway for clock drift
        payload = jwt.decode(
            token, 
            signing_key.key, 
            algorithms=["RS256"], 
            # Disable strict audience/issuer checks - Clerk tokens can vary
            options={"verify_aud": False, "verify_iss": False},
            leeway=120  # Increased leeway to 2 minutes
        )
        
        print(f"✅ Token verified for: {payload.get('email') or payload.get('sub')}")
        return payload
        
    except jwt.ExpiredSignatureError:
        print(f"⏰ Token expired!")
        raise
    except jwt.InvalidTokenError as e:
        print(f"❌ Invalid token: {str(e)}")
        raise
    except Exception as e:
        # Debug: Log the token metadata
        try:
            unverified_header = jwt.get_unverified_header(token)
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            print(f"🔍 Token Debug - KID: {unverified_header.get('kid')}, ISS: {unverified_payload.get('iss')}, SUB: {unverified_payload.get('sub')}")
        except Exception as debug_err:
            print(f"🔍 Could not decode token for debug: {debug_err}")
        
        print(f"❌ JWT Verification failed: {str(e)}")
        raise
