import os
import shutil
import uuid
import re
import io
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_role
from app.models import Prescription, Patient, User
from app.api.v1.prescriptions.schemas import PrescriptionCreate, PrescriptionUpdate
from app.services.pdf import FlossyPDF

router = APIRouter()

# 🏥 UPLOAD X-RAYS
@router.post("/upload_xray")
async def upload_xray(file: UploadFile = File(...), user = Depends(require_role("dentist"))):
    try:
        from app.core.storage import upload_file
        
        file_ext = file.filename.split(".")[-1]
        file_name = f"{uuid.uuid4()}.{file_ext}"
        
        result_url = upload_file(file, file_name)
        
        # If result_url is a full https://, return it as url. Otherwise use local path.
        if result_url.startswith("http"):
            return {"filename": file_name, "url": result_url}
        else:
            return {"filename": file_name, "url": f"/uploads/{file_name}"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/")
def create_prescription(data: PrescriptionCreate, db: Session = Depends(get_db), user = Depends(require_role("dentist"))):
    # 1. Search for Patient record first
    search_name = data.patient_name.strip().title()
    
    # Try exact case-insensitive match
    patient = db.query(Patient).filter(Patient.name.ilike(search_name)).first()

    # Fallback: Try with wildcards to handle extra whitespace
    if not patient:
        patient = db.query(Patient).filter(Patient.name.ilike(f"%{search_name}%")).first()

    # Fallback: Normalize and compare all patient names
    if not patient:
        all_patients = db.query(Patient).all()
        for p in all_patients:
            if p.name and p.name.strip().title() == search_name:
                patient = p
                break

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
    linked_id = None
    if data.continue_prescription_id:
        # Verify the continuation target exists and belongs to same patient
        parent = db.query(Prescription).filter(Prescription.id == data.continue_prescription_id).first()
        if parent and parent.patient_id == patient.id:
            # Find the root prescription (follow chain up)
            root_id = parent.linked_to or parent.id
            linked_id = root_id

    new_presc = Prescription(
        patient_id=patient.id,
        doctor_id=user.id,
        details=data.details,
        diagnosis=data.diagnosis,
        treatment_plan=data.treatment_plan,
        recommendations=data.recommendations,
        linked_to=linked_id,
        xrays=data.xrays or [],
        created_at=data.created_at or datetime.now(timezone.utc)
    )
    db.add(new_presc)
    db.commit()
    db.refresh(new_presc)
    return {"success": True, "prescription_id": new_presc.id}

# Alias for /create endpoint (used by frontend)
@router.post("/create")
def create_prescription_alias(data: PrescriptionCreate, db: Session = Depends(get_db), user = Depends(require_role("dentist"))):
    return create_prescription(data, db, user)

@router.get("/recent")
def get_recent_prescriptions(db: Session = Depends(get_db), user = Depends(require_role(["dentist", "receptionist"]))):
    """
    Get recent prescriptions for the dashboard (last 10).
    """
    prescs = db.query(Prescription).order_by(Prescription.created_at.desc()).limit(10).all()
    return {
        "prescriptions": [
            {
                "id": p.id,
                "patient_name": p.patient.name if p.patient else "Unknown",
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

@router.get("/patient/{patient_name}")
def get_patient_prescriptions_by_name(patient_name: str, db: Session = Depends(get_db), user = Depends(require_role(["dentist", "receptionist"]))):
    """
    Get all prescriptions for a specific patient by name.
    Used by dentist dashboard to show prescription history when selecting a patient.
    """
    import urllib.parse
    decoded_name = urllib.parse.unquote(patient_name).strip()
    search_name = decoded_name.title()
    
    # 1. Try exact case-insensitive match
    patient = db.query(Patient).filter(Patient.name.ilike(decoded_name)).first()
    
    # 2. Try with title case
    if not patient:
        patient = db.query(Patient).filter(Patient.name.ilike(search_name)).first()

    # 3. Try with wildcards to handle extra whitespace in DB
    if not patient:
        patient = db.query(Patient).filter(Patient.name.ilike(f"%{search_name}%")).first()

    # 4. Normalize and compare all patient names
    if not patient:
        all_patients = db.query(Patient).all()
        for p in all_patients:
            if p.name and p.name.strip().title() == search_name:
                patient = p
                break
    
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

@router.delete("/{id}")
def delete_prescription(id: int, db: Session = Depends(get_db), user = Depends(require_role("dentist"))):
    presc = db.query(Prescription).filter(Prescription.id == id).first()
    if not presc:
        raise HTTPException(status_code=404, detail="Prescription not found")
    db.delete(presc)
    db.commit()
    return {"success": True}
@router.get("/{id}/pdf")
def download_prescription_pdf(id: int, stamp: bool = Query(True), db: Session = Depends(get_db)):
    presc = db.query(Prescription).filter(Prescription.id == id).first()
    if not presc:
        raise HTTPException(status_code=404, detail="Prescription not found")

    # ── Collect all linked prescriptions (root + continuations) ──
    root = presc
    if presc.linked_to:
        parent = db.query(Prescription).filter(Prescription.id == presc.linked_to).first()
        if parent:
            root = parent

    continuations = db.query(Prescription).filter(Prescription.linked_to == root.id).order_by(Prescription.created_at.asc()).all()
    all_prescriptions = [root] + continuations

    # ── Patient name resolution ──
    p_name = presc.patient.name if presc.patient else "Valued Patient"
    if p_name.lower().startswith("auto-") or p_name.lower() == "undefined":
        if presc.patient and presc.patient.user:
            prefix = presc.patient.user.email.split("@")[0]
            p_name = re.sub(r'\d+', '', prefix).replace(".", " ").replace("_", " ").replace("-", " ").strip().title()
    else:
        p_name = p_name.title()

    # ── Doctor name resolution ──
    def resolve_doctor_name(doc_user):
        if not doc_user:
            return "Dentist"
        doc_raw = doc_user.email.split("@")[0]
        clean = re.sub(r'\d+', '', doc_raw)
        clean = clean.replace(".", " ").replace("_", " ").replace("-", " ").strip()
        parts = clean.split()
        if len(parts) == 2:
            p1, p2 = parts[0].lower(), parts[1].lower()
            if p1 == "choudhary" and p2 == "shruti":
                proper = f"{parts[1].capitalize()} {parts[0].capitalize()}"
            else:
                proper = f"{parts[0].capitalize()} {parts[1].capitalize()}"
        else:
            proper = " ".join(p.capitalize() for p in parts)
        if not proper.lower().startswith("dr.") and not proper.lower().startswith("dr "):
            proper = f"Dr. {proper}"
        return proper

    from pathlib import Path
    logo_path = str(Path(__file__).resolve().parents[4] / "logo.png")
    stamp_path = str(Path(__file__).resolve().parents[4] / "Clinic Stamp.jpg")

    pdf = FlossyPDF()
    pdf.set_auto_page_break(auto=True, margin=20)

    p_age = str(presc.patient.age) if presc.patient and presc.patient.age else "N/A"
    p_sex = presc.patient.sex if presc.patient and presc.patient.sex else "N/A"

    # ── Helper: render one prescription page ──
    def render_prescription_page(p, page_idx, total_pages):
        doc_name = resolve_doctor_name(p.doctor)
        pdf.add_page()

        # ── HEADER: Logo & Clinic Info ──
        try:
            pdf.image(logo_path, 10, 15, 30)
        except:
            pass

        pdf.set_xy(45, 15)
        pdf.set_font("Times", "B", 24)
        pdf.set_text_color(212, 175, 55)
        brand_w = pdf.get_string_width("Smile Artists")
        pdf.cell(0, 8, "Smile Artists", ln=True)

        pdf.set_font("Times", "I", 13)
        tag_w = pdf.get_string_width("...crafting smiles")
        pdf.set_x(45 + brand_w - tag_w)
        pdf.set_text_color(212, 175, 55)
        pdf.cell(0, 6, "...crafting smiles", ln=True)
        pdf.ln(2)

        pdf.set_x(45)
        pdf.set_font("Arial", "", 8)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 4, "573, Smile Artists Dental Studio, Artemis Hospital Road", ln=True)
        pdf.set_x(45)
        pdf.cell(0, 4, "Koyal Vihar, Gurugram - 122003, Haryana, India", ln=True)
        pdf.set_x(45)
        pdf.cell(0, 4, "Ph: +91 9693288488, +91 8507213999 | Web: www.smileartistsdentalstudio.com", ln=True)

        # Gold accent bar under header
        pdf.ln(3)
        pdf.set_fill_color(212, 175, 55)
        pdf.rect(10, pdf.get_y(), 190, 1.2, 'F')
        pdf.ln(5)

        # ── TITLE BAR ──
        pdf.set_font("Arial", "B", 13)
        pdf.set_fill_color(35, 35, 35)
        pdf.set_text_color(255, 255, 255)
        title_text = " MEDICAL PRESCRIPTION"
        if page_idx > 0:
            title_text = f" MEDICAL PRESCRIPTION  -  CONTINUATION (Visit {page_idx + 1})"
        pdf.cell(190, 10, title_text, ln=True, align="C", fill=True)
        pdf.ln(6)

        # ── PATIENT INFO TABLE ──
        # Row 1
        pdf.set_font("Arial", "B", 9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(28, 7, "Patient Name:")
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(72, 7, p_name.upper())
        pdf.set_font("Arial", "B", 9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(25, 7, "Presc. ID:")
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(0, 7, f"#{1000 + root.id}", ln=True)

        # Row 2
        pdf.set_font("Arial", "B", 9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(28, 7, "Age / Sex:")
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(72, 7, f"{p_age} / {p_sex}")
        pdf.set_font("Arial", "B", 9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(25, 7, "Patient ID:")
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(0, 7, f"P-{1000 + presc.patient_id}", ln=True)

        # Row 3
        pdf.set_font("Arial", "B", 9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(28, 7, "Date:")
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(72, 7, p.created_at.strftime("%d %b, %Y"))
        pdf.set_font("Arial", "B", 9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(25, 7, "Dentist:")
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(0, 7, doc_name, ln=True)

        # Separator line
        pdf.ln(4)
        pdf.set_draw_color(212, 175, 55)
        pdf.set_line_width(0.3)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(6)

        # ── SECTION RENDERER ──
        def add_section(title, content, bullet=True, rx_symbol=False):
            if not content:
                return

            if rx_symbol:
                # Draw large Rx symbol in gold
                pdf.set_font("Times", "BI", 22)
                pdf.set_text_color(212, 175, 55)
                pdf.cell(16, 10, "Rx", ln=0)
                pdf.set_font("Arial", "B", 11)
                pdf.set_text_color(212, 175, 55)
                pdf.cell(0, 10, title.upper(), ln=True)
            else:
                pdf.set_font("Arial", "B", 11)
                pdf.set_text_color(212, 175, 55)
                pdf.cell(0, 8, title.upper(), ln=True)

            # Thin underline under section title
            pdf.set_draw_color(230, 210, 140)
            pdf.set_line_width(0.2)
            pdf.line(10, pdf.get_y(), 100, pdf.get_y())
            pdf.ln(3)

            pdf.set_font("Arial", "", 10)
            pdf.set_text_color(40, 40, 40)

            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                clean_line = re.sub(r'^[•\-\*]\s*', '', line)
                try:
                    clean_line.encode('latin-1')
                except UnicodeEncodeError:
                    clean_line = clean_line.encode('ascii', 'ignore').decode('ascii')
                if not clean_line:
                    continue

                if bullet:
                    pdf.set_x(15)
                    pdf.cell(5, 6, "\xb7", ln=0)
                    pdf.multi_cell(0, 6, clean_line)
                else:
                    pdf.set_x(15)
                    pdf.multi_cell(0, 6, clean_line)
            pdf.ln(5)

        # ── PRESCRIPTION CONTENT ──
        if p.details:
            add_section("Chief Complaint", p.details, bullet=False)
        if p.diagnosis:
            add_section("Diagnosis", p.diagnosis)
        if p.treatment_plan:
            add_section("Treatment Plan", p.treatment_plan)
        if p.recommendations:
            add_section("Recommendation / Instructions", p.recommendations, rx_symbol=True)

        # ── X-RAY SECTION ──
        if p.xrays and len(p.xrays) > 0:
            pdf.add_page() # Put X-rays on a fresh page
            pdf.set_font("Arial", "B", 12)
            pdf.set_text_color(212, 175, 55)
            pdf.cell(0, 10, "RADIOLOGICAL EVIDENCE (X-RAYS)", ln=True, align="C")
            pdf.ln(5)
            
            x_start = 15
            y_curr = pdf.get_y()
            img_w = 85
            img_h = 65
            spacing = 10
            
            for i, img_name in enumerate(p.xrays):
                f_path = os.path.join("uploads", img_name)
                
                # If not local, try to download from GCS for PDF generation
                if not os.path.exists(f_path):
                    try:
                        from app.core.config import STORAGE_BUCKET
                        from google.cloud import storage
                        client = storage.Client()
                        bucket = client.bucket(STORAGE_BUCKET)
                        blob = bucket.blob(img_name)
                        if blob.exists():
                            if not os.path.exists("uploads"): os.makedirs("uploads")
                            blob.download_to_filename(f_path)
                            print(f"📦 JIT Downloaded {img_name} for PDF")
                    except: pass

                if not os.path.exists(f_path): continue
                
                col = i % 2
                x_pos = x_start + (col * (img_w + spacing))
                
                # If it's a new row, update y_curr
                if i > 0 and col == 0:
                    y_curr += img_h + spacing + 10
                    
                # New page if overflow
                if y_curr + img_h > 260:
                    pdf.add_page()
                    y_curr = 20
                
                try:
                    pdf.image(f_path, x=x_pos, y=y_curr, w=img_w, h=img_h)
                    pdf.set_xy(x_pos, y_curr + img_h + 2)
                    pdf.set_font("Arial", "I", 8)
                    pdf.set_text_color(100, 100, 100)
                    pdf.cell(img_w, 5, f"X-ray Image {i+1}", align="C", ln=0)
                except: pass

        # ── FOOTER: Signature & Stamp ──
        if pdf.get_y() > 240:
            pdf.add_page()

        pdf.set_auto_page_break(False)

        # Doctor signature area
        pdf.set_y(252)
        pdf.set_draw_color(150, 150, 150)
        pdf.set_line_width(0.3)
        pdf.line(140, 258, 195, 258)
        pdf.set_font("Arial", "", 8)
        pdf.set_text_color(100, 100, 100)
        sig_text = f"Signature - {doc_name}"
        sig_w = pdf.get_string_width(sig_text)
        pdf.set_xy(140 + (55 - sig_w) / 2, 259)
        pdf.cell(55, 5, sig_text, align="C")

        # Stamp (only on last page)
        if stamp and page_idx == total_pages - 1:
            try:
                with pdf.rotation(angle=-5, x=167.5, y=245):
                    pdf.image(stamp_path, x=150, y=235, w=35)
            except:
                try:
                    pdf.image(stamp_path, x=150, y=235, w=35)
                except:
                    pass

        # Page number
        pdf.set_font("Arial", "I", 7)
        pdf.set_text_color(150, 150, 150)
        pdf.set_xy(10, 280)
        pdf.cell(190, 5, f"Page {page_idx + 1} of {total_pages}  |  Prescription #{1000 + root.id}", align="C")

        pdf.set_auto_page_break(True, margin=20)

    # ── RENDER ALL PAGES ──
    total = len(all_prescriptions)
    for idx, p in enumerate(all_prescriptions):
        render_prescription_page(p, idx, total)

    pdf_bytes = bytes(pdf.output())
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=prescription_{id}.pdf"}
    )

