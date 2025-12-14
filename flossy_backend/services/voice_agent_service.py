import os
import json
import asyncio
from datetime import datetime, timedelta
import dateutil.parser
from typing import Optional

import assemblyai as aai
from elevenlabs import generate, stream as elevenlabs_stream
from openai import OpenAI

from database import SessionLocal
from models import User, Patient, Appointment

# Knowledge Base
KNOWLEDGE_BASE = """
[PRICING]
- Routine Check-up: ₹500
- Scaling & Cleaning: ₹1,500+
- Dental Implants: ₹25,000+
- Root Canal: ₹4,000-8,000
- Braces/Invisalign: ₹35,000+

[POST-OP CARE]
- No vigorous rinsing for 24 hours
- Apply ice for swelling
- Soft diet for 24 hours

[SYMPTOMS]
- Toothache: Rinse with salt water, book ASAP
- Bleeding Gums: Book cleaning
- Knocked-out Tooth: Keep in milk, come within 1 hour
"""

def get_system_prompt(user_name: str) -> str:
    return f"""You are FlossyAI, a warm dental receptionist at Smile Artists Dental Studio.

CURRENT USER: {user_name}

KNOWLEDGE BASE:
{KNOWLEDGE_BASE}

RULES:
1. Be warm, professional, and concise
2. Address the user by their name ({user_name})
3. Answer questions using the knowledge base
4. For booking: collect date, time, phone, reason
5. When you have all details, respond with: "Let me book that for you. [BOOK: date=YYYY-MM-DD, time=HH:MM, phone=XXXXXXXXXX, reason=...]"
6. After booking, say "All set! Your appointment is confirmed."
"""

class VoiceAgentService:
    def __init__(self, user_email: str, user_name: str, websocket):
        # API Keys
        aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        
        # User info
        self.user_email = user_email
        self.user_name = user_name
        self.websocket = websocket
        
        # Conversation history with personalized prompt
        self.conversation = [
            {"role": "system", "content": get_system_prompt(user_name)},
        ]
    
    async def process_audio(self, audio_data: bytes):
        """Process incoming audio from browser"""
        try:
            # Send to AssemblyAI for transcription
            # Note: For WebSocket, we'll use a different approach
            # This is a placeholder for the actual implementation
            pass
        except Exception as e:
            print(f"Audio processing error: {e}")
    
    async def process_transcript(self, transcript_text: str):
        """Process transcribed text and generate response"""
        try:
            # Add user message
            self.conversation.append({"role": "user", "content": transcript_text})
            
            # Send to WebSocket
            await self.websocket.send_json({
                "type": "transcript",
                "role": "user",
                "text": transcript_text
            })
            
            # Get OpenAI response
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=self.conversation
            )
            
            ai_response = response.choices[0].message.content
            
            # Check for booking
            if "[BOOK:" in ai_response:
                booking_result = await self.handle_booking(ai_response)
                ai_response = booking_result
            
            # Add assistant message
            self.conversation.append({"role": "assistant", "content": ai_response})
            
            # Send transcript to WebSocket
            await self.websocket.send_json({
                "type": "transcript",
                "role": "assistant",
                "text": ai_response
            })
            
            # Generate and stream audio
            await self.generate_audio(ai_response)
            
        except Exception as e:
            print(f"Transcript processing error: {e}")
            await self.websocket.send_json({
                "type": "error",
                "message": str(e)
            })
    
    async def generate_audio(self, text: str):
        """Generate TTS audio and stream to client"""
        try:
            # Generate audio with ElevenLabs
            audio_generator = generate(
                api_key=self.elevenlabs_api_key,
                text=text,
                voice="Rachel",
                model="eleven_monolingual_v1",
                stream=True
            )
            
            # Stream audio chunks to WebSocket
            for chunk in audio_generator:
                if chunk:
                    import base64
                    audio_base64 = base64.b64encode(chunk).decode('utf-8')
                    await self.websocket.send_json({
                        "type": "audio",
                        "data": audio_base64
                    })
            
            # Signal audio complete
            await self.websocket.send_json({
                "type": "audio_complete"
            })
            
        except Exception as e:
            print(f"TTS error: {e}")
    
    async def handle_booking(self, ai_response: str) -> str:
        """Extract booking details and create appointment"""
        try:
            # Parse booking details
            booking_part = ai_response.split("[BOOK:")[1].split("]")[0]
            details = {}
            for item in booking_part.split(","):
                key, value = item.split("=")
                details[key.strip()] = value.strip()
            
            if not self.user_email:
                return "I'm sorry, you need to be logged in to book appointments."
            
            db = SessionLocal()
            try:
                # Find user
                user = db.query(User).filter(User.email == self.user_email).first()
                if not user:
                    return "I couldn't find your account."
                
                # Find patient
                patient = db.query(Patient).filter(Patient.user_id == user.id).first()
                if not patient:
                    return "I couldn't find your patient profile."
                
                # Parse datetime
                try:
                    dt_str = f"{details['date']} {details['time']}"
                    appt_dt = dateutil.parser.parse(dt_str)
                except:
                    appt_dt = datetime.now() + timedelta(days=1)
                
                # Get doctor from database (first dentist user)
                doctor_user = db.query(User).filter(User.role == "dentist").first()
                if doctor_user:
                    # Format doctor name from email
                    email_prefix = doctor_user.email.split("@")[0]
                    clean = email_prefix.replace(".", " ")
                    proper = " ".join([p.capitalize() for p in clean.split()])
                    doctor_name = f"Dr. {proper}"
                else:
                    doctor_name = "Dr. Available"
                
                # Create appointment
                appt = Appointment(
                    patient_id=patient.id,
                    datetime=appt_dt,
                    status="scheduled",
                    doctor_name=doctor_name,
                    reason=details.get('reason', 'General checkup')
                )
                db.add(appt)
                db.commit()
                
                # Notify via WebSocket
                await self.websocket.send_json({
                    "type": "booking_success",
                    "appointment": {
                        "id": appt.id,
                        "datetime": appt_dt.isoformat(),
                        "doctor": "Dr. Smith",
                        "reason": appt.reason
                    }
                })
                
                formatted_time = appt_dt.strftime("%A, %B %d at %I:%M %p")
                return f"Perfect, {self.user_name}! Your appointment with {doctor_name} is confirmed for {formatted_time}. We'll see you then!"
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"Booking error: {e}")
            return "I'm sorry, there was an issue booking your appointment."
