from fastapi import FastAPI, WebSocket, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from routers.sms import send_notification  # your Firebase or SMS sender
from agent_server import handle_user_utterance_text, handle_user_utterance_voice
from utils.auth import verify_token  # Clerk JWT verifier
import json

app = FastAPI(title="FlossyAI – Smart Dental Assistant")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change to specific domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# ------------------------- CHAT ROUTE -------------------------
@app.post("/chat")
async def chat_route(payload: dict):
    """Handles text-based AI chat requests"""
    user_msg = payload.get("message", "")
    if not user_msg:
        raise HTTPException(status_code=400, detail="Message is empty")

    response_text = await handle_user_utterance_text(user_msg)
    return {"reply": response_text}

# ---------------------- WEBSOCKET VOICE ROUTE ----------------------
@app.websocket("/ws/agent")
async def agent_websocket(ws: WebSocket):
    """Handles live audio + text streaming with the voice agent"""
    await ws.accept()
    try:
        while True:
            data = await ws.receive_text()
            message = json.loads(data)

            if message["type"] == "audio":
                await handle_user_utterance_voice(ws, message["content"])
            elif message["type"] == "text":
                reply = await handle_user_utterance_text(message["content"])
                await ws.send_json({"type": "bot_text", "text": reply})

    except Exception as e:
        print("WebSocket error:", e)
        await ws.close()

# ---------------------- NOTIFICATION ROUTE ----------------------
@app.post("/send")
async def send_notification_route(payload: dict):
    """Send Firebase notification to device"""
    try:
        token = payload["token"]
        title = payload["title"]
        text = payload["text"]
        result = send_notification({"token": token, "title": title, "text": text})
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send notification: {e}")

# ---------------------- DENTIST DASHBOARD ----------------------
@app.get("/dentist", response_class=HTMLResponse)
async def dentist_dashboard(request: Request):
    token = request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        session_info = verify_token(token)
        user_id = session_info.get("sub", "Unknown")
        email = session_info.get("email", "Not available")

        html = f"""
        <html><body style='font-family:Poppins;text-align:center;'>
        <h1>Welcome, Dentist!</h1>
        <p>Authenticated User ID: {user_id}</p>
        <p>Email: {email}</p>
        </body></html>
        """
        return HTMLResponse(content=html)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

# ---------------------- PATIENT DASHBOARD ----------------------
@app.get("/patient", response_class=HTMLResponse)
async def patient_dashboard(request: Request):
    token = request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        session_info = verify_token(token)
        user_id = session_info.get("sub", "Unknown")
        email = session_info.get("email", "Not available")

        html = f"""
        <html><body style='font-family:Poppins;text-align:center;'>
        <h1>Welcome, Patient!</h1>
        <p>Authenticated User ID: {user_id}</p>
        <p>Email: {email}</p>
        </body></html>
        """
        return HTMLResponse(content=html)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
