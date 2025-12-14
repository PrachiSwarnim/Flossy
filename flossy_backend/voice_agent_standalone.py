import os
import json
import asyncio
from datetime import datetime, timedelta
import dateutil.parser
from dotenv import load_dotenv

import assemblyai as aai
from elevenlabs import generate, stream
from openai import OpenAI

from database import SessionLocal
from models import User, Patient, Appointment

load_dotenv()

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

SYSTEM_PROMPT = f"""You are FlossyAI, a warm dental receptionist at Smile Artists Dental Studio.

KNOWLEDGE BASE:
{KNOWLEDGE_BASE}

RULES:
1. Be warm, professional, and concise
2. Answer questions using the knowledge base
3. For booking: collect date, time, phone, reason
4. When you have all details, say "Let me book that for you" and I'll handle it
5. After booking, say "All set! Your appointment is confirmed."

IMPORTANT: When user provides booking details, respond with:
"Let me book that for you. [BOOK: date=YYYY-MM-DD, time=HH:MM, phone=XXXXXXXXXX, reason=...]"
"""

class FlossyAI_Assistant:
    def __init__(self, user_email=None, user_name="Guest"):
        # API Keys
        aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        
        # User info
        self.user_email = user_email
        self.user_name = user_name
        
        # Transcriber
        self.transcriber = None
        
        # Conversation history
        self.full_transcript = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

    # Step 2: Real-Time Transcription with AssemblyAI
    def start_transcription(self):
        self.transcriber = aai.RealtimeTranscriber(
            sample_rate=16000,
            on_data=self.on_data,
            on_error=self.on_error,
            on_open=self.on_open,
            on_close=self.on_close,
            end_utterance_silence_threshold=1000
        )
        
        self.transcriber.connect()
        microphone_stream = aai.extras.MicrophoneStream(sample_rate=16000)
        self.transcriber.stream(microphone_stream)
    
    def stop_transcription(self):
        if self.transcriber:
            self.transcriber.close()
            self.transcriber = None
    
    def on_open(self, session_opened: aai.RealtimeSessionOpened):
        print(f"🎤 Session ID: {session_opened.session_id}")
    
    def on_data(self, transcript: aai.RealtimeTranscript):
        if not transcript.text:
            return
        
        if isinstance(transcript, aai.RealtimeFinalTranscript):
            self.generate_ai_response(transcript)
        else:
            print(transcript.text, end="\r")
    
    def on_error(self, error: aai.RealtimeError):
        print(f"❌ Error: {error}")
    
    def on_close(self):
        pass
    
    # Step 3: Pass real-time transcript to OpenAI
    def generate_ai_response(self, transcript):
        self.stop_transcription()
        
        self.full_transcript.append({"role": "user", "content": transcript.text})
        print(f"\n👤 Patient: {transcript.text}")
        
        # Call OpenAI
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=self.full_transcript
        )
        
        ai_response = response.choices[0].message.content
        
        # Check if booking is requested
        if "[BOOK:" in ai_response:
            booking_result = self.handle_booking(ai_response)
            ai_response = booking_result
        
        self.generate_audio(ai_response)
        
        self.start_transcription()
        print(f"\n🎤 Listening...")
    
    # Step 4: Generate audio with ElevenLabs
    def generate_audio(self, text):
        self.full_transcript.append({"role": "assistant", "content": text})
        print(f"\n🤖 FlossyAI: {text}")
        
        audio_stream = generate(
            api_key=self.elevenlabs_api_key,
            text=text,
            voice="Rachel",
            stream=True
        )
        
        stream(audio_stream)
    
    # Booking Handler
    def handle_booking(self, ai_response):
        """Extract booking details and create appointment"""
        try:
            # Parse booking details from AI response
            # Format: [BOOK: date=2024-01-15, time=10:00, phone=1234567890, reason=checkup]
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
                    return "I couldn't find your account. Please sign up first."
                
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
                
                # Create appointment
                appt = Appointment(
                    patient_id=patient.id,
                    datetime=appt_dt,
                    status="scheduled",
                    doctor_name="Dr. Smith",
                    reason=details.get('reason', 'General checkup')
                )
                db.add(appt)
                db.commit()
                
                formatted_time = appt_dt.strftime("%A, %B %d at %I:%M %p")
                return f"Perfect! Your appointment is confirmed for {formatted_time}. We'll see you then!"
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"Booking error: {e}")
            return "I'm sorry, there was an issue booking your appointment. Please try again."

# Main
if __name__ == "__main__":
    print("🦷 Welcome to Smile Artists Dental Studio")
    print("=" * 50)
    
    # Get user info (in production, this would come from your auth system)
    user_email = input("Enter your email (or press Enter for guest mode): ").strip()
    user_name = input("Enter your name: ").strip() or "Guest"
    
    # Initialize assistant
    assistant = FlossyAI_Assistant(
        user_email=user_email if user_email else None,
        user_name=user_name
    )
    
    # Start conversation
    greeting = f"Hi {user_name}! I'm Flossy, your dental assistant at Smile Artists. How can I help you today?"
    assistant.generate_audio(greeting)
    assistant.start_transcription()
