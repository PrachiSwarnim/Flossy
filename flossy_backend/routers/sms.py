from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from firebase_admin import messaging
from firebase_client import firebase_admin

router = APIRouter()

class NotificationRequest(BaseModel):
    token: str
    title: str
    text: str

@router.post("/send")
def send_notification(request: NotificationRequest):
    try:
        # Create a notification message
        message = messaging.Message(
            notification=messaging.Notification(
                title=request.title,
                body=request.text
            ),
            token=request.token
        )

        # Send it via FCM
        response = messaging.send(message)
        return {"message": "Notification sent successfully!", "response": response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
