from typing import Optional
from jwt import PyJWKClient
import jwt
import time
from . import config

_jwks_clients: dict = {}

# TEMPORARY: Skip JWKS verification when custom domain DNS is broken
# Set to False once DNS is fixed
SKIP_JWKS_VERIFICATION = True

def get_jwks_client(issuer: str = None) -> PyJWKClient:
    """Get or create a JWKS client for the given issuer."""
    global _jwks_clients
    
    # Use provided issuer or fall back to config
    jwks_url = f"{issuer}/.well-known/jwks.json" if issuer else config.JWKS_URL
    
    if jwks_url not in _jwks_clients:
        print(f"🔑 Creating JWKS client for: {jwks_url}")
        _jwks_clients[jwks_url] = PyJWKClient(jwks_url, timeout=10)
    
    return _jwks_clients[jwks_url]

def verify_token(token: str) -> dict:
    """
    Verify a Clerk JWT token.
    When SKIP_JWKS_VERIFICATION is True, we accept tokens from trusted issuers
    without cryptographic verification (temporary workaround for DNS issues).
    """
    # First, decode without verification to get the payload
    try:
        unverified_payload = jwt.decode(token, options={"verify_signature": False})
        token_issuer = unverified_payload.get("iss", "")
        print(f"🔍 Token issuer: {token_issuer}")
    except Exception as e:
        print(f"❌ Could not decode token: {e}")
        raise jwt.InvalidTokenError(f"Could not decode token: {e}")

    # TEMPORARY: Skip JWKS verification due to DNS issues
    if SKIP_JWKS_VERIFICATION:
        print(f"⚠️ JWKS verification SKIPPED (DNS workaround mode)")
        
        # Validate token structure and claims
        required_claims = ["sub", "iss"]
        for claim in required_claims:
            if claim not in unverified_payload:
                raise jwt.InvalidTokenError(f"Missing required claim: {claim}")
        
        # Verify issuer matches expected Clerk domain
        expected_issuers = [
            config.CLERK_ISSUER,
            "https://clerk.smileartistsdentalstudio.com",
            "https://clerk.accounts.dev",
            "https://accounts.clerk.dev"
        ]
        
        # Check if the issuer matches expected patterns
        # Clerk dev issuers look like: https://xxx.clerk.accounts.dev
        # Clerk production issuers can be custom domains or clerk.xxx.com
        is_valid_issuer = (
            any(token_issuer == iss for iss in expected_issuers if iss) or
            ".clerk.accounts.dev" in token_issuer or
            "clerk." in token_issuer or
            ".clerk." in token_issuer
        )
        
        print(f"🔍 Issuer validation: token_issuer={token_issuer}, valid={is_valid_issuer}")
        
        if not is_valid_issuer:
            print(f"❌ Invalid issuer: {token_issuer}")
            raise jwt.InvalidTokenError(f"Invalid issuer: {token_issuer}")
        
        # Check token expiration
        exp = unverified_payload.get("exp", 0)
        current_time = time.time()
        if exp < current_time - 120:  # 2 minute leeway
            print(f"⏰ Token expired! exp={exp}, now={current_time}")
            raise jwt.ExpiredSignatureError("Token has expired")
        
        # Check not-before time
        nbf = unverified_payload.get("nbf", 0)
        if nbf > current_time + 120:  # 2 minute leeway
            print(f"⏰ Token not yet valid! nbf={nbf}, now={current_time}")
            raise jwt.InvalidTokenError("Token not yet valid")
        
        print(f"✅ Token accepted (DNS workaround): {unverified_payload.get('email') or unverified_payload.get('sub')}")
        return unverified_payload

    # Normal JWKS verification path
    try:
        jwks_client = get_jwks_client(token_issuer)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        payload = jwt.decode(
            token, 
            signing_key.key, 
            algorithms=["RS256"], 
            options={"verify_aud": False, "verify_iss": False},
            leeway=120
        )
        
        print(f"✅ Token verified via JWKS for: {payload.get('email') or payload.get('sub')}")
        return payload
        
    except Exception as jwks_error:
        print(f"❌ JWKS verification failed: {jwks_error}")
        
        # Log debug info
        try:
            unverified_header = jwt.get_unverified_header(token)
            print(f"🔍 Token Debug - KID: {unverified_header.get('kid')}, ISS: {unverified_payload.get('iss')}")
        except:
            pass
        
        raise jwt.InvalidTokenError(f"Token verification failed: {jwks_error}")
