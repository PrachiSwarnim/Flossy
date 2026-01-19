# 🤖 Flossy AI Implementation Documentation

## Project Overview

**Flossy** is an AI-powered dental clinic management system for **Smile Artists Dental Studio**. The system leverages multiple AI/ML technologies to provide intelligent automation, personalized patient interactions, clinical decision support, and voice-based appointment booking.

---

## Table of Contents

1. [AI Components Overview](#ai-components-overview)
2. [FlossyAI Voice Agent](#1-flossyai-voice-agent)
3. [Reinforcement Learning (LinUCB Contextual Bandit)](#2-reinforcement-learning-linucb-contextual-bandit)
4. [Doctor AI Assistant (RAG System)](#3-doctor-ai-assistant-rag-system)
5. [AI Triage System](#4-ai-triage-system)
6. [Symptom Clustering System](#5-symptom-clustering-system)
7. [Smart Reminder System](#6-smart-reminder-system)
8. [Visit Summarization](#7-visit-summarization)
9. [Patient Chatbot](#8-patient-chatbot)
10. [Text-to-Speech (TTS)](#9-text-to-speech-tts)
11. [Speech-to-Text (STT)](#10-speech-to-text-stt)
12. [Multi-Provider LLM Architecture](#11-multi-provider-llm-architecture)
13. [Vector Embeddings & Semantic Search](#12-vector-embeddings--semantic-search)
14. [Technologies Summary](#13-technologies-summary)
15. [Database Schema for AI](#14-database-schema-for-ai)
16. [Quality Metrics & Monitoring](#15-quality-metrics--monitoring)

---

## AI Components Overview

| Component | Technology | Purpose | File Location |
|-----------|------------|---------|---------------|
| FlossyAI Voice Agent | Gemini 2.0 + WebSocket | Real-time voice receptionist | `agent_server.py` |
| Doctor AI Assistant | RAG + LinUCB Bandit | Clinical query answering | `app/api/v1/ai/router.py` |
| Patient Chatbot | RAG + Knowledge Base | Patient-facing chat | `app/api/v1/ai/router.py` |
| AI Triage System | LLM Structured Output | Urgent case prioritization | `app/api/v1/ai/router.py` |
| Smart Reminders | Gemini Content Generation | Personalized notifications | `app/reminders/__init__.py` |
| Symptom Clustering | FAISS + Embeddings | Semantic symptom analysis | `symptom_kb.py` |
| Visit Summarization | LLM JSON Output | Clinical note transformation | `app/api/v1/ai/router.py` |
| Text-to-Speech | ElevenLabs API | Natural voice synthesis | `app/services/tts.py` |
| Speech-to-Text | Groq Whisper | Voice transcription | `agent_server.py` |

---

## 1. FlossyAI Voice Agent

### Purpose
A real-time voice AI receptionist that handles patient calls, answers questions about pricing and symptoms, and books appointments through natural conversation.

### File: `flossy_backend/agent_server.py`

### Technology Stack

| Component | Technology | Why This Choice |
|-----------|------------|-----------------|
| **LLM** | Google Gemini 2.0 Flash | Fast inference, native function calling, good at following instructions |
| **Speech-to-Text** | Groq Whisper Large v3 | Fastest STT API available, free tier, excellent accuracy |
| **Text-to-Speech** | ElevenLabs API | Most natural-sounding voices, low latency streaming |
| **Transport** | WebSocket | Real-time bidirectional audio streaming |
| **Function Calling** | Gemini Native Tools | Structured tool invocation for database operations |

### Key Features

#### a) Real-Time Voice Processing
```python
# Audio is streamed via WebSocket and processed in chunks
@app.websocket("/ws/agent")
async def agent_ws_endpoint(ws: WebSocket):
    await ws.accept()
    while True:
        message = await ws.receive()
        if "bytes" in message:
            # Process audio chunks
            transcript = await groq_stt([audio_chunk])
            response = await process_conversation_turn(transcript)
            await send_bot(ws, response)
```

**Why WebSocket?** 
- Enables real-time, low-latency audio streaming
- Bidirectional communication for simultaneous speaking/listening
- Maintains persistent connection for conversation context

#### b) Gemini Function Calling (Tool Use)
```python
# Define tools that the AI can call
check_availability = types.Tool(
    function_declarations=[types.FunctionDeclaration(
        name="check_availability",
        description="Check if a time slot is available",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "date_str": types.Schema(type=types.Type.STRING),
                "time_str": types.Schema(type=types.Type.STRING)
            }
        )
    )]
)

book_appointment = types.Tool(
    function_declarations=[types.FunctionDeclaration(
        name="book_appointment",
        description="Book an appointment for a patient",
        parameters=types.Schema(...)
    )]
)
```

**Why Gemini Function Calling?**
- Native support for structured tool invocation
- AI decides when to call tools based on conversation context
- Reliable JSON parameter extraction
- No prompt engineering needed for tool selection

#### c) Contextual Knowledge Base
```python
KNOWLEDGE_BASE = """
[PRICING]
- Routine Check-Up: Rs. 500
- Root Canal Treatment: Rs. 4000 - Rs. 8000
- Dental Implant (per tooth): Rs. 25,000 - Rs. 45,000
...

[SYMPTOMS]
- Toothache: Rinse with warm salt water...
- Sensitivity: Use desensitizing toothpaste...

[PREVENTIVE_CARE]
- Brush twice daily with fluoride toothpaste
- Floss once daily
...
"""
```

**Why Static Knowledge Base?**
- Consistent, accurate information about clinic services
- No hallucination risk for pricing/policies
- Fast retrieval without database queries
- Easy to update and maintain

---

## 2. Reinforcement Learning (LinUCB Contextual Bandit)

### Purpose
Dynamically optimizes AI responses by learning the best prompt templates, temperatures, and models based on user interactions and feedback.

### Files: 
- `flossy_backend/contextual_bandit.py`
- `flossy_backend/rl_core.py`

### Algorithm: LinUCB (Linear Upper Confidence Bound)

**Why LinUCB?**
- Handles exploration vs exploitation tradeoff efficiently
- Works well with high-dimensional context vectors (embeddings)
- Online learning - improves with each interaction
- No labeled training data required

### Mathematical Foundation

```
For each action a:
    UCB_score(a) = θ_a^T * x + α * sqrt(x^T * A_a^{-1} * x)
    
Where:
- θ_a = A_a^{-1} * b_a (learned coefficients)
- x = context vector (user query embedding)
- α = exploration parameter
- A_a = d×d matrix (accumulated outer products)
- b_a = d-dimensional vector (accumulated rewards)
```

### Implementation

```python
class LinUCB:
    def __init__(self, bandit_name: str, actions: List[int], d: int, alpha: float = 1.0):
        self.bandit_name = bandit_name
        self.actions = list(actions)
        self.d = d  # embedding dimension (768)
        self.alpha = alpha  # exploration parameter
        self._load_state()

    def choose(self, x_context: np.ndarray, eps: float = 0.1):
        """
        Choose an action using UCB with epsilon-greedy exploration.
        """
        # Epsilon-greedy exploration
        if random.random() < eps:
            return random.choice(self.actions), {}

        # Calculate UCB scores for each action
        scores = {}
        for a in self.actions:
            A = self.state[a]["A"]
            b = self.state[a]["b"]
            A_inv = np.linalg.inv(A)
            theta = A_inv.dot(b)
            
            # UCB score = exploitation + exploration bonus
            score = theta.dot(x_context) + self.alpha * np.sqrt(x_context.dot(A_inv).dot(x_context))
            scores[a] = score
        
        return max(scores, key=lambda k: scores[k]), scores

    def update(self, action_id: int, x_context: np.ndarray, reward: float):
        """
        Update the bandit with observed reward.
        """
        A = self.state[action_id]["A"]
        b = self.state[action_id]["b"]
        
        # Ridge regression update
        self.state[action_id]["A"] = A + np.outer(x_context, x_context)
        self.state[action_id]["b"] = b + reward * x_context
        
        self._persist_action(action_id)
```

### Action Space (What the Bandit Optimizes)

```python
PROMPT_VARIANTS = [
    # Prompt 1: Direct and factual
    """You are FlossyAI Doctor Assistant.
    Answer the question directly and factually...""",
    
    # Prompt 2: Crisp and medically safe
    """Act as FlossyAI Medical Assistant.
    Keep responses crisp, medically safe...""",
    
    # Prompt 3: Concise professional
    """You are a concise, professional AI dental consultant..."""
]

TEMPS = [0.0, 0.2, 0.4]           # Temperature settings
CTX_SIZES = [1, 3, 5]             # Number of context chunks to retrieve
MODELS = [
    "models/gemini-2.5-flash",
    "models/gemini-2.5-pro",
    "models/gemini-2.0-flash-lite-001"
]

# Total actions = 3 × 3 × 3 × 3 = 81 combinations
ACTIONS = list(itertools.product(
    range(len(PROMPT_VARIANTS)), 
    TEMPS, 
    CTX_SIZES, 
    range(len(MODELS))
))
```

### Reward Signals

- **Positive reward (+1.0)**: Successful appointment booking
- **Semantic similarity score**: How well the answer matches the query
- **Groundedness score**: How well the answer is grounded in retrieved context

### State Persistence (Database)

```python
class BanditState(Base):
    __tablename__ = "bandit_state"
    id = Column(Integer, primary_key=True)
    bandit_name = Column(String, index=True)
    action_id = Column(Integer, index=True)
    d = Column(Integer)            # embedding dimension
    A_json = Column(Text)          # A matrix as JSON
    b_json = Column(Text)          # b vector as JSON
```

**Why Persist to Database?**
- Maintains learning across server restarts
- Enables offline analysis of bandit performance
- Supports distributed deployment

---

## 3. Doctor AI Assistant (RAG System)

### Purpose
Answers clinical questions for dentists using Retrieval-Augmented Generation (RAG) with semantic search over a dental knowledge base.

### File: `flossy_backend/app/api/v1/ai/router.py` → `/doctor_ai/query`

### Architecture

```
User Query
    ↓
Embedding (text-embedding-004)
    ↓
FAISS Vector Search (find similar documents)
    ↓
Retrieved Context (top-k chunks)
    ↓
RL Prompt Selection (LinUCB chooses best prompt/temp/model)
    ↓
LLM Generation (Gemini/Groq)
    ↓
Quality Metrics Calculation
    ↓
Response + Logging
```

### Implementation

```python
@router.post("/doctor_ai/query")
async def doctor_ai(request: Request):
    query = payload.get("query", "").strip()
    
    # 1. Load FAISS index
    index, chunks = load_faiss_index()
    
    # 2. Generate query embedding
    query_emb = np.array(embed_with_client(genai_client, query), dtype=float)
    
    # 3. RL bandit selects best configuration
    if bandit:
        chosen_action_id, scores = bandit.choose(query_emb, eps=0.1)
        prompt_idx, temp, ctx_size, model_idx = ACTIONS[chosen_action_id]
        chosen_prompt = PROMPT_VARIANTS[prompt_idx]
        chosen_model = MODELS[model_idx]
    
    # 4. FAISS semantic search
    D, I = index.search(query_emb.reshape(1, -1), ctx_size)
    context = "\n\n".join(chunks[i] for i in I[0])
    
    # 5. Generate response
    prompt = chosen_prompt.format(doctor=doctor_name, context=context, query=query)
    answer = ai_generate(prompt, temperature=temp, model=chosen_model)
    
    # 6. Calculate quality metrics
    answer_emb = embed_with_client(genai_client, answer)
    semantic_similarity = cos_sim(query_emb, answer_emb)
    groundedness = cos_sim(answer_emb, context_emb)
    
    # 7. Log interaction
    db.add(LLMInteraction(...))
    
    return {"answer": answer, "semantic_similarity": semantic_similarity, ...}
```

### Why RAG?

| Benefit | Explanation |
|---------|-------------|
| **Reduced Hallucination** | Answers grounded in verified knowledge base |
| **Up-to-date Information** | Easy to update knowledge without retraining |
| **Source Attribution** | Can show which documents informed the answer |
| **Domain Specificity** | Focused on dental/clinical knowledge |
| **Cost Efficiency** | Smaller prompts with relevant context only |

---

## 4. AI Triage System

### Purpose
Analyzes patient symptoms and categorizes urgency for prioritization, helping staff identify emergency cases quickly.

### File: `flossy_backend/app/api/v1/ai/router.py` → `/triage`

### Urgency Classification

| Level | Symptoms | Recommended Action |
|-------|----------|-------------------|
| **Emergency** | Severe pain, uncontrollable bleeding, facial swelling, trauma | Immediate attention |
| **Soon** | Moderate pain, loose crown, sensitivity | Schedule within 24-48h |
| **Routine** | Cleaning, check-up, mild staining | Regular scheduling |

### Implementation

```python
@router.post("/triage")
async def ai_triage(request: Request, db: Session = Depends(get_db)):
    symptoms = payload.get("symptoms", "").strip()
    
    prompt = f"""
    You are a professional dental triage assistant.
    Analyze the following patient symptoms and categorize them.
    
    PATIENT SYMPTOMS: "{symptoms}"
    
    RESPONSE FORMAT (JSON ONLY):
    {{
      "urgency": "emergency" | "soon" | "routine",
      "probable_issue": "string (e.g., Abscess, Cavity)",
      "recommended_dept": "string (e.g., Oral Surgery)",
      "ai_reasoning": "brief clinical explanation",
      "patient_guidance": "what the patient should do now"
    }}
    """
    
    raw_output = ai_generate(prompt)
    triage_data = json.loads(raw_output)
    
    # Save to database
    triage_record = TriageResult(
        patient_id=patient.id,
        symptoms=symptoms,
        urgency=triage_data["urgency"],
        ...
    )
    db.add(triage_record)
    db.commit()
    
    return {"success": True, "triage": triage_data}
```

### Why Structured JSON Output?

- **Consistent format** for frontend rendering
- **Easy database storage** of triage results
- **Actionable recommendations** for staff
- **Audit trail** for clinical decisions

---

## 5. Symptom Clustering System

### Purpose
Clusters similar patient symptoms using vector embeddings and FAISS for intelligent symptom grouping and pattern recognition.

### File: `flossy_backend/symptom_kb.py`

### Architecture

```
Patient Text Input
    ↓
LLM Extraction (extract symptom phrases)
    ↓
Embedding Generation (text-embedding-004)
    ↓
FAISS Search (find similar clusters)
    ↓
Match Found?
    ├─ Yes → Update cluster centroid (moving average)
    └─ No → Create new cluster with LLM-generated metadata
    ↓
Store Example + Return Results
```

### Cluster Metadata Generation

```python
def create_cluster_with_metadata(self, vector: np.ndarray, examples: List[str]):
    prompt = f"""
    Given these patient symptom phrases: {examples}
    Produce a JSON object with fields:
    - canonical_name (short, lowercase)
    - display_name (human friendly)
    - metadata: {{
        causes: [...],
        severity: "1-5",
        urgency: "low/medium/high",
        explanation: "patient-friendly text",
        recommended_action: "..."
      }}
    """
    
    meta_obj = json.loads(ai_generate(prompt))
    
    cluster = SymptomCluster(
        canonical_name=meta_obj["canonical_name"],
        display_name=meta_obj["display_name"],
        metadata=meta_obj["metadata"],
        centroid=vec_to_bytes(vector),
        count=1
    )
    db.add(cluster)
```

### Centroid Update (Online Learning)

```python
def update_cluster_centroid(self, cluster: SymptomCluster, new_vector: np.ndarray):
    """
    Moving average update for cluster centroid.
    """
    old = bytes_to_vec(cluster.centroid)
    n = cluster.count or 1
    
    # Weighted average: (old * n + new) / (n + 1)
    updated = (old * n + new_vector) / (n + 1)
    
    cluster.centroid = vec_to_bytes(updated)
    cluster.count = n + 1
    db.commit()
```

**Why Moving Average?**
- Adapts to new symptom variations over time
- Maintains cluster stability
- No need to recompute from all examples

---

## 6. Smart Reminder System

### Purpose
Sends personalized, Zomato-style quirky SMS reminders at timed intervals using AI-generated messages.

### File: `flossy_backend/app/reminders/__init__.py`

### Reminder Levels

| Level | Time Before Appointment | Message Style |
|-------|------------------------|---------------|
| 0 | Booking confirmation | Welcome message |
| 1 | 10 hours | Friendly reminder |
| 2 | 30 minutes | Urgent reminder |

### AI Message Generation

```python
def generate_quirky_message_gemini(level: int, patient_name: str, time_str: str, 
                                   doctor_name: str, remaining_text: str) -> str:
    prompt = f"""
    You are a quirky, fun, and engaging dental assistant named Flossy, 
    inspired by Zomato's marketing style.
    
    Generate a short, funny, and attention-grabbing SMS for a dental appointment.
    
    Context:
    - Patient Name: {patient_name}
    - Doctor Name: {doctor_name}
    - Appointment Time: {time_str}
    - Time Remaining: {remaining_text}
    - Urgency Level: {level}
    
    Guidelines:
    - Use emojis! 🦷✨
    - Be witty and slightly dramatic but friendly
    - Keep it under 160 characters (SMS limit)
    - Do NOT include any intro like "Here is a message:"
    """
    
    return genai_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    ).text.strip()
```

### SMS Delivery via Twilio

```python
def send_simulated_notification(db: Session, appt: Appointment, level: int):
    msg = generate_quirky_message_gemini(level, patient.name, time_str, ...)
    
    # Send via Twilio
    client = Client(account_sid, auth_token)
    message = client.messages.create(
        body=msg,
        from_=twilio_from,
        to=patient.phone
    )
    
    # Log to database
    log = Interaction(
        patient_id=patient.id,
        channel="sms_sent",
        message=msg,
        created_at=datetime.now(timezone.utc)
    )
    db.add(log)
```

### Background Daemon

```python
async def reminder_daemon():
    """
    Background task running every 60 seconds.
    """
    print("(Clock) Reminder Daemon Started")
    while True:
        await asyncio.to_thread(check_reminders_sync)
        await asyncio.sleep(60)
```

---

## 7. Visit Summarization

### Purpose
Transforms shorthand dentist notes into structured clinical records and patient-friendly summaries.

### File: `flossy_backend/app/api/v1/ai/router.py` → `/summarize_visit`

### Dual Output Format

```python
@router.post("/summarize_visit")
async def summarize_visit(request: Request):
    notes = payload.get("notes", "").strip()
    
    prompt = f"""
    You are a dental clinical documentation assistant.
    Transform the following shorthand dentist notes into two summaries:
    
    1. A formal "Clinical Record" for the dentist's archive
    2. A "Patient-Friendly Summary" in simple terms
    
    DENTIST NOTES: "{notes}"
    
    RESPONSE FORMAT (JSON ONLY):
    {{
      "clinical": "formal clinical narrative...",
      "patient_friendly": "warm, simple explanation...",
      "suggested_follow_up": "recommendation for next visit"
    }}
    """
    
    summary_data = json.loads(ai_generate(prompt))
    return summary_data
```

### Example Transformation

**Input (Dentist Notes):**
```
RCT #36, 3 canals, Ca(OH)2 dressing, temp filling ZOE
```

**Output:**
```json
{
  "clinical": "Root canal therapy was performed on tooth #36 (lower left first molar). Three canals were identified and cleaned. Calcium hydroxide dressing was placed for inter-appointment medication. Temporary filling with zinc oxide eugenol cement.",
  
  "patient_friendly": "We treated your lower left back tooth today. We cleaned out the infected area inside the tooth and placed medication to help it heal. A temporary filling was placed - please avoid chewing hard foods on that side until your next visit.",
  
  "suggested_follow_up": "Return in 1-2 weeks for permanent filling and crown preparation."
}
```

---

## 8. Patient Chatbot

### Purpose
Patient-facing chat assistant that answers questions using the clinic's knowledge base.

### File: `flossy_backend/app/api/v1/ai/router.py` → `/ai_response`

### Knowledge Base Loading

```python
@router.post("/ai_response")
async def ai_response(request: Request):
    # Load clinic knowledge base
    kb_path = "resources/clinic_knowledge.json"
    with open(kb_path, "r") as f:
        KB_DATA = json.load(f)
    
    user_name = user_payload.get("first_name") or "there"
    
    SYSTEM_PROMPT = f"""
    You are Flossy, the intelligent RAG-powered assistant for {KB_DATA['clinic_info']['name']}.
    You are chatting with a patient named {user_name}.
    
    **CRITICAL GUIDELINE:**
    - ALWAYS base your answers on the provided [CLINIC KNOWLEDGE]
    - If you answer from the knowledge base, start with 📚 icon
    - If using general knowledge, state it's general advice
    - Keep responses professional and empathetic (max 3 sentences)
    
    [CLINIC KNOWLEDGE]
    {json.dumps(KB_DATA, indent=2)}
    """
    
    reply = ai_generate(f"{SYSTEM_PROMPT}\n\nUSER: {user_msg}\n\nFLOSSY:")
    
    return {
        "answer": reply,
        "is_grounded": "📚" in reply  # Indicates if answer is from KB
    }
```

### Knowledge Base Structure (`clinic_knowledge.json`)

```json
{
    "clinic_info": {
        "name": "Smile Artists Dental Studio",
        "location": "New Delhi, India",
        "hours": "Mon-Sat: 10:00 AM - 8:00 PM",
        "emergency_policy": "Text our emergency line at +91-9999999999"
    },
    "pricing": {
        "Consultation": "₹500 (Waived if treatment starts same day)",
        "Scaling & Cleaning": "₹1,500 - ₹3,000",
        "Root Canal Treatment": "₹4,500 - ₹8,500"
    },
    "post_op_care": {
        "Extraction": ["Keep gauze for 30-45 mins", "No rinsing for 24h"],
        "Root Canal": ["Don't eat until numbness wears off"]
    },
    "faq": {
        "Does RCT hurt?": "Most patients feel relief after RCT..."
    }
}
```

---

## 9. Text-to-Speech (TTS)

### Purpose
Converts AI text responses to natural-sounding speech for the voice agent.

### File: `flossy_backend/app/services/tts.py`

### ElevenLabs Integration

```python
def stream_text_to_speech(text: str):
    """
    Generates audio from text using ElevenLabs API.
    Streams audio chunks for low-latency playback.
    """
    api_key = os.getenv("ELEVEN_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "ZT9u07TYPVl83ejeLakq")
    model_id = "eleven_flash_v2.5"  # Fast streaming model
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    
    data = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }
    
    response = requests.post(url, json=data, headers=headers, stream=True)
    
    # Stream audio chunks
    for chunk in response.iter_content(chunk_size=1024):
        if chunk:
            yield chunk
```

### Why ElevenLabs?

| Feature | Benefit |
|---------|---------|
| **Natural voices** | Human-like intonation and emotion |
| **Streaming** | Low latency for real-time conversation |
| **Customizable** | Voice cloning for brand consistency |
| **Multilingual** | Hindi/English support |

---

## 10. Speech-to-Text (STT)

### Purpose
Transcribes patient voice input to text for processing by the AI agent.

### Primary: Groq Whisper

```python
async def groq_stt(audio_chunks: List[bytes]) -> str:
    """
    Fast speech-to-text using Groq's Whisper API.
    """
    combined = b"".join(audio_chunks)
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(combined)
        temp_path = f.name
    
    # Transcribe with Groq
    with open(temp_path, "rb") as audio_file:
        transcription = groq_client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=audio_file,
            response_format="text"
        )
    
    return transcription.strip()
```

### Why Groq Whisper?

| Feature | Benefit |
|---------|---------|
| **Speed** | Fastest Whisper inference available |
| **Free tier** | No cost for moderate usage |
| **Accuracy** | State-of-the-art transcription quality |
| **Large v3** | Best model for medical terminology |

### Fallback: Google Cloud Speech

```python
async def google_stt(audio_chunks: List[bytes]) -> str:
    """
    Fallback STT using Google Cloud Speech-to-Text.
    Used when Groq is unavailable.
    """
    from google.cloud import speech
    
    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(content=b"".join(audio_chunks))
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        language_code="en-IN"
    )
    
    response = client.recognize(config=config, audio=audio)
    return response.results[0].alternatives[0].transcript
```

---

## 11. Multi-Provider LLM Architecture

### Purpose
Ensures high availability and cost optimization by using multiple LLM providers with intelligent fallback.

### File: `flossy_backend/app/core/utils.py`, `flossy_backend/app/services/llm_client.py`

### Provider Hierarchy

```
┌─────────────────────────────────────┐
│          User Request               │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│    1. Try Groq (LLaMA 3.3 70B)     │  ← Fast, Free
│        ↓ (on failure)              │
│    2. Try Gemini 2.0 Flash         │  ← Reliable, Paid
│        ↓ (on rate limit)           │
│    3. Return Error Message          │
└─────────────────────────────────────┘
```

### Implementation

```python
GROQ_MODEL = "llama-3.3-70b-versatile"

def ai_generate(prompt, temperature=0.7, model="gemini-2.0-flash", client_override=None):
    # 1. Try Groq First (Faster, Free Tier)
    if groq_client:
        try:
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a helpful dental assistant named Flossy."},
                    {"role": "user", "content": prompt}
                ],
                model=GROQ_MODEL,
                temperature=temperature,
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"⚠️ Groq Error: {e}. Falling back to Gemini...")

    # 2. Fallback to Gemini
    try:
        res = client.models.generate_content(
            model=model,
            contents=prompt,
            config=GenerationConfig(temperature=temperature)
        )
        return res.text.strip()
    except Exception as e:
        print(f"❌ Both AI Providers Failed: {e}")
        return "I apologize, but I am having trouble connecting. Please try again later."
```

### Why This Architecture?

| Provider | Pros | Cons |
|----------|------|------|
| **Groq** | Extremely fast, free tier | Rate limits, fewer models |
| **Gemini** | Reliable, function calling | Slower, costs money |

---

## 12. Vector Embeddings & Semantic Search

### Purpose
Convert text to dense vectors for semantic similarity search, enabling RAG and symptom clustering.

### Embedding Model: `text-embedding-004`

```python
def embed_with_client(genai_client, text: str) -> List[float]:
    """
    Generate 768-dimensional embedding vector.
    """
    resp = genai_client.models.embed_content(
        model="models/text-embedding-004",
        contents=[text]
    )
    return list(resp.embeddings[0].values)
```

### FAISS Vector Store

```python
class FaissManager:
    def __init__(self, dim=768, index_file="symptom_index.faiss"):
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)  # Inner Product similarity
        self._load()
    
    def add(self, vector: np.ndarray, cluster_id: int):
        v = vector.astype("float32").reshape(1, -1)
        faiss.normalize_L2(v)  # Normalize for cosine similarity
        self.index.add(v)
        self.meta["ids"].append(cluster_id)
        self.save()
    
    def search(self, vector: np.ndarray, k=1) -> Tuple[List[float], List[int]]:
        v = vector.astype("float32").reshape(1, -1)
        faiss.normalize_L2(v)
        D, I = self.index.search(v, k)
        return D[0].tolist(), [self.meta["ids"][i] for i in I[0]]
```

### Why FAISS?

| Feature | Benefit |
|---------|---------|
| **Speed** | Millisecond search over millions of vectors |
| **Memory** | Efficient storage and loading |
| **Scalability** | Handles growing knowledge bases |
| **Flexibility** | Multiple index types (flat, IVF, HNSW) |

### Cosine Similarity Calculation

```python
def cos_sim(a: np.ndarray, b: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.
    Returns value between -1 and 1.
    """
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)
```

---

## 13. Technologies Summary

### AI/ML Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| Google Gemini | 2.0 Flash, 2.5 Flash/Pro | Primary LLM for generation |
| Groq LLaMA | 3.3 70B Versatile | Fast inference, fallback LLM |
| Google text-embedding-004 | N/A | 768-dim text embeddings |
| Whisper Large v3 (Groq) | N/A | Speech-to-text |
| ElevenLabs | Flash v2.5 | Text-to-speech |
| FAISS | faiss-cpu | Vector similarity search |
| LinUCB | Custom | Contextual bandit RL |

### Backend Stack

| Technology | Purpose |
|------------|---------|
| FastAPI | Async web framework |
| SQLAlchemy | ORM for database |
| PostgreSQL | Primary database |
| WebSocket | Real-time communication |
| Twilio | SMS notifications |

### Frontend Stack

| Technology | Purpose |
|------------|---------|
| React 19 | UI framework |
| Vite 7 | Build tool |
| Clerk | Authentication |
| TailwindCSS | Styling |

---

## 14. Database Schema for AI

### LLMInteraction (Logging AI Calls)

```sql
CREATE TABLE llm_interactions (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(255) UNIQUE,
    doctor_id VARCHAR(255),
    query TEXT,
    response TEXT,
    context_used TEXT,
    semantic_similarity FLOAT,
    groundedness FLOAT,
    instruction_score FLOAT,
    safety_score FLOAT,
    coherence_score FLOAT,
    accuracy_score FLOAT,
    prompt_variant INTEGER,
    action_id INTEGER,
    temp_used FLOAT,
    model_used VARCHAR(255),
    ctx_size_used INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE
);
```

### TriageResult (Triage Assessments)

```sql
CREATE TABLE triage_results (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER REFERENCES patients(id),
    symptoms TEXT,
    urgency VARCHAR(50),
    probable_issue TEXT,
    recommended_dept VARCHAR(255),
    ai_reasoning TEXT,
    created_at TIMESTAMP WITH TIME ZONE
);
```

### SymptomCluster (Symptom Groups)

```sql
CREATE TABLE symptom_clusters (
    id SERIAL PRIMARY KEY,
    canonical_name VARCHAR(255) UNIQUE,
    display_name VARCHAR(255),
    metadata JSONB,
    centroid BYTEA,  -- 768-dim float32 vector
    count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE
);
```

### BanditState (RL State)

```sql
CREATE TABLE bandit_state (
    id SERIAL PRIMARY KEY,
    bandit_name VARCHAR(255),
    action_id INTEGER,
    d INTEGER,
    A_json TEXT,  -- d×d matrix as JSON
    b_json TEXT   -- d-dim vector as JSON
);
```

---

## 15. Quality Metrics & Monitoring

### Metrics Tracked

| Metric | Description | Range |
|--------|-------------|-------|
| **Semantic Similarity** | Cosine similarity between query and answer embeddings | 0.0 - 1.0 |
| **Groundedness** | How well answer matches retrieved context | 0.0 - 1.0 |
| **Instruction Score** | Adherence to system prompt guidelines | 0.0 - 1.0 |
| **Safety Score** | Medical safety compliance | 0.0 - 1.0 |
| **Coherence Score** | Logical flow of response | 0.0 - 1.0 |

### Metrics API

```python
@router.get("/metrics/llm")
def llm_metrics(db: Session = Depends(get_db)):
    rows = db.query(LLMInteraction).all()
    data = [{
        "request_id": r.request_id,
        "query": r.query,
        "semantic_similarity": r.semantic_similarity,
        "groundedness": r.groundedness,
        "instruction_score": r.instruction_score,
        "safety_score": r.safety_score,
        "coherence_score": r.coherence_score,
        "accuracy_score": r.accuracy_score,
        "timestamp": r.timestamp
    } for r in rows]
    return {"interactions": data}
```

---

## Environment Variables Required

```bash
# LLM Providers
GOOGLE_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key

# TTS
ELEVEN_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=ZT9u07TYPVl83ejeLakq

# Database
DATABASE_URL=postgresql://user:pass@host:5432/flossy

# Authentication
CLERK_SECRET_KEY=your_clerk_secret
CLERK_PUBLISHABLE_KEY=your_clerk_publishable

# Notifications (Optional)
TWILIO_SID=your_twilio_sid
TWILIO_AUTH=your_twilio_auth
TWILIO_FROM=+1234567890
```

---

## Conclusion

Flossy implements a comprehensive AI stack that combines:

1. **Conversational AI** (Voice Agent with Gemini)
2. **Retrieval-Augmented Generation** (Doctor AI, Patient Chatbot)
3. **Reinforcement Learning** (LinUCB for prompt optimization)
4. **Semantic Analysis** (Symptom clustering, embeddings)
5. **Content Generation** (Smart reminders, visit summaries)
6. **Multi-modal AI** (Text, Speech, Voice)

This architecture ensures:
- ✅ **Reliability** through multi-provider fallbacks
- ✅ **Performance** through fast inference (Groq)
- ✅ **Quality** through RAG and grounding
- ✅ **Continuous Improvement** through RL
- ✅ **Scalability** through efficient vector search

---

*Documentation generated on: January 19, 2026*
*Project: Flossy - AI-Powered Dental Clinic Management System*
*Developer: Smile Artists Dental Studio*
