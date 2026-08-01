"""
Database configuration and ORM models for GIIPS.

Defines the SQLAlchemy engine, session maker, base declarative,
and the Complaint and Incident models.
"""

import uuid
import datetime
import os
import random
from datetime import timedelta
from pathlib import Path
from sqlalchemy import create_engine, Column, String, Integer, Float, Text, DateTime, ForeignKey, Boolean, or_, func, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

DB_DIR = Path(__file__).parent.parent / 'data'
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / 'giips.db'

DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{DB_PATH}"

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
        pool_recycle=300,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ── Coimbatore City Municipal Corporation (CCMC) ward data ─────────────────
# All 100 real wards across 5 zones, sourced from ccmc.gov.in delimitation.
from coimbatore_wards import (
    WARDS, WARD_BY_NUMBER, ZONE_BY_WARD, AREAS_BY_WARD,
    ALL_WARD_NUMBERS, WARDS_BY_ZONE, ZONES, AREA_TO_WARD, ward_for_area,
)

# ── Civic-only complaint templates keyed to real Coimbatore areas ─────────
# Every template references a Coimbatore landmark or area name so the
# seed_synthetic_data() generator can correctly map it to its real ward+zone.
# Non-civic / personal / interpersonal categories are excluded.

CCMC_COMPLAINT_TEMPLATES = {
    "Roads": [
        "Pothole on Sathy Road near Hope College junction damaging vehicles",
        "Road surface crumbled on Avinashi Road near L&T Bypass needs immediate repair",
        "Deep crater on Mettupalayam Road near Sungam causing accidents at night",
        "Speed breaker too high on Trichy Road near KNG Pudur damaging car undercarriage",
        "Road cave-in on Thadagam Road near Vadavalli junction after recent rains",
        "Patchwork repair on Sathy Road near Saravanampatti already caved within a week",
        "Gravel and broken bitumen on Mettupalayam Road near Ganapathy due to lorry traffic",
        "Car damaged hitting pothole on Avinashi Road near Lakshmi Mills junction",
        "Speed breaker not painted on Pollachi Road near Kuniyamuthur invisible at night",
        "Road washed out on Maruthamalai Road near Iyyampalayam after last downpour",
        "Buses swerving to avoid craters on Trichy Road near Singanallur stretch",
        "Two-wheeler slipped on loose gravel on Thadagam Road near Rathinapuri",
        "Half-hearted patch on Sathy Road near Chinnavedampatti collapsed in two days",
        "Deep pothole near Gandhipuram bus stand causing traffic snarls every evening",
        "Broken road on service lane of Sathy Road near Kalapatti with no warning signage",
        "Road near Ukkadam bus stand completely broken after heavy vehicle movement",
        "Waterlogging turns potholes into invisible traps on Trichy Road near Irugur",
        "Road relaying badly needed on Pollachi Road near Eachanari whole stretch affected",
        "Truck broke road while digging water line on Sathy Road near Thudiyalur",
        "Bikers falling daily on bad stretch near Ganapathy junction no action taken",
        "Road completely washed away near Perur temple road after monsoon rain",
        "Pothole near Race Course junction causing vehicle tyre damage every day",
        "Loose gravel on Maruthamalai Road near Vadavalli making bike riding risky",
        "Road in front of CCMC office in poor condition ironic for corporation road",
        "Footpath near Town Hall encroached by vendors forcing pedestrians onto busy road",
        "Stretch of road between RS Puram and Gandhipuram completely broken after water works",
    ],
    "Water Supply": [
        "No water supply for past 3 days in Thudiyalur area entire street affected",
        "Brownish muddy water coming from taps in Saravanampatti since last week",
        "Water supply disrupted due to pipe burst on Sathy Road near Ganapathy",
        "Low water pressure in RS Puram affecting daily routine upper floors get no water",
        "Borewell supplying Vadavalli colony broken motor not working for a week",
        "Tankers not coming to Kuniyamuthur area for 5 days residents buying water daily",
        "Pipeline laid by TWAD on Avinashi Road already burst again near Peelamedu",
        "Water contamination reported after sewage pipe broke near Ukkadam lake",
        "No regular water supply in Singanallur for 15 days despite paying full bills",
        "Water supplied once in 4 days at 2 AM in Gandhipuram residents can't collect",
        "Complaint to CCMC water division in Ramanathapuram no response getting nowhere",
        "Water pressure so low can't fill overhead tank on fourth floor in RS Puram",
        "Sewage water mixing with drinking water supply in Kuniyamuthur very dangerous",
        "Newly laid pipeline in Vellalore has leakage wasting water all day",
        "TDS levels very high in supplied water in Thudiyalur white deposit on utensils",
        "Water board officials ignoring written complaints in Perur for last 10 days",
        "Water supplied only at 4 AM in Vadavalli when no one awake to collect",
        "Brownish smelly water from taps in Singanallur since festival season",
        "Pressurised supply causing pipe bursts at multiple homes in Eachanari",
        "Water stagnation in sump due to irregular supply breeding mosquitoes in Ganapathy",
        "Residents of Saravanampatti forced to buy mineral water for drinking cooking",
        "No warning before 2-day water cut in Race Course only informed through newspaper",
        "Contaminated water with sewage floaters visible in Peelamedu colony",
        "Prolonged no water in Kalapatti residents walking 500m to public tap",
        "Overhead tank overflowing in Thudiyalur no telemetry system in the ward",
    ],
    "Waste Management": [
        "Garbage collection missed for 2 weeks in Saravanampatti streets stinking bad",
        "Overflowing garbage bins at Gandhipuram bus stand unhygienic foul smell everywhere",
        "Construction debris dumped illegally on service road near Vadavalli bypass",
        "No garbage pickup in Kovaipudur for 20 days waste piling up on streets",
        "Garbage truck comes only once a month to Thudiyalur west side residents suffering",
        "Wet and dry waste mixed up by collection staff in Ganapathy again today",
        "Garbage bins missing on Sathy Road near Chinnavedampatti no place to dump",
        "Kids falling sick due to rotting garbage near school in RS Puram",
        "Garbage dump near water tank in Kuniyamuthur residents forced to buy bottled water",
        "Waste contractor not attending phones in Ramanathapuram complaints ignored",
        "Overflowing bin near Ukkadam bus stop very unhygienic attracting stray dogs",
        "Residents throwing garbage into storm water drain in Vellalore no collection service",
        "Garbage dumped on vacant site near Perur temple breeding mosquitoes",
        "Waste collection vehicle too small for entire ward in Vadavalli",
        "Household waste piled up near temple entrance in Rathinapuri residents burning it",
        "CCMC workers come only for photos after media reports no actual work on ground",
        "Vegetable market waste piled up near Singanallur bus stop polluting road",
        "Collection staff demand extra money for lifting bulk waste in Race Course",
        "Stray dogs tearing garbage bags near school in Peelamedu every evening",
        "Sweepers not coming for past week in Thudiyalur streets stinking in summer",
        "Plastic waste dumped near Perur temple tank no segregation done at all",
        "Compost pit overflowing with mixed waste near Vadavalli ward office",
        "Waste collection time never followed in Gandhipuram truck comes irregularly",
        "Garbage bins shifted from street to empty plot causing blockage in Eachanari",
        "Dead animals not picked up by CCMC near Trichy Road foul smell spreading",
    ],
    "Sanitation": [
        "Drainage outlet clogged with plastic waste on Sathy Road near Saravanampatti",
        "Open drain overflowing during rains entering homes in Ganapathy colony",
        "Drain cover missing on Avinashi Road near Peelamedu hazard for pedestrians",
        "Blocked drain causing water stagnation and smell near Gandhipuram bus stand",
        "Drainage channel choked with construction debris on Mettupalayam Road bypass",
        "Stagnant water in open drain near school in Vadavalli health risk for children",
        "Manhole cover broken for 3 weeks on Trichy Road near Irugur very dangerous",
        "Rainwater mixing with sewage due to choked drain in RS Puram",
        "Encroachment of drain by shopkeepers in Ukkadam causing water logging every rain",
        "Desilting of main drain desperately needed before monsoon in Singanallur",
        "Stinking drain water on Pollachi Road near Kuniyamuthur market no action taken",
        "Drainage clogged by plastic waste after festival in Thudiyalur",
        "Cover missing on storm water drain near Perur temple entrance danger for kids",
        "Mosquito breeding in standing drain water in Vellalore colony",
        "Child fell into open drain in Rathinapuri cover missing for over a month",
        "Choked drain behind apartments in Race Course releasing bad odour whole day",
        "Rains bring sewage water into ground floor homes in Eachanari western extension",
        "Water logging for 3 hours every rain near Vadavalli bus terminus due to choked drain",
        "Overflowing drain near market in Thudiyalur health department please act",
        "Silt in storm water drain not cleared from past year in Saravanampatti",
        "Covered drain reopened for repair not closed back in Ganapthy bridge area",
        "Drainage maintenance on paper no desilting done ground in Kuniyamuthur",
        "Chicken shop waste thrown into drainage near cinema road in Singanallur",
        "Cross drainage near bridge at Eachanari choked no water outlet during rains",
        "Sewage drain broken near market in Vadavalli causing fly infestation",
    ],
    "Street Lighting": [
        "LED street light not working for a week near Gandhipuram bus stand road",
        "Multiple street lights out on Sathy Road near Ganapthy for past month",
        "Street light pole bent by vehicle impact on Avinashi Road near Peelamedu",
        "Light pole sparking dangerously during rain near RS Puram junction",
        "Entire stretch of Maruthamalai Road dark after 8 PM women scared to walk",
        "LED light flickering continuously near Thudiyalur tank disturbing sleep at night",
        "No streetlight on service road near Vadavalli stretch pitch dark after sunset",
        "Street light pole tilting dangerously after lorry hit on Trichy Road",
        "Newly installed LED on Sathy Road not working from day one near Saravanampatti",
        "Most streetlights not working on NSTV road near Kalapatti depot",
        "Fuse box issue causing all 5 lights on lane to go off after every rain",
        "Street light cable cut during road digging near Vellalore colony",
        "No light on pedestrian subway near Ukkadam bus stand back entrance",
        "Street light not working for 3 months near Singanallur police station",
        "Half the lights on Mettupalayam Road flicker intermittently near Ganapathy",
        "Light pole grounding creating electric shock risk near Kovaipudur school",
        "Complete darkness on Pollachi Road near Kuniyamuthur after 7 PM accidents risk",
        "Streetlight wires hanging low near Eachanari arcot road touching ground",
        "Only 1 of 4 pole lights working on Perur temple road western end",
        "Too dim light near Vadavalli hospital forcing relatives to use mobile phones",
        "Underground cable damaged during road work no light for 2 weeks in Rathinapuri",
        "Street light at Irugur signal dead causing accident risk at night",
        "Kids cannot play safely outside due to no working light in Thudiyalur colony",
        "No light on link road between Saravanampatti and Chinnavedampatti pitch dark",
        "Multiple damaged poles on road to Eachanari no maintenance since years",
    ],
    "Electricity": [
        "Frequent power cuts during evening hours affecting students in RS Puram",
        "Transformer failure near Gandhipuram bus stand blackout 100 families affected",
        "Voltage fluctuation damaging fridge and TV in Ganapthy for past week",
        "Street lights not getting power on Town Hall road for days",
        "Low voltage causing motor burn in borewell in Vadavalli at morning time",
        "Entire street dark due to fuse off at midnight near Thudiyalur school road",
        "Underground cable snapped during road work near Peelamedu outage for 3 days",
        "Power cut for 3 hours every alternate day in Saravanampatti no notice given",
        "Transformer oil leak creating fire risk near Singanallur junction urgent",
        "Electric pole leaning dangerously after heavy rain in Kuniyamuthur",
        "Meter box sparking when plugging geyser in Race Course residents scared",
        "Low income families most affected by long power cuts in Vellalore",
        "No street light after transformer blast at Eachanari bridge",
        "Frequent tripping due to illegal power draw by shop in Ukkadam",
        "TANGEDCO staff not arriving for scheduled repair in Ramanathapuram since days",
        "Streetlight dim because of load shedding in Gandhipuram colony dark nights",
        "Single power line serving 200 homes old infrastructure in Thudiyalur frequent failure",
        "TANGEDCO staff demanding bribe for new connection in Kalapatti",
        "Overloaded transformer sparking near Perur vegetable market dangerous area",
        "Power cut scheduled at 2 AM unsuitable for students in RS Puram exam season",
        "Underground cable waterlogged due to rain in Vadavalli third outage this month",
        "Power restoration after storm took 18 hours in Saravanampatti unbearable summer",
        "Three phase current imbalance causing motor vibration in Ganapathy",
        "Live wire hanging low near Mettupalayam Road junction construction site risky",
        "Transformer replacement done only after media report otherwise no action in Kuniyamuthur",
    ],
    "Public Health": [
        "Stagnant water near Vadavalli colony breeding mosquitoes risk of dengue",
        "Public toilet near Gandhipuram bus stand not cleaned regularly unhygienic",
        "Health hazard due to open garbage near school in RS Puram very serious",
        "Dengue prevention fogging not done in Saravanampatti for over a month",
        "Drainage water stagnant near Eachanari hospital creating mosquito menace",
        "Stray dog population increasing near Ukkadam market no catch van deployed",
        "Rat infestation in old residential area of Thudiyalur very bad situation",
        "Water contamination causing stomach illness in Singanallur locality",
        "No mosquito fogging done in Kuniyamuthur despite repeated dengue cases reported",
        "Overflowing public toilet at Perur temple health department please act",
        "Pest control needed for termites in government school building in Ganapathy",
        "Construction dust causing breathing trouble in Peelamedu locality no action",
        "Stray cattle on road near Vadavalli causing accidents and traffic daily",
        "Plastic waste burned openly near residential colony in Kalapatti toxic fumes",
        "Flies from garbage dump near Kovaipudur clinic making patient recovery hard",
        "Sewage treatment plant near Nanjundapuram not working residents suffering since months",
        "Open drain with sewage right in front of apartment entrance in Race Course",
        "Methane gas smell near dump yard in Vellalore residents severely affected",
        "Water stagnation near Eachanari road breeding mosquitoes in large numbers",
        "Public health camp needed for workers at SIDCO industrial estate",
        "Stray dogs entering garbage dump in Rathinapuri spreading waste on road",
        "No dustbins near Thudiyalur bus stand causing littering and health risk",
        "Waterborne disease spreading in Kuniyamuthur slum needs medical team urgently",
        "Accumulated hospital waste behind private nursing home in Ganapathy unsanitary",
        "Air quality poor near SIDCO estate due to industrial smoke residents falling sick",
    ],
}

