from datetime import datetime, timezone
import re
import io
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from core.database import get_db
from core.dependencies import require_role
from models import Prescription, Patient, User
from .schemas import PrescriptionCreate, PrescriptionUpdate
from services.pdf import FlossyPDF

router = APIRouter()

@router.post("/")
def create_prescription(data: PrescriptionCreate, db: Session = Depends(get_db), user = Depends(require_role("dentist"))):
    # 1. Search for Patient record first
    search_name = data.patient_name.strip().title()
    patient = db.query(Patient).filter(Patient.name.ilike(search_name)).first()

    if not patient:
        # Fallback: Search in Users table for legacy or derived names
        target_user = None
        all_users = db.query(User).filter(User.role.ilike("patient")).all()
        
        for u in all_users:
            p = db.query(Patient).filter(Patient.user_id == u.id).first()
            if p and p.name and p.name.strip().title() == search_name:
                patient = p
                break
            
            # Fallback: Derived name
            prefix = (u.email or "").split("@")[0]
            prefix_no_digits = re.sub(r'\d+', '', prefix)
            derived_name = prefix_no_digits.replace(".", " ").replace("_", " ").replace("-", " ").strip().title()
            
            if derived_name == search_name:
                target_user = u
                break
        
        if not patient and not target_user:
            raise HTTPException(status_code=404, detail="User not found for this patient name.")

        if not patient and target_user:
            # Create a Patient profile for this User
            patient = Patient(
                name=data.patient_name,
                phone=f"auto-{target_user.id}",
                user_id=target_user.id
            )
            db.add(patient)
            db.commit()
            db.refresh(patient)

    # 3. Create the prescription with structured fields
    new_presc = Prescription(
        patient_id=patient.id,
        doctor_id=user.id,
        details=data.details,
        diagnosis=data.diagnosis,
        treatment_plan=data.treatment_plan,
        recommendations=data.recommendations,
        created_at=data.created_at or datetime.now(timezone.utc)
    )
    db.add(new_presc)
    db.commit()
    db.refresh(new_presc)
    return {"success": True, "prescription_id": new_presc.id}

@router.get("/my")
def get_my_prescriptions(db: Session = Depends(get_db), user = Depends(require_role("patient"))):
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
        return {"prescriptions": []}
    
    prescs = db.query(Prescription).filter(Prescription.patient_id == patient.id).order_by(Prescription.created_at.desc()).all()
    return {
        "prescriptions": [
            {
                "id": p.id,
                "doctor": p.doctor.email.split("@")[0].title() if p.doctor else "Dentist",
                "details": p.details,
                "diagnosis": p.diagnosis,
                "treatment_plan": p.treatment_plan,
                "recommendations": p.recommendations,
                "date": p.created_at.isoformat()
            }
            for p in prescs
        ]
    }

@router.get("/dentist")
def get_dentist_prescriptions(db: Session = Depends(get_db), user = Depends(require_role("dentist"))):
    prescs = db.query(Prescription).filter(Prescription.doctor_id == user.id).order_by(Prescription.created_at.desc()).all()
    return {
        "prescriptions": [
            {
                "id": p.id,
                "patient": p.patient.name,
                "details": p.details,
                "diagnosis": p.diagnosis,
                "treatment_plan": p.treatment_plan,
                "recommendations": p.recommendations,
                "date": p.created_at.isoformat()
            }
            for p in prescs
        ]
    }

@router.put("/{id}")
def update_prescription(id: int, data: PrescriptionUpdate, db: Session = Depends(get_db), user = Depends(require_role("dentist"))):
    presc = db.query(Prescription).filter(Prescription.id == id).first()
    if not presc:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    if presc.doctor_id != user.id:
        if user.email != "prachi.swarnim@gmail.com":
             raise HTTPException(status_code=403, detail="Not authorized to edit this prescription")

    if data.details is not None: presc.details = data.details
    if data.diagnosis is not None: presc.diagnosis = data.diagnosis
    if data.treatment_plan is not None: presc.treatment_plan = data.treatment_plan
    if data.recommendations is not None: presc.recommendations = data.recommendations
    if data.created_at is not None: presc.created_at = data.created_at
    
    db.commit()
    return {"success": True}

