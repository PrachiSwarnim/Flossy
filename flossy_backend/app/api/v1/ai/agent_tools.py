import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Appointment, Patient, Invoice, User

def get_appointments(db: Session, date_str: str) -> str:
    """Returns a summary of appointments for a given date (YYYY-MM-DD) or 'today'."""
    try:
        if date_str.lower() == "today":
            dt = datetime.now(timezone.utc).date()
        else:
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d").date()
            except:
                dt = datetime.now(timezone.utc).date()
                
        appts = db.query(Appointment).all()
        day_appts = [a for a in appts if a.datetime.date() == dt]
        
        if not day_appts:
            return f"No appointments found for {dt.strftime('%Y-%m-%d')}."
            
        result = [f"Found {len(day_appts)} appointments:"]
        for a in day_appts:
            pat = db.query(Patient).filter(Patient.id == a.patient_id).first()
            pname = pat.name if pat else "Unknown"
            astatus = a.status
            atime = a.datetime.strftime("%H:%M")
            result.append(f"- ID: {a.id} | {atime} | Patient: {pname} | Status: {astatus} | Reason: {a.reason}")
        return "\n".join(result)
    except Exception as e:
        return f"Error fetching appointments: {str(e)}"

def search_patients(db: Session, query: str) -> str:
    """Searches for patients by name and returns their basic info and ID."""
    try:
        patients = db.query(Patient).filter(Patient.name.ilike(f"%{query}%")).limit(5).all()
        if not patients:
            return f"No patients found matching '{query}'."
            
        result = [f"Found {len(patients)} patients matching '{query}':"]
        for p in patients:
            result.append(f"- ID: {p.id} | Name: {p.name} | Phone: {p.phone} | Age: {p.age}")
        return "\n".join(result)
    except Exception as e:
        return f"Error searching patients: {str(e)}"

def calculate_daily_revenue(db: Session, date_str: str) -> str:
    """Calculates total revenue and generated invoices for a given date (YYYY-MM-DD) or 'today'."""
    try:
        if date_str.lower() == "today":
            dt = datetime.now(timezone.utc).date()
        else:
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d").date()
            except:
                dt = datetime.now(timezone.utc).date()
                
        invoices = db.query(Invoice).all()
        day_invoices = [i for i in invoices if i.date.date() == dt]
        
        if not day_invoices:
            return f"No revenue generated for {dt.strftime('%Y-%m-%d')}."
            
        total = sum((i.total_amount or 0.0) for i in day_invoices)
        return f"Daily Closure Report for {dt.strftime('%Y-%m-%d')}:\n- Total Invoices: {len(day_invoices)}\n- Gross Revenue: INR {total:,.2f}"
    except Exception as e:
        return f"Error calculating revenue: {str(e)}"

def flag_patient_for_followup(db: Session, patient_id: int, reason: str) -> str:
    """Flags an existing appointment for a follow-up."""
    try:
        appt = db.query(Appointment).filter(Appointment.patient_id == patient_id).order_by(Appointment.datetime.desc()).first()
        if not appt:
            return f"Patient {patient_id} has no past appointments to flag."
        
        appt.status = "follow_up"
        appt.follow_up_reason = reason
        db.commit()
        return f"Success! Patient ID {patient_id} has been flagged for follow-up regarding: {reason}."
    except Exception as e:
        return f"Error flagging follow up: {str(e)}"

# Define the tools exactly as expected by Groq/OpenAI function calling schemas
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_appointments",
            "description": "Fetch a list of appointments for a specific date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_str": {
                        "type": "string",
                        "description": "The date to check in YYYY-MM-DD format, or 'today' for the current date."
                    }
                },
                "required": ["date_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_patients",
            "description": "Search for patients by passing a name or partial name query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Patient's first or last name to search for (e.g. 'Dhruv')."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_daily_revenue",
            "description": "Calculate daily clinic closure statistics including total revenue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_str": {
                        "type": "string",
                        "description": "The date to check in YYYY-MM-DD format, or 'today' for the current date."
                    }
                },
                "required": ["date_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "flag_patient_for_followup",
            "description": "Flag a database patient for a follow up by leaving a clinical reason.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "integer",
                        "description": "The numeric ID of the patient (e.g. 1)."
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for the follow-up, e.g., 'Check crown margins'."
                    }
                },
                "required": ["patient_id", "reason"]
            }
        }
    }
]

# Gemini Tool Schema (Slightly different from OpenAI/Groq format)
GEMINI_TOOLS_SCHEMA = [{
    "function_declarations": [
        {
            "name": "get_appointments",
            "description": "Fetch a list of appointments for a specific date.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "date_str": {"type": "STRING", "description": "The date to check in YYYY-MM-DD format, or 'today' for the current date."}
                },
                "required": ["date_str"]
            }
        },
        {
            "name": "search_patients",
            "description": "Search for patients by passing a name or partial name query.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "query": {"type": "STRING", "description": "Patient's first or last name to search for (e.g. 'Dhruv')."}
                },
                "required": ["query"]
            }
        },
        {
            "name": "calculate_daily_revenue",
            "description": "Calculate daily clinic closure statistics including total revenue.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "date_str": {"type": "STRING", "description": "The date to check in YYYY-MM-DD format, or 'today' for the current date."}
                },
                "required": ["date_str"]
            }
        },
        {
            "name": "flag_patient_for_followup",
            "description": "Flag a database patient for a follow up by leaving a clinical reason.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "patient_id": {"type": "INTEGER", "description": "The numeric ID of the patient (e.g. 1)."},
                    "reason": {"type": "STRING", "description": "Reason for the follow-up, e.g., 'Check crown margins'."}
                },
                "required": ["patient_id", "reason"]
            }
        }
    ]
}]

# Dispatcher
def execute_tool(tool_name: str, arguments: dict, db: Session) -> str:
    if tool_name == "get_appointments":
        return get_appointments(db, arguments.get("date_str", "today"))
    elif tool_name == "search_patients":
        return search_patients(db, arguments.get("query", ""))
    elif tool_name == "calculate_daily_revenue":
        return calculate_daily_revenue(db, arguments.get("date_str", "today"))
    elif tool_name == "flag_patient_for_followup":
        return flag_patient_for_followup(db, arguments.get("patient_id", -1), arguments.get("reason", ""))
    else:
        return f"Error: Tool {tool_name} not found."