# Sentence-initial variations so no two seeded rows have identical text
# while preserving category semantics for meaningful duplicate detection.
_TEMPLATE_SUFFIXES = [
    "This has been reported multiple times by residents in the area.",
    "Local residents are very concerned about the ongoing situation.",
    "Immediate attention requested from the concerned ward councillor.",
    "This issue is causing significant inconvenience to the public.",
    "Multiple households affected; please treat as a priority complaint.",
    "Complaint raised by citizen during morning walk; situation worsening daily.",
    "Issue persists despite earlier complaint — escalation required urgently.",
    "Elderly residents and children particularly affected by this problem.",
    "We have raised this before but no corrective action taken on ground.",
    "Situation critical especially during monsoon / peak summer season.",
    "Nearby commercial establishments also impacted by this civic failure.",
    "Photos and details shared with CCMC; public attention growing.",
    "Ward councillor has been informed — awaiting departmental response.",
    "Residents association has formally written to CCMC zonal office.",
    "This is a recurring complaint in this ward for several months now.",
    "Health and safety hazard; request emergency response from authorities.",
    "Area residents held small meeting and decided to escalate collectively.",
    "Multiple calls to CCMC helpline went unanswered — complaint registered now.",
    "Complaint raised on behalf of senior citizens living in the vicinity.",
]

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
    department = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    status = Column(String, default="active", nullable=False)
    notify_status_updates = Column(Boolean, default=True, nullable=False)
    availability = Column(String, default="available", nullable=False)
    skills = Column(String, nullable=True)
    zone = Column(String, nullable=True)

    # FEATURE 14: email verification
    verification_code = Column(String, nullable=True)
    email_verified = Column(Boolean, default=False, nullable=False)

    # FEATURE 15: shift schedule
    current_shift = Column(String, nullable=True)

    # FEATURE 2: login streak
    login_streak = Column(Integer, default=0, nullable=False)
    show_on_leaderboard = Column(Boolean, default=False, nullable=False)

    # FEATURE 4: citizen trust score
    trust_score = Column(Float, default=50.0, nullable=False)