@router.get("/{id}/pdf")
def download_prescription_pdf(id: int, stamp: bool = Query(True), db: Session = Depends(get_db)):
    presc = db.query(Prescription).filter(Prescription.id == id).first()
    if not presc:
        raise HTTPException(status_code=404, detail="Prescription not found")

    p_name = presc.patient.name if presc.patient else "Valued Patient"
    if p_name.lower().startswith("auto-") or p_name.lower() == "undefined":
        if presc.patient and presc.patient.user:
            prefix = presc.patient.user.email.split("@")[0]
            p_name = re.sub(r'\d+', '', prefix).replace(".", " ").replace("_", " ").replace("-", " ").strip().title()
    else:
        p_name = p_name.title()

    doc_raw = "Dentist"
    if presc.doctor:
        doc_raw = presc.doctor.email.split("@")[0]

    clean = re.sub(r'\d+', '', doc_raw)
    clean = clean.replace(".", " ").replace("_", " ").replace("-", " ").strip()
    
    parts = clean.split()
    if len(parts) == 2:
        p1 = parts[0].lower()
        p2 = parts[1].lower()
        if p1 == "choudhary" and p2 == "shruti":
            proper = f"{parts[1].capitalize()} {parts[0].capitalize()}"
        else:
            proper = f"{parts[0].capitalize()} {parts[1].capitalize()}"
    else:
        proper = " ".join(p.capitalize() for p in parts)
        
    doc_name = proper
    if not doc_name.lower().startswith("dr.") and not doc_name.lower().startswith("dr "):
        doc_name = f"Dr. {doc_name}"

    pdf = FlossyPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Header: Logo & Clinic Info
    logo_path = r"c:\Users\Prachi Swarnim\Desktop\Flossy\flossy-ui\public\static\assets\logo.png"
    try:
        pdf.image(logo_path, 10, 15, 30)
    except:
        pass
        
    pdf.set_xy(45, 15)
    pdf.set_font("Times", "B", 24)
    pdf.set_text_color(240, 184, 0)
    brand_w = pdf.get_string_width("Smile Artists")
    pdf.cell(0, 8, "Smile Artists", ln=True)
    
    pdf.set_font("Times", "I", 14)
    tag_w = pdf.get_string_width("...crafting smiles")
    pdf.set_x(45 + brand_w - tag_w) 
    pdf.set_text_color(240, 184, 0)
    pdf.cell(0, 6, "...crafting smiles", ln=True)
    pdf.ln(2) 
    
    pdf.set_x(45)
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, "573, Smile Artists Dental Studio, Artemis Hospital Road", ln=True)
    pdf.set_x(45)
    pdf.cell(0, 5, "Koyal Vihar, Gurugram - 122003, Haryana, India", ln=True)
    pdf.set_x(45)
    pdf.cell(0, 5, "Ph: +91 9693288488, +91 8507213999 | Web: www.smileartists.in", ln=True)
    
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 14)
    pdf.set_fill_color(244, 244, 244)
    pdf.set_text_color(26, 26, 26)
    pdf.cell(190, 10, " MEDICAL PRESCRIPTION ", ln=True, align="C", fill=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 8, "Patient Name:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(70, 8, p_name)
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 8, "Prescription ID:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, f"#{1000 + presc.id}", ln=True)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 8, "Age / Sex:")
    pdf.set_font("Arial", "", 10)
    p_age = str(presc.patient.age) if presc.patient and presc.patient.age else "N/A"
    p_sex = presc.patient.sex if presc.patient and presc.patient.sex else "N/A"
    pdf.cell(70, 8, f"{p_age} / {p_sex}")

    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 8, "Patient ID:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, f"P-{1000 + presc.patient_id}", ln=True)
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 8, "Date:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(70, 8, presc.created_at.strftime("%d %b, %Y"))
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 8, "Dentist:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, doc_name, ln=True)
    
    pdf.ln(5)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)
    
    def add_section(title, content, bullet=True):
        if not content: return
        pdf.set_font("Arial", "B", 11)
        pdf.set_text_color(212, 175, 55)
        pdf.cell(0, 8, title.upper(), ln=True)
        pdf.ln(1)
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(40, 40, 40)
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line: continue
            clean_line = re.sub(r'^[•\-\*]\s*', '', line)
            try: clean_line.encode('latin-1')
            except UnicodeEncodeError: clean_line = clean_line.encode('ascii', 'ignore').decode('ascii')
            if not clean_line: continue
            
            if bullet:
                pdf.set_x(15)
                pdf.cell(5, 6, "\xb7", ln=0)
                pdf.multi_cell(0, 6, clean_line)
            else:
                pdf.set_x(15)
                pdf.multi_cell(0, 6, clean_line)
        pdf.ln(4)

    if presc.details:
        add_section("Chief Complaint", presc.details, bullet=False)
        
    if presc.diagnosis:
        add_section("Diagnosis", presc.diagnosis)
    if presc.treatment_plan:
        add_section("Treatment Plan", presc.treatment_plan)
    if presc.recommendations:
        add_section("Recommendations", presc.recommendations)
    
    if pdf.get_y() > 250: pdf.add_page() 
    pdf.set_auto_page_break(False) 
    
    if stamp:
        stamp_path = r"Clinic Stamp.jpg"
        try:
            with pdf.rotation(angle=-5, x=167.5, y=262):
                pdf.image(stamp_path, x=150, y=252, w=35) 
        except:
            try: pdf.image(stamp_path, x=150, y=252, w=35) 
            except: pass

    pdf_bytes = bytes(pdf.output())
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=prescription_{id}.pdf"}
    )
