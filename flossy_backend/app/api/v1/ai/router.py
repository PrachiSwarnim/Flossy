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
from app.models import LLMInteraction, User, TriageResult, Patient, Appointment
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
    try:
        if index is not None and len(chunks) > 0:
            ctx_size = max(1, min(ctx_size, len(chunks)))
            Dvals, I = index.search(qvec, ctx_size)
            context = "\n\n".join(chunks[i] for i in I[0] if i < len(chunks))
        else:
            context = ""
    except Exception as e:
        print(f"⚠️ Index search failed: {e}")
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

from app.api.v1.ai.agent_tools import TOOLS_SCHEMA, execute_tool

@router.post("/chat")
async def ai_chat(request: Request, user=Depends(require_role(["dentist", "receptionist", "patient"])), db: Session = Depends(get_db)):
    """
    General chat endpoint for FlossyAI panel in dashboards.
    Works for all authenticated users.
    """
    payload = await request.json()
    message = payload.get("message", "").strip()
    context = payload.get("context", "general")  # "dentist_dashboard", "patient_dashboard", etc.
    
    if not message:
        return {"response": "I didn't receive any message. How can I help you?"}
    
    # Get user info
    user_name = user.first_name or user.email.split("@")[0].title() if user else "there"
    user_role = user.role if user else "user"
    
    # Context-aware system prompts
    if context == "dentist_dashboard" or user_role == "dentist":
        system_context = f"""You are FlossyAI, an intelligent dental practice assistant for Dr. {user_name} at Smile Artists Dental Studio.
        You help with:
        - Summarizing patient histories and appointments
        - Generating prescription templates
        - Providing clinical suggestions
        - Answering dental practice management questions
        - Patient follow-up reminders
        Keep responses concise (max 3 sentences) and professional."""
    elif user_role == "receptionist":
        system_context = f"""You are FlossyAI, a helpful assistant for {user_name} at Smile Artists Dental Studio reception.
        You help with:
        - Appointment scheduling and management
        - Patient record lookups
        - Answering clinic information questions
        Keep responses concise (max 3 sentences) and friendly."""
    else:
        system_context = f"""You are FlossyAI, a friendly dental health assistant for {user_name} at Smile Artists Dental Studio.
        You help with:
        - Answering dental health questions
        - Explaining procedures
        - Appointment guidance
        Keep responses concise (max 3 sentences) and empathetic."""
    
    prompt = f"{system_context}\n\nUser: {message}\n\nFlossyAI:"
    
    # Try Groq for Agentic capabilities
    from app.services.llm_client import groq_client
    if groq_client and user_role in ["dentist", "receptionist"]:
        try:
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_context},
                    {"role": "user", "content": message}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.4,
                tools=TOOLS_SCHEMA,
                tool_choice="auto",
            )
            
            response_msg = chat_completion.choices[0].message
            tool_calls = response_msg.tool_calls
            
            if tool_calls:
                # Execute tools and return the results!
                print(f"🔧 FlossyAI is calling {len(tool_calls)} tools!")
                messages_for_second_pass = [
                    {"role": "system", "content": system_context},
                    {"role": "user", "content": message},
                    response_msg
                ]
                
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    import json
                    try:
                        function_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        function_args = {}
                    
                    tool_output = execute_tool(function_name, function_args, db)
                    print(f"🛠️ Result from {function_name}: {tool_output}")
                    
                    messages_for_second_pass.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": str(tool_output)
                        }
                    )
                
                # Make second LLM request to synthesize tool responses
                second_response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages_for_second_pass
                )
                
                response = second_response.choices[0].message.content.strip()
            else:
                response = response_msg.content.strip()
                
        except Exception as e:
            print(f"❌ AI Agent Chat Error (Groq): {e}")
            try:
                response = ai_generate(prompt, temperature=0.7)
                response = response.strip()
            except:
                response = f"I'm having trouble connecting right now, {user_name}. Please try again in a moment."
    else:
        # Fallback to standard generic response for patients or if Groq fails
        try:
            response = ai_generate(prompt, temperature=0.7)
            response = response.strip()
        except Exception as e:
            print(f"❌ AI Chat Error: {e}")
            response = f"I'm having trouble connecting right now, {user_name}. Please try again in a moment."
    
    return {
        "response": response,
        "context": context
    }