class Incident(Base):
    """ORM model representing an aggregated Incident of multiple grouped complaints."""
    __tablename__ = "incidents"

    id = Column(String, primary_key=True, index=True)
    incident_number = Column(String, unique=True, index=True, nullable=False)
    category = Column(String, nullable=False)
    original_category = Column(String, nullable=True)
    ward = Column(String, nullable=False)
    cluster_size = Column(Integer, default=1, nullable=False)
    priority_score = Column(Float, default=0.0, nullable=False)
    priority_label = Column(String, default="Low", nullable=False)
    summary = Column(Text, nullable=True)
    status = Column(String, default="open", nullable=False)
    status_changed_at = Column(DateTime, nullable=True)
    recommended_action = Column(Text, nullable=True)
    days_open = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # Escalation fields
    escalated = Column(Boolean, default=False, nullable=False)
    escalated_at = Column(DateTime, nullable=True)
    escalated_by = Column(String, nullable=True)
    escalation_reason = Column(Text, nullable=True)

    # Citizen verification for resolution
    verification_code = Column(String, nullable=True)

    # Resolution note — officer's comment when marking resolved
    resolution_note = Column(Text, nullable=True)

    # Resolution quality score
    resolution_quality_score = Column(Float, nullable=True)

    # Resolution photo
    resolution_photo_path = Column(String, nullable=True)

    # Private officer notes
    private_note = Column(Text, nullable=True)
    private_note_updated_at = Column(DateTime, nullable=True)

    # Citizen appeal fields
    appealed = Column(Boolean, default=False, nullable=False)
    appeal_reason = Column(Text, nullable=True)
    appealed_at = Column(DateTime, nullable=True)

    # Multi-ward incident linking (Feature 8)
    affected_wards = Column(Text, nullable=True)

    # Officer acceptance (Feature 15)
    accepted_by = Column(String, nullable=True)
    accepted_at = Column(DateTime, nullable=True)

    # FEATURE 11: sibling incident
    sibling_of = Column(String, nullable=True)

    # FEATURE 17: Impact assessment
    impact_score = Column(Float, nullable=True)
    economic_impact = Column(Float, nullable=True)
    beneficiaries = Column(Integer, nullable=True)

    # FEATURE 7: estimated remediation cost
    estimated_cost = Column(Float, nullable=True)

    # F1: severity auto-escalation to media — high-impact incidents flagged for public attention
    public_attention_flag = Column(Boolean, default=False, nullable=False)

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
    address = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Sprint 5: Explainability fields
    similarity_score = Column(Float, nullable=True)
    merge_reason = Column(Text, nullable=True)
    merged_at = Column(DateTime, nullable=True)

    # Photo duplicate detection fields
    photo_hash = Column(String, nullable=True, index=True)
    photo_duplicate_flag = Column(String, nullable=True)
    photo_duplicate_of = Column(String, nullable=True)

    # Citizen satisfaction rating (1-5, set once after resolution verification)
    citizen_rating = Column(Integer, nullable=True)

    # Tags (JSON array stored as string, max 3)
    tags = Column(Text, nullable=True)

    # FEATURE 14: location accuracy
    location_accuracy = Column(String, nullable=True)

    # Complaint language detection
    complaint_language = Column(String, nullable=True)

    # Complexity score fields
    complexity_score = Column(Float, nullable=True)
    complexity_label = Column(String, nullable=True)

    # Urgency flag (set by ML pipeline)
    urgency_flag = Column(String, nullable=True, default="LOW")

    # FEATURE 8: multi-photo
    photo_paths = Column(Text, nullable=True)

    # FEATURE 11: predicted resolution time
    predicted_resolution_days = Column(Float, nullable=True)

    # FEATURE 10: resubmission
    resubmission_of = Column(String, nullable=True)

    # F12: follow-up count
    follow_up_count = Column(Integer, default=0, nullable=False)

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

