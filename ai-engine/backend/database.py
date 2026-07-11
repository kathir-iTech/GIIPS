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
from sqlalchemy import create_engine, Column, String, Integer, Float, Text, DateTime, ForeignKey
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
        "Speed breaker too high causing undercarriage damage",
        "Multiple potholes on stretch between T Nagar and Saidapet after rains",
        "Road cave-in near Adyar river bridge, very dangerous at night no lights",
        "Patchwork repair on Velachery main road already caved in within a week",
        "Gravel and broken bitumen on Guindy industrial road due to lorry traffic",
        "Car damaged hitting large pothole on Anna Salai near Thousand Lights mosque",
        "Speed breaker not painted white invisible at night many accidents near Chromepet",
        "Road completely washed away in last rain near Tambaram to Vandalur link road",
        "Buses avoiding lane due to cratered road on Nungambakkam High Road",
        "Two-wheeler slipped on gravel scattered on Mylapore tank bund road",
        "Half-hearted patch in front of Luz Corner mosque collapsed in two days",
        "Very deep pothole near Ashok Pillar at Kodambakkam causing traffic jams",
        "Broken road on service lane of Chennai Bypass with no warning signage",
        "Speed breakers on West Sadasivam Nagar road not painted since months",
        "Honking and traffic mess because people slowing down for potholes on ECR",
        "Road washed out completely after recent downpour near Kelambakkam",
        "Pothole near Central railway station damaging auto tyres every single day",
        "Tar boil on hot road stuck to my tyre now tyre burst near Koyambedu market",
        "Boundary wall collapsed on road after rain near Villivakkam railway station",
        "Loose gravel on Chengalpattu road near SRP college making bike riding risky",
        "Crater on Kaliamman Koil Street in Virugambakkam after pipeline work",
        "Small patch pothole near Naduvakkarai junction on GST road trouble",
        "Road in front of district collectorate in poor shape ironical situation",
        "Encroached footpath forcing walkers onto road near Parrys corner",
        "Missing road signage for speed breaker after metro construction in Teynampet",
        "Stretch of road between Madhavaram and Puzhal completely broken after lorry",
        "Waterlogging turns potholes into dangerous invisible pits on OMR near Sholinganallur",
        "Badly need road relaying in Muthamizh Nagar near Pammal whole stretch",
        "Truck broke road while digging up newly laid bitumen at Vanagaram",
        "Perumbakkam road has huge tanker damaged pothole nobody caring complaint",
        "Rainwater mixing with broken road on Tharamani link road worst condition",
        "Bikers falling daily on bad stretch near Padi junction no action yet",
        "Court allapuram road near VelloreCollectorate has large sinkhole report",
    ],
    "Water Supply": [
        "No water supply for past 3 days entire street affected in Anna Nagar",
        "Brownish muddy water coming from taps morning since last week Tambaram",
        "Water supply disrupted due to pipe burst near Koyambedu metro station",
        "Low water pressure affecting daily routine only fourth floor gets water Adyar",
        "Water in our taps literally brown and smelly since Tuesday morning No water",
        "Borewell supplying entire apartment complex broken old motor not working anymore",
        "Metro water lorries not coming from past week we are buying water every day",
        "Pipeline laid by CMWSSB last month already burst again near Valasaravakkam",
        "Water contamination reported after sewage pipe broke near Chetpet Lake",
        "We have not received regular water supply since 15 days paying full bills",
        "Water being supplied once in four days that too at 2 AM in the morning",
        "Complaint to Metrowater no response still have to buy water tanker for family",
        "Water pressure so low we can not fill overhead tank on fourth floor T Nagar",
        "Sewage water mixing with drinking water supply near Moolakadai very dangerous",
        "No water in entire locality included Elders and sick people who need it daily",
        "Newly laid pipeline in our lane has leakage wasting water whole day Tondiarpet",
        "TDS levels very high in supplied water white deposit on all utensils Royapettah",
        "Water board officials not responding to written complaints for last 10 days",
        "Water supplied only early morning 4 AM when no one awake to collect water",
        "Siphon works internally but still water brownish and smelly since festival time",
        "Pressurised water supply causing pipe bursts at multiple homes in Selaiyur",
        "Hand pump in ward eight still broken after one month of complaint filed",
        "Water stagnation in sump due to irregular supply breeding mosquitoes Mogappair",
        "Pay Rs 250 monthly still getting dirty water with worms Tell us why",
        "Residents forced to buy mineral water for drinking cooking all the time",
        "No warning before 2 day water cut told only through newspaper too late",
        "Water ISRO road colony contaminated with sewage floaters visible to eyes",
        "Prolonged no water near Karapakkam residents hiking 500m to public tap",
        "Overhead tank overflowing because no telemetry system in our ward Washermanpet",
        "Bad smell and taste in tap water since Diwali suspect pipe contamination somewhere",
        "Supply pipe damaged by road contractor now no water since three days Perungudi",
        "Water table dropping alarmingly borewells drying everywhere in Ambattur area",
        "Repeated complaints about chlorinated water supply ignored by CMWSSB board",
        "Illegal water connections near Tambaram Sanatorium depleting pressure here",
    ],
    "Drainage": [
        "Drainage outlet clogged with plastic waste blocking entire road at Madipakkam",
        "Open drain overflowing during rains entering homes on Mylapore Smith Road",
        "Drain cover missing creating hazard for walkers near Adyar bus depot",
        "Blockage causing water stagnation and smell near Chromepet signal area",
        "Drainage channel choked with construction debris near Velachery bypass road",
        "Stagnant water in open drain near school at Kovilambakkam health risk",
        "Manhole cover broken for past three weeks no one fixing very dangerous",
        "Rainwater mixes with sewage due to choked drain at Royapuram harbour area",
        "Encroachment of drain by shopkeepers now water logging in every rain Guindy",
        "Desilting of main drain desperately needed before monsoon hits Saidapet",
        "Stinking drain water on Pallavaram main road near market no action yet",
        "Drainage clogged by plastic bags after festival garbage people throw anywhere",
        "Cover missing on storm water drain near Tambaram railway station road crossing",
        "Mosquito breeding in standing drain water near Thiruvanmiyur beach road",
        "Small child fell into open drain near T Nagar Brundavan street cover missing",
        "Choked drain behind apartment at Nungambakkam releasing bad odour whole day",
        "Rains bring sewage water into ground floor homes at Mogappair western extn",
        "Water logging for 3 hours every rain near K K Nagar bus terminus due to drain",
        "Overflowing drain near market area in Villivakkam health department please act",
        "Silt in storm water drain not cleared from past year department unresponsive",
        "Covered drain opened again for repair work not closed back at Saidapet bridge",
        "Foul smell from underground drain at Indira Nagar near Adyar entering flats",
        "Drainage maintenance done on paper but no desilting actual on ground Tondiarpet",
        "Bio mulch not decomposing in drain causing blockage repeatedly in Perungudi",
        "Chicken shop waste thrown into drainage opening near cinema road Salem",
        "Residents reporting drain mosquitoes hospitalising kids near Puzhuthivakkam",
        "Cross drainage near bridge at Coimbatore Main silted no water outlet during rain",
        "Blocked outlet at Kallakurichi town drain causing stagnant water everywhere",
        "Sewage drain line broken near market causing outbreak of flies indiscriminately",
        "Long pending desilting of main drain at Kanyakumari Main Road required now",
        "Rats and vermin breeding in open solid waste drain near Vellore old bus stand",
        "Drainage blockage behind ration shop at Madurai East side very unhygienic",
        "Storm water drain near Karur bypass water stagnant causing accidents bike slipping",
        "Fresh water channel mixed with drain water due to broken partition wall somewhere",
        "Waste oil from nearby workshop drains into storm water during every rain event",
    ],
    "Streetlights": [
        "LED street light not functioning for a week near Koyambedu market road",
        "Multiple street lights out on T Nagar Brundavan street for past month",
        "Street light pole bent due to vehicle impact near Anna Salai Thiruvanmiyur",
        "Light pole sparking dangerously in rain near Kodambakkam bridge worry",
        "Entire stretch of road near Adyar river dark after 8 PM women scared walking",
        "LED light flickering continuously near Mylapore tank disturbing sleep at night",
        "No streetlight on service road of Old Mahabalipuram Road Sholinganallur stretch",
        "Street light pole tilting dangerously after lorry hit at West Mambalam",
        "No illumination on footpath near Tambaram railway station platform road",
        "Newly installed LED not working from day one at Anna Nagar East 2nd Avenue",
        "Most of streetlights not working on Velachery Bypass near VELACHERY depot",
        "Fuse box issue causing all five lights on lane to go off after every rain",
        "Street light cable cut during digging by contractor at Guindy Rajbhavan road",
        "Broken glass on ground from smashed street light near ECR besant nagar stretch",
        "No light on pedestrian subway road at T Nagar Natesan park back entrance",
        "Street light on pole not working for three months near Pammal police station",
        "Half of the lights on our street flicker intermittently near Ashok Nagar 4th Ave",
        "Newspaper reports dark streets but electricity board doing nothing Royapuram",
        "Light pole grounded creating electric shock risk near Royapettah Government school",
        "Complete darkness on road near Pallavaram market after 7 PM two wheeler accidents",
        "LED works only 1 minute out of 10 entire stretch from Madipakkam to Medavakkam",
        "Streetlight wires hanging low near Valasaravakkam arcot road touching ground",
        "Only one out of four pole lights working on Saidapet bridge western end",
        "Too dim light near hospital campus at Kilpauk forcing relatives to use mobile",
        "Metro construction damaged underground cable no light for past two weeks Chromepet",
        "Street light at Perungalathur signal dead causing accident at 10 PM reported twice",
        "Light flickers only in rain near Pallikaranai marsh board aware since two months",
        "Kids cannot play safely outside due no working light at Ambattur housing board",
        "No light on link road between Tharamani and Taramani whole stretch pitch dark",
        "Streetlight superintendent not picking phone no one repairing lights anywhere",
        "Multiple damaged poles on road to Vandalur zoo no maintenance since years",
        "Single pole with two lights not working near Madhavaram bus terminus dark spot",
        "Light outage at intersection near Washermanpet results in heavy traffic jams",
        "Glare from newly installed high mast too bright near school blinding drivers",
        "Underground cable stolen by thieves no working lights at Maduravoyal junction",
        "Solar light installed by ward member still not operational months later Salem",
    ],
    "Garbage": [
        "Garbage collection missed for 2 weeks in our ward K K Nagar stinking roads",
        "Overflowing garbage bins near T Nagar market unhygienic foul smell everywhere",
        "Construction debris dumped illegally on service road near Velachery bypass",
        "No garbage pickup service in our ward Mrs Jayalalithaa Avenue for 20 days",
        "Garbage truck comes only once a month to our street in Madipakkam west side",
        "Wet and dry waste mixed up by collection staff in Mogappair East again today",
        "Garbage bins nowhere to be found on road near Saidapet bridge for two weeks",
        "Kids falling sick due rotten garbage near school in Anna Nagar 2nd Avenue",
        "BBMP garbage workers strike affecting entire vadapalani area for past days",
        "Garbage dump near water tank at Pammal residents forced to buy bottled water",
        "Waste contractor not attending phones complaints not taken seriously Tambaram",
        "Illegal dump of medical waste near private hospital in Ashok Nagar dangerous",
        "Overflowing bin near bus stop at Guindy international market very unhygienic",
        "Residents throwing garbage into storm water drain as no collection service Maduravoyal",
        "Terrible smell near market area at Madurai South old garbage rotting uncollected",
        "Garbage dumped on vacant site near school breeding mosquitoes Adyar back road",
        "Waste collection vehicle capacity too small for entire ward at Anna Nagar West",
        "Household waste piled up near temple entrance residents forced to burn it",
        "BBMP officials come only for photos after media reports no real work on ground",
        "Garbage dump near railway track at Villivakkam causing fire risk dry leaves",
        "Vegetable market waste piled up near bus stop polluting road Royapettah mornings",
        "Collection staff demand extra money for lifting big sacks near Nungambakkam",
        "Stray dogs tearing garbage bags near school making roads dirty every evening",
        "Sweepers not coming for past week streets stinking in Coimbatore racecourse area",
        "Foul smell near village panchayat office at Kallakurichi garbage heap burning",
        "Plastic waste dumped near temple tank Kanyakumari no segregation at all",
        "Compost pit overflowing with mixed waste near ward office Trichy",
        "Waste collection time not followed they come irregularly disturbing sleep Vellore",
        "Shifted garbage bins from street to empty plot causing blockage Salem town",
        "Garbage truck rarely visits area we segregate waste then it mixed up again",
        "Dead animals not picked up by corporation near main road Virudhunagar dead smell",
        "Open defecation area cleaned only once complaint not resolved permanently",
        "Private trash burning near residential area causing breathing problems near ECR",
        "E-waste collected in normal bins near IT corridor Sholinganallur hazardous",
        "Garbage dumped on road by roadside eatery near Ambur nobody cleaning it",
        "Rotten waste pile near vegetable market at Namakkal attracting flies everywhere",
    ],
    "Public Health": [
        "Stagnant water near residential complex causing mosquito breeding Madipakkam",
        "Public toilets in park not cleaned regularly T Nagar Natesan park stinking",
        "Health hazard due to open garbage near school in Anna Nagar East very serious",
        "Dengue prevention fogging not done in our area for past one month Tambaram",
        "Drainage water stagnant near hospital creating mosquito menace at Adyar side",
        "Dog population increasing alarmingly near market no catch van deployed Royapuram",
        "No sewerage connection in newly built apartments Mogappair West raw sewage seen",
        "Illegal meat shop near school operating without licence health risk children",
        "Unhygienic condition at Chennai Central platform toilets urgent cleaning needed",
        "Rat infestation in old residential area near Mint street very bad situation",
        "Water contamination causing stomach illness complaints in entire locality Tondiarpet",
        "No mosquito fogging Done near Saidapet despite repeated dengue cases reported",
        "Overflowing public toilet at Besant Nagar beach health department please act",
        "Pest control service requested for termites in government school building Egmore",
        "Air quality poor near railway yard due to coal dust residents falling sick",
        "Construction dust causing breathing trouble in T Nagar locality no action yet",
        "Stray cattle roaming on road near airport Sholinganallur causing accidents daily",
        "Birth and death registration office always crowded no online system needed urgently",
        "Malnutrition case noticed at Anganwadi centre in Perambalur proper oversight need",
        "Sanitary workers not provided gloves and equipment near market Royapettah risky",
        "Public health centre runs out of basic medicines every week at Tambaram Sanatorium",
        "Plastic waste burned openly near residential colony near Guindy industrial estate",
        "Cholera-like symptoms in children after eating street food near beach road Mamallapuram",
        "Flies from garbage dump near hospital at Kilpauk making patient recovery hard",
        "Sewage treatment plant near Avaniya Nagar not working since months people suffering",
        "Open drain with sewage water right in front of apartment entrance at Perungudi",
        "No ambulance nearby from primary health centre when emergency at Madhavaram",
        "Methane gas smell near dumping ground in Kodungaiyur residents near affected",
        "Water stagnant and dirty near cremation ground at Velachery Main Road",
        "Public health checkup camp needed for workers at Guindy industrial estate",
        "Pesticide spraying not done in government school ground at Madurai East side",
        "Stray dogs entering garbage dump site near wharf at Royapuram harbour area",
        "No dustbins near bus stand at Namakkal causing littering and health risk",
        "Water borne disease spreading at Thanjavur slum area medical team request item",
        "Accumulation of hospital waste behind private nursing home at Karur very unsanitary",
    ],
    "Electricity": [
        "Frequent power cuts during evening hours affecting students in Anna Nagar West",
        "Transformer failure causing blackout near T Nagar Luz area 100 families affected",
        "Voltage fluctuation damaging fridge and TV at home in Adyar for past week",
        "Street lights not getting power supply on Mylapore Kutchery road for days",
        "Low voltage causing motor burn in borewell at Vandalur today morning again",
        "Entire street in dark due fuse off at midnight near Tambaram middleschool road",
        "Underground cable snapped due road work near Ashok Nagar 4th Avenue outage 3 days",
        "Power cut for 3 hours every alternate day in Teynampet colony notice not given",
        "Transformer oil leak creating fire risk near Guindy Rajbhavan road urgent",
        "Electric pole leaning dangerously on Vinayaka Nagar after heavy rain at Puzhuthivakkam",
        "Meter box sparking when we plug geyser residents scared near Mambalam west side",
        "BPL families affected most by long power cuts in Vellore interior villages request",
        "No street light after transformer blast at Saidapet bridge near Sinnaiyappar temple",
        "Frequent tripping due to illegal power draw by shop near Madipakkam bus terminus",
        "Electricity board staff not arriving for scheduled repair at Korukkupet since days",
        "Neon sign from shop creating voltage dip every night near T Nagar bus stop",
        "Streetlight dim because of load shedding nearby Sholinganallur IT corridor dark",
        "Single power line serving 200 homes old infrastructure near Pammal area frequent fail",
        "Tangedco staff demanding bribe for new connection near Maduravoyal middle class",
        "Solar panels on apartment common area not maintained proper nobody fixing attempt",
        "Overloaded transformer sparking near vegetable market Madurai South danger area",
        "Power cut scheduled at 2 AM unsuited for students in KK Nagar examination season",
        "Underground cable waterlogged due rain at Velachery Bypass outage today third time",
        "Power restoration after storm took 18 hours near Kovilambakkam unbearable summer",
        "Transformer on pavement at Vellore old town sparking risk passersby worry",
        "Three phase current imbalance causing motor vibration and near burn Madhavaram",
        "Single phase supply for 3 phase homes near Perambalur old town affected power",
        "Live wire hanging low near Maduravoyal junction construction site very risky",
        "Electricity board van not attended 5 complaints sent online all near Tambaram Sanatorium",
        "Transformer replacement done only after minister visit otherwise no action here",
        "Tree branches falling on power lines every rain near Karapakkam cutting supply",
        "Substation load shedding map incorrect published online tells 2 hrs we get 6 hrs",
        "Streetlight wiring missing on pillar near Washermanpet market complete dark road",
        "Generator noise from apartment near hospital at Kilpauk violating noise rules too",
        "Weak load current reaching end of line at Thanjavur North side fans running slow",
        "Low lying transformer waterlogged during every rain near Tiruchirappalli Cantonment",
    ],
}

