from datetime import datetime, timezone
import uuid
import io
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_role
from app.models import Invoice, InvoiceItem, PaymentRecord, Patient, User
from app.api.v1.invoices.schemas import InvoiceCreate
from app.services.pdf import FlossyPDF

router = APIRouter()

@router.post("/")
def create_invoice(data: InvoiceCreate, db: Session = Depends(get_db), user = Depends(require_role("any"))):
    """
    Creates an itemized invoice. Accessible by both dentist and receptionist.
    """
    try:
        # 1. Find patient - try multiple matching strategies since the frontend
        # sends the display_name which may differ from the raw Patient.name
        search_name = data.patient_name.strip()
        
        # Strategy 1: Direct match on Patient.name
        patient = db.query(Patient).filter(Patient.name.ilike(search_name)).first()
        
        # Strategy 2: Match on first_name + last_name (display_name from patients API)
        if not patient:
            from sqlalchemy import func
            patients_all = db.query(Patient).all()
            for p in patients_all:
                # Build display_name the same way the patients router does
                if p.first_name:
                    display = f"{p.first_name} {p.last_name or ''}".strip()
                else:
                    display = (p.name or "").strip()
                if display.lower() == search_name.lower():
                    patient = p
                    break
        
        # Strategy 3: Partial/fuzzy match on name field
        if not patient:
            patient = db.query(Patient).filter(
                Patient.name.ilike(f"%{search_name}%")
            ).first()
                
        if not patient:
            raise HTTPException(status_code=404, detail=f"Patient '{data.patient_name}' not found.")

        # 3. Create main Invoice record
        invoice = Invoice(
            invoice_number=data.invoice_number or "PENDING", # Placeholder
            patient_id=patient.id,
            doctor_id=user.id if user.role == "dentist" else None,
            discount=data.discount,
            currency=data.currency or "INR",
            date=data.date or datetime.now(timezone.utc),
            status="paid" # default assumed, will recalc
        )
        db.add(invoice)
        db.flush() 
        
        if not data.invoice_number:
            # Start sequence from 1000 (ID 1 -> 1000)
            invoice.invoice_number = f"INV-{999 + invoice.id}" 

        # 4. Add items
        gross_amount = 0.0
        for itm in data.items:
            t_date = datetime.now(timezone.utc)
            if itm.treatment_date:
                try: t_date = datetime.strptime(itm.treatment_date, "%Y-%m-%d")
                except: pass
            
            db.add(InvoiceItem(
                invoice_id=invoice.id,
                treatment_name=itm.treatment_name,
                treatment_date=t_date,
                cost=itm.cost,
                discount=itm.discount
            ))
            gross_amount += itm.cost - itm.discount

        # total_amount is sum(items net) - global discount
        invoice.total_amount = gross_amount - data.discount

        # 5. Add payments
        total_paid = 0.0
        for pay in data.payments:
            p_date = datetime.now(timezone.utc)
            if pay.paid_on:
                try: p_date = datetime.strptime(pay.paid_on, "%Y-%m-%d")
                except: pass
            
            rec_num = pay.receipt_number or f"REC-{uuid.uuid4().hex[:8].upper()}"
            db.add(PaymentRecord(
                invoice_id=invoice.id,
                receipt_number=rec_num,
                paid_on=p_date,
                payment_method=pay.payment_method,
                amount=pay.amount
            ))
            total_paid += pay.amount

        # Update status based on payment
        if total_paid >= invoice.total_amount:
            invoice.status = "paid"
        elif total_paid > 0:
            invoice.status = "partially_paid"
        else:
            invoice.status = "unpaid"

        db.commit()
        db.refresh(invoice)
        return {"success": True, "invoice_id": invoice.id, "invoice_number": invoice.invoice_number}
    except Exception as e:
        db.rollback()
        print(f"ERROR creating invoice: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{id}")
