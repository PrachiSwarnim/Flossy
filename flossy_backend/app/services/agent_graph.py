
import os
from typing import Annotated, Sequence, TypedDict, Union, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import logging

# --- DATABASE TOOLS (Ported from agent_server.py) ---
from app.core.database import SessionLocal
from app.models import Appointment, Patient, User
from sqlalchemy import and_
from datetime import datetime, timedelta

@tool
def lookup_patient(query: str):
    """Looks up a patient by name or phone number in the clinical database."""
    db = SessionLocal()
    try:
        patients = db.query(Patient).filter(
            (Patient.name.ilike(f"%{query}%")) | 
            (Patient.phone.ilike(f"%{query}%"))
        ).all()
        if not patients: return "No patient found."
        return "\n".join([f"Name: {p.name}, Phone: {p.phone}, Age: {p.age or 'N/A'}" for p in patients])
    finally: db.close()

@tool
def get_todays_appointments():
    """Returns a list of patients scheduled for today."""
    db = SessionLocal()
    try:
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        apps = db.query(Appointment).filter(
            and_(Appointment.datetime >= start, Appointment.datetime < end, Appointment.status == "scheduled")
        ).all()
        if not apps: return "No appointments today."
        res = ["Today's Appointments:"]
        for a in apps:
            p = db.query(Patient).filter(Patient.id == a.patient_id).first()
            time_str = a.datetime.strftime("%I:%M %p")
            res.append(f"- {p.name if p else 'Unknown'} at {time_str}")
        return "\n".join(res)
    finally: db.close()

@tool
def check_availability(date_str: str, time_str: str):
    """Checks if a dentist appointment slot is available. Format: YYYY-MM-DD HH:MM"""
    db = SessionLocal()
    try:
        dt_req = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        conflict = db.query(Appointment).filter(
            and_(Appointment.datetime >= dt_req, Appointment.datetime < dt_req + timedelta(minutes=30), Appointment.status == "scheduled")
        ).first()
        return "Slot is booked." if conflict else "Slot is available."
    finally: db.close()

tools = [lookup_patient, get_todays_appointments, check_availability]

# --- RAG RETRIEVER ---
class DentalRAG:
    def __init__(self):
        self.vectorstore = None
        try:
            embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
            # In a real scenario, we'd load dental_embeddings.faiss
            # For this demo, we'll assume the local file exists or initialize empty
            if os.path.exists("dental_embeddings.faiss"):
                self.vectorstore = FAISS.load_local("dental_embeddings.faiss", embeddings, allow_dangerous_deserialization=True)
            else:
                logging.warning("dental_embeddings.faiss not found. RAG will be empty.")
        except Exception as e:
            logging.error(f"RAG Init Error: {e}")

    def retrieve(self, query: str) -> str:
        if not self.vectorstore: return "No knowledge base available."
        docs = self.vectorstore.similarity_search(query, k=3)
        return "\n---\n".join([d.page_content for d in docs])

rag = DentalRAG()

# --- LANGGRAPH STATE ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], lambda x, y: x + y]
    rag_context: str

# --- NODES ---
model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", api_key=os.getenv("GOOGLE_API_KEY"))
model_with_tools = model.bind_tools(tools)

def call_model(state: AgentState):
    messages = state['messages']
    rag_context = state.get('rag_context', "")
    
    # Inject RAG context into the first system message if it exists
    if rag_context:
        updated_messages = []
        for m in messages:
            if isinstance(m, SystemMessage):
                updated_content = f"{m.content}\n\n[DENTAL KNOWLEDGE CONTEXT]\n{rag_context}"
                updated_messages.append(SystemMessage(content=updated_content))
            else:
                updated_messages.append(m)
        messages = updated_messages

    response = model_with_tools.invoke(messages)
    return {"messages": [response]}

def retrieve_rag(state: AgentState):
    last_message = state['messages'][-1].content
    # Simple logic: if message looks like a dental question, pull RAG
    context = rag.retrieve(last_message)
    return {"rag_context": context}

# --- GRAPH DEFINITION ---
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("action", ToolNode(tools))
workflow.add_node("retrieve", retrieve_rag)

workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "agent")

def route_after_agent(state: AgentState):
    last_message = state['messages'][-1]
    if last_message.tool_calls:
        return "action"
    return END

workflow.add_conditional_edges("agent", route_after_agent, {"action": "action", END: END})
workflow.add_edge("action", "agent")

app_graph = workflow.compile()
