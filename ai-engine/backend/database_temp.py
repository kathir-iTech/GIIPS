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
from sqlalchemy import create_engine, Column, String, Integer, Float, Text, DateTime, ForeignKey, Boolean, or_, func
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
    "Road Infrastructure": [
        "Footpath near bus stand broken pedestrians forced onto road",
        "No pedestrian crossing near school zone dangerous for children",
        "Road divider damaged on highway at Tambaram stretch",
        "Bridge approach road subsiding near Adyar river",
        "Missing guardrail on flyover at Maduravoyal junction",
        "Road shoulder erosion on service road near Porur",
        "Pavement tiles broken on Anna Nagar Tower park pathway",
        "Cycle track encroached by parked vehicles on OMR",
        "Junction needs traffic island for safe crossing at Chromepet",
        "Underpass flooded every rain at Guindy industrial estate",
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
    "Pollution": [
        "Factory releasing black smoke early morning near residential area Ambattur",
        "Construction dust causing breathing trouble in T Nagar locality no action yet",
        "Burning of plastic waste near school in Chromepet toxic fumes every evening",
        "Noise pollution from temple speakers late night beyond permitted decibel at Mylapore",
        "Chemical waste dumped in open drain near Pallavaram industrial area",
        "Vehicle emission testing not enforced near Koyambedu bus terminus smoke everywhere",
        "Sewage treatment plant odour unbearable near Perungudi residents suffering",
        "Boiler stack from nearby laundry blackening buildings in Anna Nagar West",
        "Industrial effluent discharged into river near Erode tanneries water contaminated",
        "Burning of leaves and garbage near Velachery lake causing respiratory issues",
        "Plastic recycling unit operating without pollution board clearance in Madipakkam",
        "Quarry dust from stone crusher enveloping residential streets in Kanchipuram",
        "Fish kill in Adyar river due to industrial discharge toxic foam visible",
        "Hotel generator noise violating norms near Kilpauk medical college",
        "Fly ash from brick kiln affecting crops in Tiruvallur agricultural belt",
    ],
    "Traffic": [
        "Traffic signal not working at junction near T Nagar bus stand causing chaos",
        "Road blocked by illegal parking on Anna Salai near Spencer Plaza",
        "Missing traffic sign at school zone Tambaram east very dangerous",
        "No pedestrian crossing at signal near Saidapet court heavy traffic",
        "Auto rickshaws blocking main road near Koyambedu market during peak hours",
        "Heavy congestion every evening at Maduravoyal junction no traffic police deployed",
        "U-turn closed without alternative causing 2 km detour at Porur junction",
        "Encroached pavement forcing pedestrians onto busy road near Broadway",
        "Traffic bottleneck near toll plaza on Chennai Bypass adds 30 min commute",
        "Road rage incidents increasing near Guindy signal no police presence",
        "School zone speed breaker missing warning sign near Pammal tuition centre",
        "Wrong side driving rampant on one-way street near Mylapore tank",
        "Traffic police absent during evening peak at Velachery Bypass signal",
        "Illegal speed breakers installed by local residents on GST road dangerous",
        "Signal timing too short for elderly crossing near Parrys corner intersection",
    ],
    "Animal Nuisance": [
        "Stray dogs roaming aggressive near school in Anna Nagar children scared",
        "Cow carcass dumped on roadside near Perambur not removed since 3 days",
        "Monkey menace in residential area damaging property near Adyar Signal",
        "Stray cattle eating garbage and blocking traffic near Koyambedu",
        "Dead dog lying on road near Pallavaram market since two days",
        "Pig menace in residential locality near Madipakkam garbage strewn around",
        "Stray dogs barking all night near T Nagar residents unable to sleep",
        "Cow begging gang forcing vehicles to stop on highway near Chengalpattu",
        "Rabies vaccination needed after stray dog bites in Saidapet locality",
        "Packs of dogs chasing two-wheelers near Sholinganallur IT corridor",
        "Buffaloes roaming on busy OMR stretch near Thoraipakkam causing accidents",
        "Stray dog birth control programme not implemented in zone 10 Chennai",
        "Monkeys snatching food from pedestrians near Mylapore Kapaleeswarar temple",
        "Dead cat in drain near school breeding flies in Velachery",
        "Donkeys abandoned on road near landfill site at Kodungaiyur unhealthy",
    ],
    "Fire Safety": [
        "Electrical short circuit caused fire in slum near Chetpet no fire extinguisher",
        "Building near school has no fire exit certificate T Nagar high risk",
        "Gas cylinder burst in roadside eatery near Koyambedu no fire safety gear",
        "Fire hydrant on street not working near Kilpauk medical college zone",
        "Crackers sold illegally near market area in Mylapore without fire permit",
        "Fire engine could not access narrow lane near George Town during emergency",
        "Industrial unit operating without fire NOC near Ambattur estate fire risk",
        "LPG godown in residential area near Madipakkam unauthorised operation",
        "Transformer fire near school in Chromepet firemen arrived late",
        "No fire safety equipment in multistorey apartment in Velachery",
        "Forest fire near reserve forest at Vandalur zoo spreading fast",
        "Fire alarm not working in cinema theatre near T Nagar",
        "Petrol bunk operating too close to residential area in Medavakkam",
        "Stubble burning uncontrolled near Tambaram airbase smoke hazard",
        "Cracker stall near hospital during Diwali in Perambur fire emergency risk",
    ],
    "Building Violation": [
        "Third floor constructed without approval in residential zone Adyar",
        "Building under construction dumping debris on road near T Nagar",
        "Compound wall encroaching footpath in Mylapore hindering walkers",
        "Commercial building operating in residential zone at Anna Nagar causing nuisance",
        "Old building dangerous structure near school in Georgetown needs demolition",
        "Highrise violating FSI norms near Saidapet blocking sunlight to neighbours",
        "Construction without safety net at Velachery debris falling on road",
        "Building plan violation in CMDA zone at Chromepet floors added illegally",
        "Illegal extension on terrace creating load risk near Mambalam railway",
        "New construction blocking drainage path flooding neighbouring homes Madipakkam",
        "Shopping mall constructed on lake buffer zone near Pallikaranai marsh",
        "Property tax evasion building used commercial filed as residential Guindy",
        "Heritage building demolished illegally in Mylapore urgent CMDA intervention needed",
        "Construction on water body encroachment near Perungudi marshland",
        "Real estate project cancelled but no refund to buyers Ambattur area",
    ],
    "Encroachment": [
        "Footpath encroached by vegetable vendor near Tambaram station no walking space",
        "Roadside hawker blocking bus stop entrance at T Nagar Ranganathan Street",
        "Temple land encroached by private party at Mylapore water tank road",
        "Park converted into marriage hall by local body backdoor at Adyar",
        "Lake bund encroached by resort near Chembarambakkam lake illegal construction",
        "Water body filled for real estate near Pallavaram encroachment danger",
        "Road widening stopped due to encroachment near Saidapet court complex",
        "Government land occupied by unauthorised colony in Velachery marshland",
        "Footpath encroached by restaurant outdoor seating in Nungambakkam",
        "Parking lot built on playground at Anna Nagar tower park encroachment",
        "Shrine encroaching pavement near Mylapore Kapaleeswarar temple tank",
        "Bus stop area encroached by auto stand operators at Koyambedu",
        "Street used as godown by nearby shops at George Town congestion",
        "Lake inlet blocked by encroachment near Korattur water body",
        "Drainage pathway encroached by building wall in Madipakkam waterlogging",
    ],
    "Parks and Gardens": [
        "Park maintained poorly children cannot play equipment broken in T Nagar park",
        "Garden fence damaged stray dogs entering park in Adyar unsafe for kids",
        "Park lights not working near Saidapet people afraid after dark",
        "Benches broken in park near Mylapore senior citizens have no place to sit",
        "Park turned into garbage dump by nearby residents in Velachery",
        "Walking track damaged with loose tiles in Anna Nagar tower park",
        "Playground encroached by parking at Nungambakkam children have no space",
        "Park gate locked during evening hours when residents need it most Chromepet",
        "Garden hose broken water stagnation breeding mosquitoes in Guindy park",
        "Trees in park need pruning branches falling during wind at Tambaram",
        "Toilets in park locked and unhygienic near Koyambedu market garden",
        "Park converted into dumping ground for construction debris in Madipakkam",
        "Children swing broken sharp edges exposed dangerous in Perambur park",
        "Bouganvillea overgrowth blocking pathway in Pammal park dangerous thorns",
        "Park clock tower not functional for years landmark ignored by corporation",
    ],
    "Street Vendor": [
        "Unauthorised street vendor blocking footpath near Tambaram station pedestrian issue",
        "Vendor selling food without hygiene licence near school Chromepet health risk",
        "Hawker occupying bus stop area at T Nagar forcing commuters onto road",
        "Street vendor operating without waste bin littering all over Mylapore road",
        "Night market noise until 2 AM near residential area in Adyar disturbance",
        "Vendor encroaching road junction at Saidapet visibility issue for drivers",
        "Illegal vending near hospital entrance in Kilpauk ambulance blocked",
        "Vendor using LPG cylinder on footpath dangerous near Velachery market",
        "Fish vendor waste rotting on roadside near Purasawalkam smell unbearable",
        "Mobile food vendor near school without any hygiene certification Madipakkam",
        "Vegetable vendor on road blocking traffic every morning Anna Nagar worst",
        "Vendor not wearing gloves handling food openly near Koyambedu unsafe",
        "Hawker using loudspeaker for sales near residential zone Mambalam noise",
        "Flower vendor waste clogging drain on roadside at Mylapore daily problem",
        "Street vendor with no designated spot harassing shoppers at Pondy Bazaar",
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
    department = Column(String, nullable=True)
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

    # Escalation fields
    escalated = Column(Boolean, default=False, nullable=False)
    escalated_at = Column(DateTime, nullable=True)
    escalated_by = Column(String, nullable=True)
    escalation_reason = Column(Text, nullable=True)

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

class Notification(Base):
    """ORM model for in-app citizen notifications."""
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)
    complaint_id = Column(String, ForeignKey("complaints.id"), nullable=True)
    type = Column(String, nullable=False)
    data = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

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

        # ── Demo Citizen (Coimbatore resident) ──
        {"full_name": "Ravi Krishnan",                   "email": "citizen@giips.gov.in",    "role": "Citizen", "password": "password123", "department": None, "ward": "27", "district": "Coimbatore"},

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

    citizen = db.query(User).filter(User.role == 'Citizen').first()
    citizen_id = citizen.id if citizen else None

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
            user_id=citizen_id,
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


# NOTE: All runtime initialization moved to app.py lifespan to avoid
# import-time side effects. database.py must remain side-effect free
# so that routes.py can safely import models at module load time.
