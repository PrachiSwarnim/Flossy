from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime, timezone


# 🧩 User table for Clerk-authenticated users
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    role = Column(String(50), nullable=True) # "dentist" or "patient"
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    patients = relationship("Patient", back_populates="user", cascade="all, delete-orphan")

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
    datetime = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="scheduled")
    doctor_name = Column(String(120), nullable=False, default="Dr. Ava Sharma") # NEW COLUMN
    patient = relationship("Patient", back_populates="appointments")

    def __repr__(self):
        return f"<Appointment(patient_id={self.patient_id}, status={self.status}, datetime={self.datetime})>"


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