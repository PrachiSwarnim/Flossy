# Setup Guide - Standalone Voice Agent (Windows)

## Step 1: Install Python Dependencies

```bash
pip install assemblyai[extras]
pip install elevenlabs
pip install openai
pip install pyaudio
```

**Note**: If `pyaudio` fails on Windows, use:
```bash
pip install pipwin
pipwin install pyaudio
```

## Step 2: Add API Keys to .env

Add these to your `.env` file:
```
ASSEMBLYAI_API_KEY=your_assemblyai_key
ELEVENLABS_API_KEY=your_elevenlabs_key
OPENAI_API_KEY=your_openai_key
```

## Step 3: Run the Agent

```bash
python voice_agent_standalone.py
```

## How It Works

1. **AssemblyAI**: Real-time speech-to-text from your microphone
2. **OpenAI**: Generates intelligent responses (GPT-4o-mini)
3. **ElevenLabs**: Converts responses to natural speech
4. **Database**: Books appointments for authenticated users

## No LiveKit Required!

This is a standalone voice agent that runs directly on your machine.
