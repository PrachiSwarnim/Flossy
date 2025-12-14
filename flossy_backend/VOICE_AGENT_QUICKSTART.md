# How to Run Voice Agent Dashboard

## Prerequisites

Add these API keys to your `.env` file:
```env
ASSEMBLYAI_API_KEY=your_assemblyai_key
ELEVENLABS_API_KEY=your_elevenlabs_key
OPENAI_API_KEY=your_openai_key
```

## Step 1: Install Dependencies

**Backend:**
```bash
cd flossy_backend
pip install assemblyai elevenlabs openai
```

**Frontend:**
```bash
cd flossy-ui
npm install
```

## Step 2: Start Backend

```bash
cd flossy_backend
uvicorn main:app --reload
```

Backend runs on: `http://localhost:8000`

## Step 3: Start Frontend

```bash
cd flossy-ui
npm run dev
```

Frontend runs on: `http://localhost:5173`

## Step 4: Test Voice Agent

1. Open browser: `http://localhost:5173`
2. Login as a patient
3. Click **"Call Flossy"** button (bottom right)
4. Allow microphone access when prompted
5. Click the microphone button and start talking!

## What You Can Do

- **Ask questions**: "What's the cost of dental implants?"
- **Book appointments**: "I want to book a cleaning for tomorrow at 10 AM"
- **Check symptoms**: "I have a toothache, what should I do?"

## Troubleshooting

**WebSocket connection fails:**
- Check backend is running on port 8000
- Verify you're logged in (JWT token required)

**Microphone not working:**
- Allow microphone permissions in browser
- Check browser console for errors

**No audio playback:**
- Verify `ELEVENLABS_API_KEY` is set
- Check browser audio permissions

**Booking not appearing:**
- Wait 1-2 seconds for instant refresh
- Or wait 10 seconds for auto-poll
- Check backend logs for errors
