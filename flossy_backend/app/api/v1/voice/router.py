from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.tts import stream_text_to_speech

router = APIRouter()

class TTSRequest(BaseModel):
    text: str

@router.post("/speak")
async def speak(req: TTSRequest):
    return StreamingResponse(
        stream_text_to_speech(req.text),
        media_type="audio/mp3",
    )

@router.get("/speak-stream")
async def speak_stream(text: str = Query(...)):
    return StreamingResponse(
        stream_text_to_speech(text),
        media_type="audio/mp3",
    )
