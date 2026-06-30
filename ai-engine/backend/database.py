"""
Database configuration and ORM models for GIIPS.

Defines the SQLAlchemy engine, session maker, base declarative,
and the Complaint and Incident models.
"""

import datetime
from pathlib import Path
from sqlalchemy import create_engine, Column, String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Determine the absolute database directory and file path
# ai-engine/backend/database.py -> DB_DIR resolves to ai-engine/data
DB_DIR = Path(__file__).parent.parent / 'data'
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / 'giips.db'

DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create the engine with connect_args for SQLite multi-thread support
# Added pooling configuration for Render deployment
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
    pool_recycle=300
)

# Create the session local session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base class for models
Base = declarative_base()

import uuid
import datetime

# ... (rest of imports)

# Declarative base class for models
Base = declarative_base()

# Add User Model
class User(Base):
    """ORM model representing a platform user."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    district = Column(String, nullable=True)
    ward = Column(String, nullable=True)
    role = Column(String, nullable=False) # 'Citizen', 'Officer', 'Executive'
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    status = Column(String, default="active", nullable=False)

# Seed demo users
def seed_demo_users():
    from auth_service import hash_password
    db = SessionLocal()
    
    users = [
        {"full_name": "Government Officer", "email": "officer@giips.gov.in", "role": "Officer", "password": "password123"},
        {"full_name": "District Collector", "email": "collector@giips.gov.in", "role": "Executive", "password": "password123"}
    ]
    
    for user in users:
        if not db.query(User).filter(User.email == user["email"]).first():
            new_user = User(
                id=str(uuid.uuid4()),
                full_name=user["full_name"],
                email=user["email"],
                password_hash=hash_password(user["password"]),
                role=user["role"]
            )
            db.add(new_user)
    db.commit()
    db.close()

# Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

Base.metadata.create_all(bind=engine)
seed_demo_users()



class Incident(Base):
    """ORM model representing an aggregated Incident of multiple grouped complaints."""
    __tablename__ = "incidents"

    id = Column(String, primary_key=True, index=True)
    incident_number = Column(String, unique=True, index=True, nullable=False)
    category = Column(String, nullable=False)
    ward = Column(String, nullable=False)
    cluster_size = Column(Integer, default=1, nullable=False)
    priority_score = Column(Float, default=0.0, nullable=False)
    priority_label = Column(String, default="Low", nullable=False)
    summary = Column(Text, nullable=True)
    status = Column(String, default="open", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # Relationship to linked complaints
    complaints = relationship("Complaint", back_populates="incident")
    priority_history = relationship("PriorityHistory", backref="incident")


class Complaint(Base):
    """ORM model representing an individual citizen complaint."""
    __tablename__ = "complaints"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String, nullable=False)
    ward = Column(String, nullable=False)
    image_path = Column(String, nullable=True)
    predicted_category = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    priority = Column(String, nullable=True)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    # Sprint 5: Explainability fields
    similarity_score = Column(Float, nullable=True)
    merge_reason = Column(Text, nullable=True)
    merged_at = Column(DateTime, nullable=True)

    # Relationship back to the aggregated incident
    incident = relationship("Incident", back_populates="complaints")

class PriorityHistory(Base):
    """ORM model for incident priority change history."""
    __tablename__ = "priority_history"

    id = Column(String, primary_key=True, index=True)
    incident_id = Column(String, ForeignKey("incidents.id"), index=True, nullable=False)
    old_score = Column(Float, nullable=False)
    new_score = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    changed_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