def update_invoice(id: int, data: InvoiceCreate, db: Session = Depends(get_db), user = Depends(require_role("any"))):
    invoice = db.query(Invoice).filter(Invoice.id == id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    try:
        # 1. Update basic fields
        if data.date: invoice.date = data.date
        if data.currency: invoice.currency = data.currency
        invoice.discount = data.discount
        
        # Patient - use same multi-strategy lookup
        search_name = data.patient_name.strip()
        patient = db.query(Patient).filter(Patient.name.ilike(search_name)).first()
        if not patient:
            patients_all = db.query(Patient).all()
            for p in patients_all:
                if p.first_name:
                    display = f"{p.first_name} {p.last_name or ''}".strip()
                else:
                    display = (p.name or "").strip()
                if display.lower() == search_name.lower():
                    patient = p
                    break
        if not patient:
            patient = db.query(Patient).filter(
                Patient.name.ilike(f"%{search_name}%")
            ).first()
        if patient: invoice.patient_id = patient.id

        # 2. Replace Items
        db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice.id).delete()
        gross_amount = 0.0
        for itm in data.items:
            t_date = datetime.now(timezone.utc)
            if itm.treatment_date:
                try: t_date = datetime.strptime(itm.treatment_date, "%Y-%m-%d")
                except: pass
            
            db.add(InvoiceItem(
                invoice_id=invoice.id,
                treatment_name=itm.treatment_name,
                treatment_date=t_date,
                cost=itm.cost,
                discount=itm.discount
            ))
            gross_amount += itm.cost - itm.discount

        invoice.total_amount = gross_amount - data.discount

        # 3. Replace Payments
        db.query(PaymentRecord).filter(PaymentRecord.invoice_id == invoice.id).delete()
        total_paid = 0.0
        for pay in data.payments:
            p_date = datetime.now(timezone.utc)
            if pay.paid_on:
                try: p_date = datetime.strptime(pay.paid_on, "%Y-%m-%d")
                except: pass
            
            rec_num = pay.receipt_number or f"RCP-{int(datetime.now().timestamp())}-{id}"
            db.add(PaymentRecord(
                invoice_id=invoice.id,
                receipt_number=rec_num,
                paid_on=p_date,
                payment_method=pay.payment_method,
                amount=pay.amount
            ))
            total_paid += pay.amount

        # Update Status
        if total_paid >= invoice.total_amount:
            invoice.status = "paid"
        elif total_paid > 0:
            invoice.status = "partially_paid"
        else:
            invoice.status = "unpaid"

        db.commit()
        return {"success": True, "invoice_id": invoice.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
def get_invoice_history(db: Session = Depends(get_db)):
    # Logic note: main.py had request but didn't use it except to check payload auth which Dependency handles
    query = db.query(Invoice).order_by(Invoice.date.desc())
    invs = query.all()
    results = []
    for i in invs:
        results.append({
            "id": i.id,
            "invoice_number": i.invoice_number,
            "patient_name": i.patient.name if i.patient else "Merged/Del",
            "date": i.date.isoformat(),
            "total": i.total_amount,
            "status": i.status,
            "currency": i.currency
        })
    return {"invoices": results}

@router.get("/{id}")
def get_invoice_details(id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "patient_name": invoice.patient.name,
        "date": invoice.date,
        "currency": invoice.currency,
        "discount": invoice.discount,
        "total_amount": invoice.total_amount,
        "status": invoice.status,
        "items": [
            {
                "treatment_name": i.treatment_name,
                "cost": i.cost,
                "discount": i.discount,
                "treatment_date": i.treatment_date,
                "discount_type": "flat" 
            }
            for i in invoice.items
        ],
        "payments": [
            {
                "payment_method": p.payment_method,
                "amount": p.amount,
                "paid_on": p.paid_on,
                "receipt_number": p.receipt_number
            }
            for p in invoice.payment_records
        ]
    }

@router.delete("/{id}")
def delete_invoice(id: int, db: Session = Depends(get_db), user = Depends(require_role("any"))):
    invoice = db.query(Invoice).filter(Invoice.id == id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    db.delete(invoice)
    db.commit()
    return {"success": True}

@router.get("/{id}/pdf")
def download_invoice_pdf(id: int, stamp: bool = Query(True), db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    pdf = FlossyPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # --- HEADER ---
    from pathlib import Path
    logo_path = str(Path(__file__).resolve().parents[4] / "logo.png")
    try:
        pdf.image(logo_path, 10, 15, 30)
    except:
        pass
        
    pdf.set_xy(45, 15)
    pdf.set_font("Times", "B", 24)
    pdf.set_text_color(212, 175, 55) # Gold
    brand_w = pdf.get_string_width("Smile Artists")
    pdf.cell(0, 8, "Smile Artists", ln=True)
    
    pdf.set_font("Times", "I", 14)
    tag_w = pdf.get_string_width("...crafting smiles")
    pdf.set_x(45 + brand_w - tag_w) 
    pdf.set_text_color(212, 175, 55)
    pdf.cell(0, 6, "...crafting smiles", ln=True)
    pdf.ln(2) 
    
    pdf.set_x(45)
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, "573, Smile Artists Dental Studio, Artemis Hospital Road", ln=True)
    pdf.set_x(45)
    pdf.cell(0, 5, "Koyal Vihar, Gurugram - 122003, Haryana, India", ln=True)
    pdf.set_x(45)
    pdf.cell(0, 5, "Ph: +91 9693288488, +91 8507213999 | Web: www.smileartistsdentalstudio.com", ln=True)
    
    pdf.ln(5)
    
    # Document Title
    pdf.set_font("Arial", "B", 14)
    pdf.set_fill_color(244, 244, 244)
    pdf.set_text_color(26, 26, 26)
    pdf.cell(190, 10, " OFFICIAL DIGITAL INVOICE ", ln=True, align="C", fill=True)
    pdf.ln(5)
    
    # Patient Info Row
    p_name = invoice.patient.name.upper()
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 8, "Patient:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(70, 8, p_name)
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 8, "Invoice #:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, invoice.invoice_number, ln=True)
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 8, "Age/Sex:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(70, 8, f"{invoice.patient.age or 'N/A'} / {invoice.patient.sex or 'N/A'}")
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 8, "Date:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, invoice.date.strftime("%d %b, %Y"), ln=True)
    
    pdf.ln(8)

    # Treatment Table
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(212, 175, 55)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(15, 10, "S.No", border=1, align="C", fill=True)
    pdf.cell(85, 10, " Description", border=1, fill=True)
    pdf.cell(30, 10, " Date", border=1, align="C", fill=True)
    pdf.cell(30, 10, f" Cost ({invoice.currency})", border=1, align="C", fill=True)
    pdf.cell(30, 10, " Disc.", border=1, align="C", fill=True, ln=True)
    
    pdf.set_text_color(26, 26, 26)
    pdf.set_font("Arial", "", 10)
    gross_amount = 0
    total_item_discount = 0
    for idx, item in enumerate(invoice.items, 1):
        item_discount = getattr(item, "discount", 0.0) or 0.0
        pdf.cell(15, 8, str(idx), border=1, align="C")
        pdf.cell(85, 8, f" {item.treatment_name}", border=1)
        t_date_str = item.treatment_date.strftime("%b %d, %Y") if item.treatment_date else "N/A"
        pdf.cell(30, 8, t_date_str, border=1, align="C")
        pdf.cell(30, 8, f"{item.cost:,.2f}", border=1, align="R")
        pdf.cell(30, 8, f"{item_discount:,.2f}", border=1, align="R", ln=True)
        gross_amount += item.cost
        total_item_discount += item_discount
        
    pdf.set_font("Arial", "B", 10)
    pdf.cell(150, 8, "Gross Amount", border=1, align="R")
    pdf.cell(0, 8, f"{invoice.currency} {gross_amount:,.2f}", border=1, align="R", ln=True)

    if total_item_discount > 0:
         pdf.cell(150, 8, "Item Discounts", border=1, align="R")
         pdf.cell(0, 8, f"INR {total_item_discount:,.2f}", border=1, align="R", ln=True)

    pdf.cell(150, 8, "Additional Discount", border=1, align="R")
    pdf.cell(0, 8, f"INR {invoice.discount:,.2f}", border=1, align="R", ln=True)
    
    pdf.set_fill_color(245, 245, 245)
    pdf.cell(150, 10, "TOTAL PAYABLE", border=1, align="R", fill=True)
    pdf.cell(0, 10, f"{invoice.currency} {invoice.total_amount:,.2f}", border=1, align="R", fill=True, ln=True)
    
    pdf.ln(10)

    # Payment Table
    pdf.set_font("Arial", "B", 10)
    pdf.cell(130, 8, "Payment History", ln=True)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(15, 8, "S.No", border=1, align="C")
    pdf.cell(60, 8, " Receipt #", border=1)
    pdf.cell(35, 8, " Paid On", border=1, align="C")
    pdf.cell(40, 8, " Method", border=1, align="C")
    pdf.cell(0, 8, " Amount", border=1, align="C", ln=True)
    
    pdf.set_font("Arial", "", 9)
    total_paid = 0
    for idx, pay in enumerate(invoice.payment_records, 1):
        pdf.cell(15, 7, str(idx), border=1, align="C")
        pdf.cell(60, 7, f" {pay.receipt_number}", border=1)
        pdf.cell(35, 7, pay.paid_on.strftime("%b %d, %Y"), border=1, align="C")
        pdf.cell(40, 7, pay.payment_method, border=1, align="C")
        pdf.cell(0, 7, f"{invoice.currency} {pay.amount:,.2f}", border=1, align="R", ln=True)
        total_paid += pay.amount
        
    pdf.set_font("Arial", "B", 9)
    pdf.cell(150, 8, "Total Amount Paid", border=1, align="R")
    pdf.cell(0, 8, f"{invoice.currency} {total_paid:,.2f}", border=1, align="R", ln=True)

    # Final Summary
    due = invoice.total_amount - total_paid
    pdf.ln(10)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(130, 10, "BALANCE DUE (NET):", border="B")
    pdf.set_text_color(200, 0, 0) if due > 0 else pdf.set_text_color(0, 150, 0)
    pdf.cell(0, 10, f"{invoice.currency} {max(0, due):,.2f}", border="B", align="R", ln=True)

    if pdf.get_y() > 240: pdf.add_page()
    
    if stamp:
        stamp_path = str(Path(__file__).resolve().parents[4] / "Clinic Stamp.jpg")
        try:
            with pdf.rotation(angle=-5, x=167.5, y=262):
                pdf.image(stamp_path, x=150, y=252, w=35)
        except:
             pass

    pdf_bytes = bytes(pdf.output())
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=invoice_{invoice.invoice_number}.pdf"}
    )
