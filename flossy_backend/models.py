from email.policy import default
import string
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, JSON, LargeBinary, Float
from sqlalchemy.orm import relationship, sessionmaker
from database import DATABASE_URL, Base
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 🧩 User table for Clerk-authenticated users
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
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
    name = Column(String(120), nullable=False)
    phone = Column(String(20), unique=True, nullable=False)
    contact_datetime = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

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

    datetime = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="scheduled")

    doctor_name = Column(String(120), nullable=True)  # UI only
    reason = Column(String(255), nullable=True)

    reminder_level = Column(Integer, default=0)
    follow_up_reason = Column(Text, nullable=True)

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
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

class SymptomExample(Base):
    __tablename__ = "symptom_examples"
    id = Column(Integer, primary_key=True, index=True) 
    cluster_id = Column(Integer, ForeignKey("symptom_clusters.id"))
    text = Column(String, nullable=False)
    vector = Column(LargeBinary, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

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
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

def final_score(row: LLMInteraction):
    e = row.explicit_reward or 0
    i = row.implicit_reward or 0
    a = (row.audit_score / 5) if row.audit_score else 0

    return 0.5*e + 0.3*i + 0.2*a
    
if __name__=="__main__":
    Base.metadata.create_all(bind=engine)
    print("Created tables (if not exist) in", DATABASE_URL)