class AuditLog(Base):
    """ORM model for audit log entries."""
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    user_id = Column(String, nullable=True)
    user_email = Column(String, nullable=True)
    role = Column(String, nullable=True)
    action = Column(String, nullable=False)
    target = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    status = Column(String, default="success", nullable=False)
    ip_address = Column(String, nullable=True)

class DepartmentMetrics(Base):
    """ORM model for department-level metrics."""
    __tablename__ = "department_metrics"

    id = Column(String, primary_key=True, index=True)
    department = Column(String, nullable=False)
    open_incidents = Column(Integer, default=0, nullable=False)
    critical_incidents = Column(Integer, default=0, nullable=False)
    assigned_officers = Column(Integer, default=0, nullable=False)
    avg_resolution_time = Column(Float, default=0.0, nullable=False)
    completion_percentage = Column(Float, default=0.0, nullable=False)
    workload_indicator = Column(Float, default=0.0, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

class Notification(Base):
    """ORM model for in-app citizen notifications."""
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)
    complaint_id = Column(String, ForeignKey("complaints.id"), nullable=True)
    type = Column(String, nullable=False)
    data = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    batched = Column(Boolean, default=False, nullable=False)

    # F7: smart notification grouping — group_id points at the group's lead notification
    group_id = Column(String, nullable=True, index=True)
    group_count = Column(Integer, default=1, nullable=False)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

class IncidentUpdate(Base):
    """Officer/Executive progress updates visible to citizens in tracking timeline."""
    __tablename__ = "incident_updates"

    id = Column(String, primary_key=True, index=True)
    incident_id = Column(String, ForeignKey("incidents.id"), index=True, nullable=False)
    user_id = Column(String, nullable=False)
    user_name = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    incident = relationship("Incident", backref="updates")

class IncidentComment(Base):
    __tablename__ = "incident_comments"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, ForeignKey('incidents.id'), nullable=False)
    user_id = Column(String, nullable=False)
    user_name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class KpiTarget(Base):
    __tablename__ = "kpi_targets"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    metric_name = Column(String, nullable=False)
    target_value = Column(Float, nullable=False)
    current_value = Column(Float, nullable=True)
    set_by = Column(String, nullable=False)
    set_at = Column(DateTime, default=datetime.datetime.utcnow)


