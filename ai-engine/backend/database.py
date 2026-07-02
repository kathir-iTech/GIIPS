"""
Database configuration and ORM models for GIIPS.

Defines the SQLAlchemy engine, session maker, base declarative,
and the Complaint and Incident models.
"""

import uuid
import datetime
import random
from datetime import timedelta
from pathlib import Path
from sqlalchemy import create_engine, Column, String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Determine the absolute database directory and file path
DB_DIR = Path(__file__).parent.parent / 'data'
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / 'giips.db'

DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create the engine with connect_args for SQLite multi-thread support
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

TAMIL_NADU_DISTRICTS = [
    "Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore", "Dharmapuri",
    "Dindigul", "Erode", "Kallakurichi", "Kanchipuram", "Kanyakumari", "Karur",
    "Krishnagiri", "Madurai", "Nagapattinam", "Nilgiris", "Namakkal", "Perambalur",
    "Pudukkottai", "Ramanathapuram", "Ranipet", "Salem", "Sivagangai", "Tenkasi",
    "Thanjavur", "Theni", "Thoothukudi", "Tiruchirappalli", "Tirunelveli", "Tirupathur",
    "Tiruppur", "Tiruvannamalai", "Tiruvil", "Trichy", "Vellore", "Viluppuram",
    "Virudhunagar"
]

COMPLAINT_TEMPLATES = {
    "Roads": [
        "Pothole on main road causing vehicle damage",
        "Road surface damaged requiring immediate repair",
        "Dangerous road condition with deep craters",
        "Speed breaker too high causing undercarriage damage"
    ],
    "Water Supply": [
        "No water supply for past 3 days",
        "Brownish water coming from taps",
        "Water supply disrupted due to pipe burst",
        "Low water pressure affecting daily routine"
    ],
    "Drainage": [
        "Drainage outlet clogged with plastic waste",
        "Open drain overflowing during rains",
        "Drain cover missing creating hazard",
        "Blockage causing water stagnation"
    ],
    "Streetlights": [
        "LED street light not functioning for a week",
        "Multiple street lights out in the area",
        "Street light pole bent due to vehicle impact",
        "Light pole sparking dangerously"
    ],
    "Garbage": [
        "Garbage collection missed for 2 weeks",
        "Overflowing garbage bins near market",
        "Construction debris dumped illegally",
        "No garbage pickup service in our ward"
    ],
    "Public Health": [
        "Stagnant water causing mosquito breeding",
        "Public toilets not cleaned regularly",
        "Health hazard due to poor sanitation",
        "Dengue prevention measures needed"
    ],
    "Electricity": [
        "Frequent power cuts during evening hours",
        "Transformer failure causing blackout",
        "Voltage fluctuation damaging appliances",
        "Street lights not getting power supply"
    ]
}

PRIORITY_LABELS = ["Critical", "High", "Medium", "Low"]
PRIORITY_WEIGHTS = [0.1, 0.25, 0.4, 0.25]

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
    recommended_action = Column(Text, nullable=True)
    days_open = Column(Integer, default=0, nullable=False)
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
    user_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
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

# Seed demo users
def seed_demo_users():
    from auth_service import hash_password
    db = SessionLocal()
    
    users = [
        {"full_name": "Government Officer", "email": "officer@giips.gov.in", "role": "Officer", "password": "password123"},
        {"full_name": "District Collector", "email": "collector@giips.gov.in", "role": "Executive", "password": "password123"},
        {"full_name": "Demo Citizen", "email": "citizen@giips.gov.in", "role": "Citizen", "password": "password123"}
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

def seed_synthetic_data(num_complaints: int = 10000, duplicate_rate: float = 0.15):
    """Generate and seed synthetic Tamil Nadu governance data."""
    db = SessionLocal()
    
    try:
        existing_count = db.query(Complaint).count()
        if existing_count > 0:
            print(f"Database already has {existing_count} complaints, skipping seed")
            return
    except:
        pass
    
    complaints = []
    incidents = []
    
    citizen = db.query(User).filter(User.role == 'Citizen').first()
    citizen_id = citizen.id if citizen else None
    
    for i in range(num_complaints):
        category = random.choice(list(COMPLAINT_TEMPLATES.keys()))
        district = random.choice(TAMIL_NADU_DISTRICTS)
        ward = f"Ward {random.randint(1, 20)}"
        
        complaint = Complaint(
            id=f"COMP-{i+1:06d}",
            title=f"{category} issue in {ward}",
            description=random.choice(COMPLAINT_TEMPLATES[category]),
            location=f"{ward}, {district}",
            ward=ward,
            predicted_category=category,
            priority=random.choices(PRIORITY_LABELS, weights=PRIORITY_WEIGHTS)[0],
            created_at=datetime.datetime.utcnow() - timedelta(days=random.randint(0, 60)),
            latitude=round(11.0 + random.random() * 3.0, 6),
            longitude=round(77.0 + random.random() * 2.0, 6),
            user_id=citizen_id
        )
        complaints.append(complaint)
    
    for c in complaints:
        db.add(c)
    db.commit()
    
    for i in range(min(150, num_complaints // 10)):
        district = random.choice(TAMIL_NADU_DISTRICTS)
        ward = f"Ward {random.randint(1, 20)}"
        category = random.choice(list(COMPLAINT_TEMPLATES.keys()))
        
        incident = Incident(
            id=f"INC-{i+1:06d}",
            incident_number=f"INC-{i+1:06d}",
            category=category,
            ward=ward,
            cluster_size=random.randint(3, 25),
            priority_score=round(random.uniform(30, 95), 1),
            priority_label=random.choices(PRIORITY_LABELS, weights=PRIORITY_WEIGHTS)[0],
            summary=f"Cluster of {category.lower()} complaints in {ward}",
            status=random.choice(["open", "in-progress", "resolved"]),
            recommended_action=f"Deploy maintenance crew to address {category.lower()}",
            days_open=random.randint(1, 30)
        )
        incidents.append(incident)
    
    for inc in incidents:
        db.add(inc)
    db.commit()
    
    print(f"Seeded database with {len(complaints)} complaints and {len(incidents)} incidents")
    db.close()

def backfill_complaint_user_ids():
    """Assign existing complaints without user_id to the demo citizen account."""
    db = SessionLocal()
    try:
        citizen = db.query(User).filter(User.role == 'Citizen').first()
        if not citizen:
            print("No citizen user found for backfill")
            return
        updated = db.query(Complaint).filter(Complaint.user_id.is_(None)).update({Complaint.user_id: citizen.id})
        db.commit()
        if updated:
            print(f"Backfilled {updated} complaints to citizen {citizen.email}")
    except Exception as e:
        print(f"Backfill error: {e}")
        db.rollback()
    finally:
        db.close()

Base.metadata.create_all(bind=engine)
seed_demo_users()
seed_synthetic_data()

def migrate_add_user_id():
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    try:
        cols = [c['name'] for c in inspector.get_columns('complaints')]
        if 'user_id' not in cols:
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE complaints ADD COLUMN user_id VARCHAR'))
                conn.commit()
    except Exception:
        pass

try:
    migrate_add_user_id()
except Exception:
    pass

try:
    backfill_complaint_user_ids()
except Exception:
    pass