# Sentence-initial variations appended to every seeded complaint so that
# no two rows have identical free text — yet the core issue / category
# semantics remain intact for SBERT clustering to find real duplicates.
_TEMPLATE_SUFFIXES = [
    "This has been reported multiple times by residents in the area.",
    "Local residents are very concerned about the ongoing situation.",
    "Immediate attention requested from the concerned ward officer.",
    "This issue is causing significant inconvenience to the public.",
    "Multiple households affected; please treat as a priority complaint.",
    "Complaint raised by citizen during morning walk; situation worsening daily.",
    "Issue persists despite earlier complaint — escalation required urgently.",
    "Elderly residents and children particularly affected by this problem.",
    "We have raised this before but no corrective action taken on ground.",
    "Situation critical especially during monsoon / peak summer season.",
    "Nearby commercial establishments also impacted by this civic failure.",
    "Photos and details shared with local press; public attention growing.",
    "Ward councillor has been informed — awaiting departmental response.",
    "Residents association has formally written to the municipal office.",
    "This is a recurring complaint in this ward for several months now.",
    "Health and safety hazard; request emergency response from authorities.",
    "Area residents held small meeting and decided to escalate collectively.",
    "Issue directly affecting daily commute and local business operations.",
    "Multiple calls to helpline went unanswered — complaint registered now.",
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
    address = Column(String, nullable=True)
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

# Seed demo users
def seed_demo_users():
    from auth_service import hash_password
    db = SessionLocal()
    
    users = [
        {"full_name": "District Collector", "email": "collector@giips.gov.in", "role": "Executive", "password": "password123"},
        {"full_name": "Government Officer - Roads", "email": "officer1@giips.gov.in", "role": "Officer", "password": "password123"},
        {"full_name": "Government Officer - Water", "email": "officer2@giips.gov.in", "role": "Officer", "password": "password123"},
        {"full_name": "Government Officer - Sanitation", "email": "officer3@giips.gov.in", "role": "Officer", "password": "password123"},
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
        category    = random.choice(list(COMPLAINT_TEMPLATES.keys()))
        district    = random.choice(TAMIL_NADU_DISTRICTS)
        ward        = f"Ward {random.randint(1, 20)}"
        base_text   = random.choice(COMPLAINT_TEMPLATES[category])
        ref         = f"COMP-{i+1:06d}"
        # Every complaint gets a unique ref tag so TF-IDF / SBERT never
        # sees identical free-text rows, while the core civic-issue text
        # is preserved for meaningful semantic clustering.
        description = f"{base_text} [{ref} | {ward} | {district}]"
        title       = f"{category} issue: {ward}, {district} — {ref}"

        complaint = Complaint(
            id=ref,
            title=title,
            description=description,
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


# NOTE: All runtime initialization moved to app.py lifespan to avoid
# import-time side effects. database.py must remain side-effect free
# so that routes.py can safely import models at module load time.