class Geofence(Base):
    """ORM model representing an executive-defined circular geofence."""
    __tablename__ = "geofences"

    id = Column(String, primary_key=True, index=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    radius_meters = Column(Float, nullable=False)
    label = Column(String, nullable=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


# FEATURE 3: push notification structure
class PushSubscription(Base):
    __tablename__ = "push_subscriptions"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)
    endpoint = Column(String, nullable=False)
    p256dh = Column(String, nullable=False)
    auth = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# FEATURE 16: drafts
class ComplaintDraft(Base):
    __tablename__ = "complaint_drafts"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    ward = Column(String, nullable=True)
    category = Column(String, nullable=True)
    tags = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

# FEATURE 3: training feedback
class TrainingFeedback(Base):
    __tablename__ = "training_feedback"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    complaint_id = Column(String, ForeignKey("complaints.id"), nullable=True)
    original_text = Column(Text, nullable=False)
    predicted_category = Column(String, nullable=False)
    corrected_category = Column(String, nullable=False)
    corrected_at = Column(DateTime, default=datetime.datetime.utcnow)

# FEATURE 4: incident dependencies
class IncidentDependency(Base):
    __tablename__ = "incident_dependencies"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False)
    depends_on_id = Column(String, ForeignKey("incidents.id"), nullable=False)
    created_by = Column(String, nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# FEATURE 6: budget tracking
class KpiBudget(Base):
    __tablename__ = "kpi_budgets"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    department = Column(String, nullable=False)
    month = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    budget_allocated = Column(Float, default=0.0)
    budget_spent = Column(Float, default=0.0)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# FEATURE 9: merge suggestions
class MergeSuggestion(Base):
    __tablename__ = "merge_suggestions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False)
    suggested_merge_id = Column(String, ForeignKey("incidents.id"), nullable=False)
    similarity_score = Column(Float, nullable=False)
    status = Column(String, default="pending")
    dismissed_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# FEATURE 11: officer leave
class OfficerLeave(Base):
    __tablename__ = "officer_leave"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    officer_id = Column(String, ForeignKey("users.id"), nullable=False)
    date = Column(String, nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# FEATURE 16: webhooks
class Webhook(Base):
    __tablename__ = "webhooks"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    url = Column(String, nullable=False)
    events = Column(Text, nullable=False)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# FEATURE 17: ward risk history
class WardRiskHistory(Base):
    __tablename__ = "ward_risk_history"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ward = Column(String, nullable=False, index=True)
    risk_score = Column(Float, nullable=False)
    snapshot_at = Column(DateTime, default=datetime.datetime.utcnow)

# FEATURE 2: peer reviews
class PeerReview(Base):
    __tablename__ = "peer_reviews"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, nullable=False, index=True)
    reviewer_id = Column(String, nullable=False)
    reviewee_id = Column(String, nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# FEATURE 7: incident cost estimation — uses column on Incident (no new table)
# FEATURE 11: predicted resolution days — uses column on Complaint (no new table)
# FEATURE 13: alert configuration
class AlertConfig(Base):
    __tablename__ = "alert_configs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    exec_user_id = Column(String, nullable=False, index=True)
    alert_type = Column(String, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    threshold = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# FEATURE 15: response templates
class ResponseTemplate(Base):
    __tablename__ = "response_templates"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    officer_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# F6: incident watchlist for executives
class Watchlist(Base):
    __tablename__ = "watchlists"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    exec_user_id = Column(String, nullable=False, index=True)
    incident_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# F13: officer reassignment request
class IncidentReassignmentRequest(Base):
    __tablename__ = "incident_reassignment_requests"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, nullable=False, index=True)
    requesting_officer_id = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# F14: citizen complaint subscription
class ComplaintSubscription(Base):
    __tablename__ = "complaint_subscriptions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    complaint_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# F10: citizen referral system
class Referral(Base):
    __tablename__ = "referrals"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    referrer_user_id = Column(String, nullable=False, index=True)
    referred_email = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# F18: report scheduler
class ReportSchedule(Base):
    __tablename__ = "report_schedules"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    exec_user_id = Column(String, nullable=False, index=True)
    report_type = Column(String, nullable=False)
    frequency = Column(String, nullable=False)
    last_generated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# Seed demo users
def seed_demo_users():
    from auth_service import hash_password
    db = SessionLocal()

    users = [
        # ── Executive (District Collector - Coimbatore) ──
        {"full_name": "District Collector - Coimbatore", "email": "collector@giips.gov.in", "role": "Executive", "password": "password123", "department": None, "ward": None, "district": "Coimbatore"},

        # ── Department Officers (CCMC engineering wing, TWAD, TANGEDCO) ──
        {"full_name": "CCMC Engineer - Roads",           "email": "officer1@giips.gov.in",  "role": "Officer", "password": "password123", "department": "CCMC Engineering Wing", "ward": None, "district": "Coimbatore"},
        {"full_name": "TWAD Board - Water Supply",       "email": "officer2@giips.gov.in",  "role": "Officer", "password": "password123", "department": "TWAD Board - Coimbatore Division", "ward": None, "district": "Coimbatore"},
        {"full_name": "CCMC Sanitation Officer",         "email": "officer3@giips.gov.in",  "role": "Officer", "password": "password123", "department": "CCMC Health Department", "ward": None, "district": "Coimbatore"},
        {"full_name": "TANGEDCO - Coimbatore Region",    "email": "officer4@giips.gov.in",  "role": "Officer", "password": "password123", "department": "TANGEDCO - Coimbatore Region", "ward": None, "district": "Coimbatore"},

        # ── Demo Citizens (Coimbatore residents, spread across wards) ──
        {"full_name": "Ravi Krishnan",                   "email": "citizen@giips.gov.in",    "role": "Citizen", "password": "password123", "department": None, "ward": "27", "district": "Coimbatore"},
        {"full_name": "Lakshmi Priya",                   "email": "citizen2@giips.gov.in",   "role": "Citizen", "password": "password123", "department": None, "ward": "1",  "district": "Coimbatore"},
        {"full_name": "Muruganantham",                   "email": "citizen3@giips.gov.in",   "role": "Citizen", "password": "password123", "department": None, "ward": "15", "district": "Coimbatore"},
        {"full_name": "Kavitha Ramesh",                  "email": "citizen4@giips.gov.in",   "role": "Citizen", "password": "password123", "department": None, "ward": "48", "district": "Coimbatore"},
        {"full_name": "Senthil Kumar",                   "email": "citizen5@giips.gov.in",   "role": "Citizen", "password": "password123", "department": None, "ward": "76", "district": "Coimbatore"},

        # ── Ward Councillors for specific real wards across all 5 zones ──
        {"full_name": "Councillor - Thudiyalur (Ward 1)",      "email": "councillor1@giips.gov.in", "role": "Councillor", "password": "password123", "department": None, "ward": "1", "district": "Coimbatore"},
        {"full_name": "Councillor - Saravanampatti (Ward 3)",  "email": "councillor2@giips.gov.in", "role": "Councillor", "password": "password123", "department": None, "ward": "3", "district": "Coimbatore"},
        {"full_name": "Councillor - Chinnavedampatti (Ward 10)","email": "councillor3@giips.gov.in","role": "Councillor", "password": "password123", "department": None, "ward": "10","district": "Coimbatore"},
        {"full_name": "Councillor - Peelamedu (Ward 27)",      "email": "councillor4@giips.gov.in", "role": "Councillor", "password": "password123", "department": None, "ward": "27","district": "Coimbatore"},
        {"full_name": "Councillor - RS Puram (Ward 46)",       "email": "councillor5@giips.gov.in", "role": "Councillor", "password": "password123", "department": None, "ward": "46","district": "Coimbatore"},
        {"full_name": "Councillor - Race Course (Ward 48)",    "email": "councillor6@giips.gov.in", "role": "Councillor", "password": "password123", "department": None, "ward": "48","district": "Coimbatore"},
        {"full_name": "Councillor - Vadavalli (Ward 33)",      "email": "councillor7@giips.gov.in", "role": "Councillor", "password": "password123", "department": None, "ward": "33","district": "Coimbatore"},
        {"full_name": "Councillor - Kuniyamuthur (Ward 76)",   "email": "councillor8@giips.gov.in", "role": "Councillor", "password": "password123", "department": None, "ward": "76","district": "Coimbatore"},

        # ── Zone Commissioners (one per zone) ──
        {"full_name": "Commissioner - North Zone",   "email": "commr-north@giips.gov.in",  "role": "Commissioner", "password": "password123", "department": "CCMC North Zone", "ward": None, "district": "Coimbatore"},
        {"full_name": "Commissioner - South Zone",   "email": "commr-south@giips.gov.in",  "role": "Commissioner", "password": "password123", "department": "CCMC South Zone", "ward": None, "district": "Coimbatore"},
        {"full_name": "Commissioner - East Zone",    "email": "commr-east@giips.gov.in",   "role": "Commissioner", "password": "password123", "department": "CCMC East Zone", "ward": None, "district": "Coimbatore"},
        {"full_name": "Commissioner - West Zone",    "email": "commr-west@giips.gov.in",   "role": "Commissioner", "password": "password123", "department": "CCMC West Zone", "ward": None, "district": "Coimbatore"},
        {"full_name": "Commissioner - Central Zone", "email": "commr-central@giips.gov.in","role": "Commissioner", "password": "password123", "department": "CCMC Central Zone", "ward": None, "district": "Coimbatore"},

        # ── MLA - Coimbatore Central ──
        {"full_name": "MLA - Coimbatore Central",     "email": "mla1@giips.gov.in",         "role": "MLA",       "password": "password123", "department": None, "ward": None, "district": "Coimbatore"},

        # ── District Collector oversight ──
        {"full_name": "Collector - Coimbatore District", "email": "collector1@giips.gov.in","role": "Collector", "password": "password123", "department": None, "ward": None, "district": "Coimbatore"},
    ]

    for user in users:
        if not db.query(User).filter(User.email == user["email"]).first():
            new_user = User(
                id=str(uuid.uuid4()),
                full_name=user["full_name"],
                email=user["email"],
                password_hash=hash_password(user["password"]),
                role=user["role"],
                department=user.get("department"),
                ward=user.get("ward"),
                district=user.get("district"),
            )
            db.add(new_user)
    db.commit()
    db.close()

def seed_default_executive():
    from auth_service import hash_password
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "collector@gov.in").first()
        if not user:
            new_user = User(
                id=str(uuid.uuid4()),
                full_name="District Collector",
                email="collector@gov.in",
                password_hash=hash_password("1234567"),
                role="Executive"
            )
            db.add(new_user)
            db.commit()
            print("[SEED] Default executive account created: collector@gov.in / 1234567")
        else:
            user.password_hash = hash_password("1234567")
            db.commit()
            print("[SEED] Default executive account verified: collector@gov.in")
    finally:
        db.close()

# Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_synthetic_data(num_complaints: int = 10000, duplicate_rate: float = 0.15):
    """Generate and seed synthetic Coimbatore-specific civic data.

    Every complaint is matched to its real CCMC ward and zone using the
    AREA_TO_WARD lookup from coimbatore_wards.py.  No fictional wards,
    no area-ward mismatches, and no non-civic categories.
    """
    from collections import defaultdict

    db = SessionLocal()

    try:
        existing_count = db.query(Complaint).count()
        if existing_count > 0:
            print(f"Database already has {existing_count} complaints, skipping seed")
            return
    except:
        pass

    categories = list(CCMC_COMPLAINT_TEMPLATES.keys())
    complaints_list = []
    incidents = []

    citizens = db.query(User).filter(User.role == 'Citizen').all()

    zone_lat_lng = {
        "North":   (11.052, 76.96),
        "South":   (10.975, 76.94),
        "East":    (11.025, 77.02),
        "West":    (11.015, 76.88),
        "Central": (11.000, 76.96),
    }

    for i in range(num_complaints):
        category  = random.choice(categories)
        # Pick a random area whose templates we'll use
        base_text = random.choice(CCMC_COMPLAINT_TEMPLATES[category])

        # Extract area hint from template — templates contain area names
        # like "Sathy Road", "Gandhipuram", etc.  Try to find the
        # correct real ward from one of the known area tokens.
        template_lower = base_text.lower()
        matched_ward = None
        for area_name, (wn, _zone) in AREA_TO_WARD.items():
            if area_name in template_lower:
                matched_ward = wn
                break

        if matched_ward is None:
            # Fallback: pick a random Coimbatore ward
            matched_ward = random.choice(ALL_WARD_NUMBERS)

        ward_num = matched_ward
        zone     = ZONE_BY_WARD[ward_num]
        areas    = AREAS_BY_WARD[ward_num]
        area_label = random.choice(areas)
        lat_lng  = zone_lat_lng[zone]
        ref      = f"COMP-{i+1:06d}"

        description = f"{base_text} [{ref} | Ward {ward_num} | {zone} Zone | Coimbatore]"
        title       = f"{category} in {area_label}, Ward {ward_num} ({zone} Zone) — {ref}"

        # Distribute complaints round-robin across all citizens
        owner = citizens[i % len(citizens)] if citizens else None

        complaint = Complaint(
            id=ref,
            title=title,
            description=description,
            location=f"{area_label}, Ward {ward_num}, {zone} Zone, Coimbatore",
            ward=str(ward_num),
            predicted_category=category,
            priority=random.choices(PRIORITY_LABELS, weights=PRIORITY_WEIGHTS)[0],
            created_at=datetime.datetime.utcnow() - timedelta(days=random.randint(0, 60)),
            latitude=round(lat_lng[0] + random.uniform(-0.04, 0.04), 6),
            longitude=round(lat_lng[1] + random.uniform(-0.04, 0.04), 6),
            user_id=owner.id if owner else None,
        )
        complaints_list.append(complaint)

    for c in complaints_list:
        db.add(c)
    db.commit()

    # Create incidents — one per distinct (category, ward) with enough complaints
    cat_ward_buckets = defaultdict(list)
    for c in complaints_list:
        cat_ward_buckets[(c.predicted_category, c.ward)].append(c)

    inc_idx = 0
    for (cat, ward), pool in cat_ward_buckets.items():
        if len(pool) < 3:
            continue  # skip tiny groups
        cluster_sz = min(len(pool), random.randint(3, min(25, len(pool))))
        zone = ZONE_BY_WARD.get(int(ward), "Central")
        inc_idx += 1
        inc_id = f"INC-{inc_idx:06d}"

        incident = Incident(
            id=inc_id,
            incident_number=inc_id,
            category=cat,
            ward=str(ward),
            cluster_size=cluster_sz,
            priority_score=round(random.uniform(30, 95), 1),
            priority_label=random.choices(PRIORITY_LABELS, weights=PRIORITY_WEIGHTS)[0],
            summary=f"Cluster of {cat.lower()} complaints in Ward {ward} ({zone} Zone)",
            status=random.choice(["open", "in-progress", "resolved"]),
            recommended_action=f"Deploy {cat.lower()} maintenance crew to Ward {ward}, {zone} Zone",
            days_open=random.randint(1, 30),
        )
        incidents.append(incident)

        # Link complaints to this incident
        batch = pool[:cluster_sz]
        for c in batch:
            c.incident_id = inc_id
            pool.remove(c)

    for inc in incidents:
        db.add(inc)
    db.commit()

    print(f"Seeded database with {len(complaints_list)} complaints across {len(incidents)} incidents")
    print(f"  Wards used: {len(set(c.ward for c in complaints_list))} / 100")
    print(f"  Zones used: {len(set(ZONE_BY_WARD.get(int(c.ward), '?') for c in complaints_list))} / 5")
    print(f"  Categories: {len(set(c.predicted_category for c in complaints_list))} (civic only)")
    db.close()

    topup_wards(min_per_ward=50)


def topup_wards(min_per_ward: int = 50):
    """Ensure every ward has at least min_per_ward complaints.

    Queries existing complaints from the DB, tops up short wards,
    and assigns topped-up complaints to new incidents.
    Idempotent and safe to call multiple times.
    """
    from collections import defaultdict
    db = SessionLocal()
    try:
        rows = db.query(Complaint.ward, func.count(Complaint.id)).group_by(Complaint.ward).all()
        ward_counts = defaultdict(int, {w: c for w, c in rows})

        last_ref = db.query(func.max(Complaint.id)).scalar()
        if last_ref and last_ref.startswith("COMP-"):
            counter = int(last_ref.split("-")[1])
        else:
            counter = 0

        categories = list(CCMC_COMPLAINT_TEMPLATES.keys())
        citizens = db.query(User).filter(User.role == 'Citizen').all()

        zone_lat_lng = {
            "North":   (11.052, 76.96),
            "South":   (10.975, 76.94),
            "East":    (11.025, 77.02),
            "West":    (11.015, 76.88),
            "Central": (11.000, 76.96),
        }

        topup_list = []
        topup_citizen_idx = 0
        for wn in ALL_WARD_NUMBERS:
            wn_str = str(wn)
            current = ward_counts.get(wn_str, 0)
            needed = max(0, min_per_ward - current)
            for _ in range(needed):
                category = random.choice(categories)
                base_text = random.choice(CCMC_COMPLAINT_TEMPLATES[category])
                zone = ZONE_BY_WARD[wn]
                areas = AREAS_BY_WARD[wn]
                area_label = random.choice(areas)
                lat_lng = zone_lat_lng[zone]
                counter += 1
                ref = f"COMP-{counter:06d}"
                owner = citizens[topup_citizen_idx % len(citizens)] if citizens else None
                topup_citizen_idx += 1
                complaint = Complaint(
                    id=ref,
                    title=f"{category} in {area_label}, Ward {wn_str} ({zone} Zone)",
                    description=f"{base_text} [Ward {wn_str} | {zone} Zone | Coimbatore]",
                    location=f"{area_label}, Ward {wn_str}, {zone} Zone, Coimbatore",
                    ward=wn_str,
                    predicted_category=category,
                    priority=random.choices(PRIORITY_LABELS, weights=PRIORITY_WEIGHTS)[0],
                    created_at=datetime.datetime.utcnow() - timedelta(days=random.randint(0, 60)),
                    latitude=round(lat_lng[0] + random.uniform(-0.04, 0.04), 6),
                    longitude=round(lat_lng[1] + random.uniform(-0.04, 0.04), 6),
                    user_id=owner.id if owner else None,
                )
                topup_list.append(complaint)

        if not topup_list:
            print(f"[TOPUP] All {len(ALL_WARD_NUMBERS)} wards already have >= {min_per_ward} complaints")
            return

        for c in topup_list:
            db.add(c)
        db.commit()

        # Group topped-up complaints into incidents
        cat_ward_buckets = defaultdict(list)
        # Re-read all complaints for accurate bucket counts
        all_rows = db.query(Complaint).all()
        for c in all_rows:
            cat_ward_buckets[(c.predicted_category, c.ward)].append(c)

        last_inc = db.query(func.max(Incident.id)).scalar()
        inc_counter = int(last_inc.split("-")[1]) if last_inc and last_inc.startswith("INC-") else 0

        new_incidents = []
        for (cat, ward), pool in cat_ward_buckets.items():
            if len(pool) < 3:
                continue
            cluster_sz = min(len(pool), random.randint(3, min(25, len(pool))))
            zone = ZONE_BY_WARD.get(int(ward), "Central")
            inc_counter += 1
            inc_id = f"INC-{inc_counter:06d}"
            incident = Incident(
                id=inc_id,
                incident_number=inc_id,
                category=cat,
                ward=str(ward),
                cluster_size=cluster_sz,
                priority_score=round(random.uniform(30, 95), 1),
                priority_label=random.choices(PRIORITY_LABELS, weights=PRIORITY_WEIGHTS)[0],
                summary=f"Cluster of {cat.lower()} complaints in Ward {ward} ({zone} Zone)",
                status=random.choice(["open", "in-progress", "resolved"]),
                recommended_action=f"Deploy {cat.lower()} maintenance crew to Ward {ward}, {zone} Zone",
                days_open=random.randint(1, 30),
            )
            new_incidents.append(incident)
            batch = pool[:cluster_sz]
            for c in batch:
                c.incident_id = inc_id
                pool.remove(c)

        for inc in new_incidents:
            db.add(inc)
        db.commit()

        print(f"[TOPUP] Added {len(topup_list)} complaints across {len(new_incidents)} incidents")
        print(f"[TOPUP] All {len(ALL_WARD_NUMBERS)} wards now have >= {min_per_ward} complaints")
    finally:
        db.close()


def backfill_wards_and_incidents():
    """One-time backfill for existing production data:
    1. Reassign wards that are stuck on a single value (e.g. \"Ward 1\").
    2. Create incidents for orphaned complaints that have no incident_id.

    Uses SQL-level batch UPDATEs and per-batch commits so the work is
    interrupt-safe — if Render's startup timeout kills the process, the
    next restart resumes from where it left off.
    """
    db = SessionLocal()
    try:
        # --- 1. Redistribute wards for complaints with an unrealistic default ---
        stale_count = db.query(Complaint).filter(
            or_(
                Complaint.ward == "Ward 1",
                Complaint.ward == "",
            )
        ).count()
        if stale_count:
            # Assign unique random wards per-batch so two runs don't keep
            # reassigning the same complaints.
            import math
            BATCH = 500
            for offset in range(0, stale_count, BATCH):
                batch = db.query(Complaint).filter(
                    or_(Complaint.ward == "Ward 1", Complaint.ward == "")
                ).limit(BATCH).offset(offset).all()
                for c in batch:
                    c.ward = f"Ward {random.randint(1, 20)}"
                db.commit()
                print(f"[BACKFILL] Wards reassigned: {min(offset + BATCH, stale_count)}/{stale_count}")
        else:
            print("[BACKFILL] No stale wards found")

        # --- 2. Link orphaned complaints to incidents ---
        # Get distinct (ward, category) pairs still needing an incident.
        pairs = db.query(Complaint.ward, Complaint.predicted_category).filter(
            Complaint.incident_id.is_(None),
            Complaint.ward.isnot(None),
            Complaint.ward != "",
        ).distinct().all()

        if pairs:
            PAIR_BATCH = 25  # process 25 (ward, category) pairs per commit
            total_linked = 0

            for i in range(0, len(pairs), PAIR_BATCH):
                batch_pairs = pairs[i:i + PAIR_BATCH]

                for ward, category in batch_pairs:
                    cat = category or "General"
                    inc_id = str(uuid.uuid4())
                    inc_number = f"INC-{uuid.uuid4().hex[:6].upper()}"

                    incident = Incident(
                        id=inc_id,
                        incident_number=inc_number,
                        category=cat,
                        ward=ward,
                        cluster_size=0,
                        priority_score=round(random.uniform(30, 95), 1),
                        priority_label="Medium",
                        summary=f"Auto-created for {cat} complaints in {ward}",
                        status="open",
                        recommended_action="Review and assign",
                        days_open=random.randint(1, 30),
                    )
                    db.add(incident)
                    db.flush()

                    # Bulk UPDATE — one SQL statement, no Python object loading
                    count = db.query(Complaint).filter(
                        Complaint.incident_id.is_(None),
                        Complaint.ward == ward,
                        Complaint.predicted_category == category,
                    ).update({Complaint.incident_id: inc_id})
                    total_linked += count

                db.commit()
                print(f"[BACKFILL] Incidents linked: {total_linked} complaints linked so far")

            print(f"[BACKFILL] Completed: {total_linked} complaints linked to incidents")
        else:
            print("[BACKFILL] No unlinked complaints found")
    finally:
        db.close()

def migrate_old_departments():
    """Migrate old department names to new standardised names in the database.
    Handles User.department and DepartmentMetrics.department columns."""
    from department_map import OLD_TO_NEW_DEPT, SLUG_TO_DISPLAY
    db = SessionLocal()
    try:
        # Migrate User.department
        for old_name, new_name in OLD_TO_NEW_DEPT.items():
            updated = db.query(User).filter(
                User.department == old_name,
                User.role == "Officer"
            ).update({User.department: new_name})
            if updated:
                print(f"[MIGRATION] Updated {updated} officer(s) department: '{old_name}' → '{new_name}'")

        # Migrate DepartmentMetrics.department
        for old_name, new_name in OLD_TO_NEW_DEPT.items():
            updated = db.query(DepartmentMetrics).filter(
                DepartmentMetrics.department == old_name
            ).update({DepartmentMetrics.department: new_name})
            if updated:
                print(f"[MIGRATION] Updated {updated} department metric(s): '{old_name}' → '{new_name}'")

        db.commit()
        print("[MIGRATION] Department migration complete")
    except Exception as e:
        print(f"[MIGRATION] Department migration error: {e}")
        db.rollback()
    finally:
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


def add_last_login_column():
    """Add last_login column to users table if it does not exist (idempotent migration)."""
    db = SessionLocal()
    try:
        db.execute(text("ALTER TABLE users ADD COLUMN last_login DATETIME"))
        db.commit()
        print("[MIGRATION] Added last_login column to users table")
    except Exception:
        db.rollback()
        print("[MIGRATION] last_login column already exists")
    finally:
        db.close()

def backfill_officer_departments():
    """Assign a real department to any officer whose department is null.
    Uses name/email heuristics; falls back to CCMC Engineering Wing.
    Idempotent — safe to call on every startup.
    """
    db = SessionLocal()
    try:
        dept_map = {
            "Roads": "CCMC Engineering Wing",
            "Sanitation": "CCMC Health Department",
            "Water": "TWAD Board - Coimbatore Division",
            "Engineering": "CCMC Engineering Wing",
            "Health": "CCMC Health Department",
        }
        null_dept = db.query(User).filter(User.role == "Officer", User.department.is_(None)).all()
        for off in null_dept:
            assigned = False
            for keyword, dept in dept_map.items():
                if keyword.lower() in (off.full_name or "").lower() or keyword.lower() in (off.email or "").lower():
                    off.department = dept
                    assigned = True
                    break
            if not assigned:
                off.department = "CCMC Engineering Wing"
        db.commit()
        if null_dept:
            print(f"[BACKFILL] Assigned department to {len(null_dept)} officers")
    except Exception:
        db.rollback()
    finally:
        db.close()


# NOTE: All runtime initialization moved to app.py lifespan to avoid
# import-time side effects. database.py must remain side-effect free
# so that routes.py can safely import models at module load time.


def add_new_feature_columns():
    """Idempotent migration for the F1/F7/F10/F18 feature columns.

    Base.metadata.create_all() creates NEW tables but never adds columns
    to EXISTING tables, so existing deployments need explicit ALTER TABLEs.
    Each ALTER runs in its own transaction: a failure on one column is
    logged loudly and never blocks the remaining columns.
    """
    from sqlalchemy import inspect

    try:
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
    except Exception as e:
        print(f"[MIGRATION] Schema inspection failed: {e}")
        return

    alter_plan = []

    if "users" in existing_tables:
        cols = {c["name"] for c in inspector.get_columns("users")}
        for col, ddl in (
            ("login_streak", "ALTER TABLE users ADD COLUMN login_streak INTEGER NOT NULL DEFAULT 0"),
            ("show_on_leaderboard", "ALTER TABLE users ADD COLUMN show_on_leaderboard BOOLEAN NOT NULL DEFAULT FALSE"),
            ("trust_score", "ALTER TABLE users ADD COLUMN trust_score FLOAT NOT NULL DEFAULT 50.0"),
        ):
            if col not in cols:
                alter_plan.append(("users", col, ddl))

    if "incidents" in existing_tables:
        cols = {c["name"] for c in inspector.get_columns("incidents")}
        for col, ddl in (
            ("public_attention_flag", "ALTER TABLE incidents ADD COLUMN public_attention_flag BOOLEAN NOT NULL DEFAULT FALSE"),
            ("estimated_cost", "ALTER TABLE incidents ADD COLUMN estimated_cost FLOAT"),
        ):
            if col not in cols:
                alter_plan.append(("incidents", col, ddl))

    if "complaints" in existing_tables:
        cols = {c["name"] for c in inspector.get_columns("complaints")}
        for col, ddl in (
            ("photo_paths", "ALTER TABLE complaints ADD COLUMN photo_paths TEXT"),
            ("resubmission_of", "ALTER TABLE complaints ADD COLUMN resubmission_of VARCHAR"),
            ("predicted_resolution_days", "ALTER TABLE complaints ADD COLUMN predicted_resolution_days FLOAT"),
            ("follow_up_count", "ALTER TABLE complaints ADD COLUMN follow_up_count INTEGER NOT NULL DEFAULT 0"),
        ):
            if col not in cols:
                alter_plan.append(("complaints", col, ddl))

    if "notifications" in existing_tables:
        cols = {c["name"] for c in inspector.get_columns("notifications")}
        for col, ddl in (
            ("group_id", "ALTER TABLE notifications ADD COLUMN group_id VARCHAR"),
            ("group_count", "ALTER TABLE notifications ADD COLUMN group_count INTEGER NOT NULL DEFAULT 1"),
        ):
            if col not in cols:
                alter_plan.append(("notifications", col, ddl))

    if not alter_plan:
        print("[MIGRATION] New feature columns verified (none missing)")
        return

    for table, col, ddl in alter_plan:
        db = SessionLocal()
        try:
            db.execute(text(ddl))
            db.commit()
            print(f"[MIGRATION] Added {table}.{col}")
        except Exception as e:
            db.rollback()
            exists = False
            try:
                exists = col in {c["name"] for c in inspect(engine).get_columns(table)}
            except Exception:
                pass
            if exists:
                print(f"[MIGRATION] {table}.{col} already exists (concurrent add) - OK")
            else:
                print(f"[MIGRATION] FAILED to add {table}.{col}: {e}")
                print(f"[MIGRATION]   SQL: {ddl}")
        finally:
            db.close()