@router.post("/ai_response")
async def ai_response(request: Request, user=Depends(require_role("patient"))):
    payload = await request.json()
    user_msg = payload.get("query", "").strip()
    if not user_msg:
        return {"answer": "I didn't receive any message. Could you please repeat that?"}

    # Load Knowledge Base
    import os
    kb_path = os.path.join(os.path.dirname(__file__), "../../../resources/clinic_knowledge.json")
    try:
        with open(kb_path, "r", encoding="utf-8") as f:
            KB_DATA = json.load(f)
    except Exception as e:
        print(f"KB Load Error: {e}")
        KB_DATA = {}

    # Get user's name
    user_payload = getattr(request.state, "user", {})
    user_name = (
        payload.get("user_name") or 
        user_payload.get("first_name") or 
        "there"
    )

    SYSTEM_PROMPT = f"""
    You are Flossy, the intelligent RAG-powered assistant for {KB_DATA.get('clinic_info', {}).get('name', 'Smile Artists')}.
    You are chatting with a patient named {user_name}.
    
    **CRITICAL GUIDELINE:**
    - ALWAYS base your answers on the provided [CLINIC KNOWLEDGE].
    - If you answer based on the knowledge base, start your response with a 📚 icon.
    - If the knowledge base doesn't have the answer, use your general dental knowledge but state it's general advice.
    - Keep responses professional and empathetic (max 3 sentences).
    
    [CLINIC KNOWLEDGE]
    {json.dumps(KB_DATA, indent=2)}
    """
    
    prompt = f"{SYSTEM_PROMPT}\n\nUSER ({user_name}): {user_msg}\n\nFLOSSY:"
    try:
        reply = ai_generate(prompt)
        reply = reply.strip()
    except Exception as e:
        print(f"AI Response Error: {e}")
        reply = f"I'm having trouble connecting to my knowledge base right now, {user_name}. Please try again later."

    return {
        "answer": reply,
        "is_grounded": "📚" in reply
    }

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
    except Exception as e:
        print(f"❌ AI Suggestion Error: {e}")
        import traceback
        traceback.print_exc()
        fact = "Your Tooth Enamel is the hardest substance in your body—even tougher than bone! ✨"

    return {"suggestion": fact}

