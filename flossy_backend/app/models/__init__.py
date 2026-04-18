from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, LargeBinary, Float
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
from datetime import timezone

# 🧩 User table for Clerk-authenticated users
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    role = Column(String(50), nullable=True) # "dentist" or "patient"
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    patients = relationship("Patient", back_populates="user", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="doctor")

    def __repr__(self):
        return f"<User(email={self.email}, role={self.role})>"


# 🧠 Patient details (linked to a User)
class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, index=True)
    first_name = Column(String(100), nullable=True, index=True)
    last_name = Column(String(100), nullable=True, index=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    age = Column(Integer, nullable=True)
    contact_datetime = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    source = Column(String(50), default="website") # "website", "manual", "voice"
    sex = Column(String(10), nullable=True) # "M", "F", "Other"
    is_archived = Column(Integer, default=0) # 0 = False, 1 = True (SQLite friendly)

    # Relationships
    user = relationship("User", back_populates="patients")
    appointments = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")
    interactions = relationship("Interaction", back_populates="patient", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Patient(name={self.name}, phone={self.phone})>"


# 📅 Appointment system
class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)

    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    datetime = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(50), default="scheduled", index=True)

    doctor_name = Column(String(120), nullable=True)  # UI only
    reason = Column(String(255), nullable=True)
    denial_reason = Column(Text, nullable=True) # Reason for rescheduling/denial

    reminder_level = Column(Integer, default=0)
    follow_up_reason = Column(Text, nullable=True)
    follow_up_status = Column(String(50), nullable=True) # "completed", "missed", "rescheduled"

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("User", back_populates="appointments")

    def __repr__(self):
        return f"<Appointment(id={self.id}, patient_id={self.patient_id}, doctor_id={self.doctor_id}, status={self.status})>"


# 💬 Interaction logs (e.g., SMS, chatbot, or call logs)
class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    channel = Column(String(50), nullable=False) # e.g., 'sms', 'chat', 'email'
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", back_populates="interactions")

    def __repr__(self):
        return f"<Interaction(channel={self.channel}, message_length={len(self.message)})>"

class SymptomCluster(Base):
    __tablename__ = "symptom_clusters"
    id = Column(Integer, primary_key=True, index=True)
    canonical_name = Column(String, nullable=True)
    display_name = Column(String, nullable=True)
    info = Column(JSON, default={})
    centroid = Column(LargeBinary, nullable=True)
    count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class SymptomExample(Base):
    __tablename__ = "symptom_examples"
    id = Column(Integer, primary_key=True, index=True) 
    cluster_id = Column(Integer, ForeignKey("symptom_clusters.id"))
    text = Column(String, nullable=False)
    vector = Column(LargeBinary, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    cluster = relationship("SymptomCluster", backref="examples")

class LLMInteraction(Base):
    __tablename__ = "llm_interactions"
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, unique=True)
    doctor_id = Column(String)
    query = Column(String)
    response = Column(Text)
    context_used = Column(Text)
    action_id = Column(Integer, nullable=True)
    prompt_variant = Column(Integer, nullable=True)
    temp_used = Column(Float, nullable=True)
    model_used = Column(String, nullable=True)
    ctx_size_used = Column(Integer, nullable=True)
    semantic_similarity = Column(Float, nullable=True)
    groundedness = Column(Float, nullable=True)
    instruction_score = Column(Float, nullable=True)
    safety_score = Column(Float, nullable=True)
    coherence_score = Column(Float, nullable=True)
    accuracy_score = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Prescription(Base):
    __tablename__ = "prescriptions"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    details = Column(Text, nullable=True) # Legacy / Catch-all
    diagnosis = Column(Text, nullable=True)
    treatment_plan = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True) # Dedicated field for patient instructions
    linked_to = Column(Integer, ForeignKey("prescriptions.id", ondelete="SET NULL"), nullable=True) # Links to original prescription for continuations
    xrays = Column(JSON, default=[]) # List of filenames or URLs for X-ray images
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    patient = relationship("Patient")
    doctor = relationship("User")

# 📄 Invoicing and Billing System
class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(50), unique=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True) # The dentist who provided service
    
    date = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    currency = Column(String(10), default="INR")
    discount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0) # Calculated as sum(items) - discount
    status = Column(String(50), default="unpaid", index=True) # "unpaid", "partially_paid", "paid"

    # Relationships
    patient = relationship("Patient")
    doctor = relationship("User")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payment_records = relationship("PaymentRecord", back_populates="invoice", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Invoice(id={self.id}, number={self.invoice_number}, patient_id={self.patient_id})>"

class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    
    treatment_name = Column(String(200), nullable=False)
    treatment_date = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    cost = Column(Float, nullable=False)
    discount = Column(Float, default=0.0)

    invoice = relationship("Invoice", back_populates="items")

class PaymentRecord(Base):
    __tablename__ = "payment_records"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    
    receipt_number = Column(String(50), unique=True, index=True)
    paid_on = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    payment_method = Column(String(50), nullable=False) # "UPI", "Cash", "Card", etc.
    amount = Column(Float, nullable=False)

    invoice = relationship("Invoice", back_populates="payment_records")

class TriageResult(Base):
    __tablename__ = "triage_results"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    symptoms = Column(Text, nullable=False)
    urgency = Column(String(50)) # emergency, soon, routine
    probable_issue = Column(String(255))
    recommended_dept = Column(String(100))
    ai_reasoning = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient")

    def __repr__(self):
        return f"<TriageResult(patient_id={self.patient_id}, urgency={self.urgency})>"

class TreatmentCatalog(Base):
    __tablename__ = "treatment_catalog"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False)
    default_cost = Column(Float, nullable=False)
    category = Column(String(100), nullable=True)
