import uuid
import json
import logging
import numpy as np
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.dependencies import require_role
from app.core.security import verify_token
from app.core.config import CLERK_SECRET_KEY
from app.models import LLMInteraction, User
from app.core.utils import ai_generate, embed_with_client, cos_sim
from app.services.ai_service import load_faiss_index, get_genai_client, get_bandit_and_meta

router = APIRouter()

@router.post("/doctor_ai/query")
async def doctor_ai(request: Request):
    payload = await request.json()
    query = payload.get("query", "").strip()
    if not query:
        return JSONResponse({"answer": "No query provided."}, status_code=400)

    doctor_name = payload.get("doctor_name", "Doctor")

    # --- Load FAISS index ---
    try:
        index, chunks = load_faiss_index()
    except FileNotFoundError:
        return JSONResponse({"answer": "Knowledge base not available on the server."}, status_code=500)
    except Exception as e:
        return JSONResponse({"answer": f"Error loading KB: {e}"}, status_code=500)

    # --- GenAI lazy ---
    genai_client = get_genai_client()

    # --- RL bandit lazy ---
    bandit, ACTIONS, PROMPT_VARIANTS, MODELS = get_bandit_and_meta()

    # --- Embedding ---
    try:
        query_emb = np.array(embed_with_client(genai_client, query), dtype=float)
    except Exception:
        query_emb = np.zeros(768, dtype=float)

    x_context = query_emb
    if bandit:
        if x_context.shape[0] != bandit.d:
            if x_context.shape[0] > bandit.d:
                x_context = x_context[:bandit.d]
            else:
                pad = np.zeros(bandit.d - x_context.shape[0], dtype=float)
                x_context = np.concatenate([x_context, pad])

        chosen_action_id, scores = bandit.choose(x_context, eps=0.1)
        try:
            prompt_idx, temp, ctx_size, model_idx = ACTIONS[chosen_action_id]
            chosen_prompt_template = PROMPT_VARIANTS[prompt_idx]
            chosen_model = MODELS[model_idx]
        except Exception:
            chosen_prompt_template = "{query}"
            temp = 0.0
            ctx_size = 2
            chosen_model = None
    else:
        chosen_prompt_template = "{query}"
        temp = 0.0
        ctx_size = 2
        chosen_model = None
        chosen_action_id = -1

    qvec = np.array([query_emb], dtype="float32")
    ctx_size = max(1, min(ctx_size, len(chunks)))
    try:
        Dvals, I = index.search(qvec, ctx_size)
        context = "\n\n".join(chunks[i] for i in I[0] if i < len(chunks))
    except Exception:
        context = ""

    prompt = chosen_prompt_template.format(
        doctor=doctor_name,
        context=context,
        query=query
    )

    try:
        answer = ai_generate(prompt, temperature=temp, model=chosen_model, client_override=genai_client)
    except Exception as e:
        print("ai_generate failed:", e)
        answer = "FlossyAI couldn't generate an answer right now."

    try:
        answer_vec = np.array(embed_with_client(genai_client, answer), dtype=float)
    except Exception:
        answer_vec = np.zeros_like(query_emb)

    try:
        context_vec = np.array(embed_with_client(genai_client, context), dtype=float) if context else np.zeros_like(query_emb)
    except Exception:
        context_vec = np.zeros_like(query_emb)

    semantic_similarity = float(cos_sim(query_emb, answer_vec))
    groundedness = float(cos_sim(answer_vec, context_vec))

    request_id = str(uuid.uuid4())

    # Optional: persist logs
    try:
        db = SessionLocal()
        interaction = LLMInteraction(
            request_id=request_id,
            doctor_id=doctor_name,
            query=query,
            response=answer,
            context_used=context,
            semantic_similarity=semantic_similarity,
            groundedness=groundedness,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(interaction)
        db.commit()
        db.close()
    except Exception as e:
        print("DB logging failed:", e)

    return {
        "answer": answer,
        "request_id": request_id,
        "semantic_similarity": semantic_similarity,
        "groundedness": groundedness
    }

@router.post("/ai_response")
async def ai_response(request: Request, user=Depends(require_role("patient"))):
    payload = await request.json()
    user_msg = payload.get("query", "").strip()
    if not user_msg:
        return {"answer": "I didn't receive any message. Could you please repeat that?"}

    # Simplified Text Chat Handler (No function calling tools for now)
    # We load the Knowledge Base text if possible, or use a default one.
    
    KNOWLEDGE_BASE = """
    [PRICING]
    - Routine Check-Up: Rs. 500
    - Scaling and Cleaning: starts at Rs. 1500
    - Dental Implants: starts at Rs. 25000
    - Root Canal Treatment: Rs. 4000 - Rs. 8000
    - Braces/Invisalign: Starts at Rs. 35, 000

    [SYMPTOMS]
    - Toothache: Rinse with warm salt water, avoid sugary and acidic foods.
    - Swollen gums: Gently brush and floss, use warm salt water rinse.
    - Bleeding gums: Gently brush and floss, use warm salt water rinse.
    - Bad breath: Brush and floss regularly, use mouthwash.
    - Tooth sensitivity: Avoid sugary and acidic foods, use fluoride toothpaste.
    - Jaw pain: Gently brush and floss, use warm salt water rinse.
    """

    SYSTEM_PROMPT = f"""
    You are Flossy, the intelligent frontdesk receptionist, for Smile Artists Dental Studio.
    
    **Your Goal:**
    1. Greet the patient warmly.
    2. Answer questions about pricing or symptoms using your Knowledge Base.
    3. Determine if the patient wants to book an appointment.
    
    **Tone:**
    - Professional, empathetic, and concise (1-2 sentences).
    
    [KNOWLEDGE BASE]
    {KNOWLEDGE_BASE}
    """
    
    prompt = f"{SYSTEM_PROMPT}\n\nUSER: {user_msg}\n\nFLOSSY:"
    try:
        reply = ai_generate(prompt)
    except Exception as e:
        print(f"AI Response Error: {e}")
        reply = "I'm having trouble connecting. Please try again or call our front desk."

    return {"answer": reply}

@router.get("/ai_suggestion")
async def ai_suggestion(request: Request, db: Session = Depends(get_db)):
    # This requires a patient role
    user_payload = getattr(request.state, "user", None)
    if not user_payload:
         return {"suggestion": "Welcome to Smile Artists! Since it's your first time here, how about a <b>Routine Check-up</b> to get started?"}
    
    email = (user_payload.get("email") or user_payload.get("email_address") or "").lower()
    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user:
         return {"suggestion": "Welcome! We're glad to have you. Book a consultation today to begin your smile journey."}

    from models import Patient, Appointment
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    
    # Check if new user
    is_new = False
    if patient:
        appts_count = db.query(Appointment).filter(Appointment.patient_id == patient.id).count()
        if appts_count == 0:
            is_new = True
    else:
        is_new = True

    import random
    styles = [
        "quirky and fun",
        "surprising and witty",
        "mind-blowing",
        "winking and energetic",
        "super interesting"
    ]
    chosen_style = random.choice(styles)

    # Instead of suggestions, we now provide "Smile Insights" (Facts)
    prompt = f"Provide one {chosen_style} dental fact that is actually fun to read (max 18 words). Use a witty tone. Format as a single sentence. Return as plain text only, no HTML tags."

    try:
        # High temperature for variety in facts
        fact = ai_generate(f"You are a fun dental historian and health expert with a sparkling personality. {prompt}", temperature=1.0)
    except:
        fact = "Your Tooth Enamel is the hardest substance in your body—even tougher than bone! ✨"

    return {"suggestion": fact}

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