@router.post("/triage")
async def ai_triage(request: Request, db: Session = Depends(get_db), user=Depends(require_role("patient"))):
    payload = await request.json()
    symptoms = payload.get("symptoms", "").strip()
    if not symptoms:
        raise HTTPException(status_code=400, detail="Please describe your symptoms")

    # Find or create patient profile
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
        # Auto-create patient profile if it doesn't exist
        import time
        from datetime import timezone
        unique_phone = f"TEMP_{user.id}_{int(time.time()) % 100000}"
        patient = Patient(
            user_id=user.id,
            name=user.email.split('@')[0] if user.email else "Patient",
            phone=unique_phone,
            source="website",
            contact_datetime=datetime.now(timezone.utc)
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        print(f"📝 Auto-created patient for triage: id={patient.id}")

    prompt = f"""
    You are a professional dental triage assistant.
    Analyze the following patient symptoms and categorize them strictly into the requested JSON format.
    
    PATIENT SYMPTOMS: "{symptoms}"
    
    RESPONSE FORMAT (JSON ONLY):
    {{
      "urgency": "emergency" | "soon" | "routine",
      "probable_issue": "string (e.g., Abscess, Cavity, Wisdom Tooth)",
      "recommended_dept": "string (e.g., General Dentistry, Oral Surgery, Orthodontics)",
      "ai_reasoning": "brief clinical explanation (max 20 words)",
      "patient_guidance": "what the patient should do now (max 15 words)"
    }}
    
    URGENCY GUIDELINES:
    - emergency: severe pain, uncontrollable bleeding, facial swelling, trauma.
    - soon: moderate pain, loose crown, sensitive tooth.
    - routine: cleaning, check-up, mild staining.
    """

    try:
        raw_ai_output = ai_generate(prompt)
        print(f"DEBUG: raw_ai_output={raw_ai_output[:100]}...") # Log first 100 chars
        
        # Handle fallback message from ai_generate
        if "I apologize" in raw_ai_output and "connecting to my brain" in raw_ai_output:
            return {
                "success": False,
                "triage": {
                    "urgency": "routine",
                    "probable_issue": "System busy",
                    "ai_reasoning": "I'm having trouble connecting to my analysis engine. Please try again in 1 minute.",
                    "patient_guidance": "If you have severe pain, please call us directly."
                }
            }

        # Handle potential markdown wrapping
        if "```json" in raw_ai_output:
            raw_ai_output = raw_ai_output.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_ai_output:
             raw_ai_output = raw_ai_output.split("```")[1].split("```")[0].strip()
        
        try:
            triage_data = json.loads(raw_ai_output)
        except json.JSONDecodeError as json_err:
            print(f"❌ Triage JSON Parse Error: {json_err}")
            print(f"📝 Raw AI Output: {raw_ai_output}")
            # If AI returned text but not JSON, try to salvage urgency at least
            return {
                "success": True,
                "triage": {
                    "urgency": "soon" if "pain" in raw_ai_output.lower() else "routine",
                    "probable_issue": "Manual review needed",
                    "ai_reasoning": "The AI provided a text-only response. Your symptoms have been recorded.",
                    "patient_guidance": "Please book an appointment for a proper diagnosis."
                }
            }

        # Save to DB
        try:
            triage_record = TriageResult(
                patient_id=patient.id,
                symptoms=symptoms,
                urgency=triage_data.get("urgency", "routine"),
                probable_issue=triage_data.get("probable_issue"),
                recommended_dept=triage_data.get("recommended_dept"),
                ai_reasoning=triage_data.get("ai_reasoning")
            )
            db.add(triage_record)
            db.commit()
            db.refresh(triage_record)
        except Exception as db_err:
            print(f"❌ Database error saving triage: {db_err}")
            db.rollback()
            # If DB fails, we still return the AI findings!
            return {
                "success": True,
                "triage": triage_data,
                "id": 0 # Temporary ID
            }
        
        return {
            "success": True,
            "triage": triage_data,
            "id": triage_record.id
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"❌ Triage Fatal Error: {e}")
        import traceback
        traceback.print_exc()
        # Return the error in the reasoning so the user can see it
        return {
            "success": False,
            "triage": {
                "urgency": "routine",
                "probable_issue": "System Error",
                "ai_reasoning": f"INTERNAL ERROR: {str(e)}",
                "patient_guidance": "Please check the server logs or try again."
            }
        }

@router.post("/summarize_visit")
async def summarize_visit(request: Request, db: Session = Depends(get_db), user=Depends(require_role("dentist"))):
    payload = await request.json()
    notes = payload.get("notes", "").strip()
    if not notes:
        raise HTTPException(status_code=400, detail="Notes are required to generate summary")

    prompt = f"""
    You are a dental clinical documentation assistant.
    Transform the following shorthand dentist notes into two distinct summaries:
    1. A formal, structured "Clinical Record" for the dentist's archive.
    2. A "Patient-Friendly Summary" that explain the procedure in simple terms.
    
    DENTIST NOTES: "{notes}"
    
    RESPONSE FORMAT (JSON ONLY):
    {{
      "clinical": "formal clinical narrative...",
      "patient_friendly": "warm, simple explanation...",
      "suggested_follow_up": "brief recommendation for next visit"
    }}
    """

    try:
        raw_ai_output = ai_generate(prompt)
        if "```json" in raw_ai_output:
            raw_ai_output = raw_ai_output.split("```json")[1].split("```")[0].strip()
        
        summary_data = json.loads(raw_ai_output)
        return summary_data
    except Exception as e:
        print(f"Summarization Error: {e}")
        raise HTTPException(status_code=500, detail="AI Summarization failed.")

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
