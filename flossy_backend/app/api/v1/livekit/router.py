import os
import json
import uuid
from fastapi import APIRouter, HTTPException, Request, Query
from livekit import api
from core.config import LIVEKIT_API_KEY, LIVEKIT_API_SECRET, LIVEKIT_URL

router = APIRouter()

@router.get("/token")
def get_livekit_token(
    identity: str = Query(default=None), 
    name: str = Query(default="Guest"), 
    email: str = Query(default="")
):
    if not identity:
        identity = f"user_{uuid.uuid4().hex[:6]}"
        
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        raise HTTPException(status_code=500, detail="LiveKit credentials not configured")

    # 2. Create VideoGrant
    grant = api.VideoGrants(
        room_join=True,
        room="flossy-room",
        can_publish=True,
        can_subscribe=True,
        can_publish_data=True,
    )

    # 3. Build Metadata JSON (Crucial for Agent)
    metadata_json = json.dumps({
        "email": email,
        "name": name
    })

    try:
        token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET) \
            .with_identity(identity) \
            .with_name(name) \
            .with_grants(grant) \
            .with_metadata(metadata_json)
        
        return {"accessToken": token.to_jwt(), "url": LIVEKIT_URL}
    except Exception as e:
        print(f"LiveKit Token Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-token")
def generate_token_legacy():
    # Legacy endpoint support if needed
    room_name = f"room-{uuid.uuid4().hex[:8]}"
    participant_identity = f"user-{uuid.uuid4().hex[:6]}"

    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
         raise HTTPException(status_code=500, detail="LiveKit config missing")

    token = api.AccessToken(
        LIVEKIT_API_KEY,
        LIVEKIT_API_SECRET,
    ).with_identity(participant_identity) \
     .with_name(f"Patient-{participant_identity}") \
     .with_grants(
        api.VideoGrants(
            room_join=True,
            room=room_name,
        )
     )

    return {
        "token": token.to_jwt(),
        "roomName": room_name,
    }
