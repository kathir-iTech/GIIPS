"""
train_expanded.py

Expanded synthetic training pipeline: ~100 examples per category (7 classes),
min_df=1, per-class metrics reported before/after.
Does NOT touch the NYC 311 CSV file.
"""

import pickle
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    import re, string
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'http\S+|www\.\S+', '', text)
    text = text.translate(str.maketrans('', '', string.punctuation))
    text = ' '.join(text.split())
    return text.strip()


def build_old_dataset() -> pd.DataFrame:
    """Replicate the original 32-sample dataset (57.1% path)."""
    data = [
        # Road Infrastructure
        {"text": "Large pothole on Main Street causing accidents", "category": "Road Infrastructure"},
        {"text": "Road surface damaged near the market area", "category": "Road Infrastructure"},
        {"text": "Speed breaker too high on Hospital Road", "category": "Road Infrastructure"},
        {"text": "Footpath tiles broken on Gandhi Road", "category": "Road Infrastructure"},
        {"text": "Manhole cover missing on MG Road", "category": "Road Infrastructure"},
        {"text": "Street has many cracks and potholes", "category": "Road Infrastructure"},
        # Water Supply
        {"text": "No water supply in Lakshmipuram for 3 days", "category": "Water Supply"},
        {"text": "Water pipe burst near the temple area", "category": "Water Supply"},
        {"text": "Dirty brown water coming from taps", "category": "Water Supply"},
        {"text": "Water contamination in residential area", "category": "Water Supply"},
        {"text": "Low water pressure in apartments", "category": "Water Supply"},
        # Waste Management
        {"text": "Garbage not collected for 2 weeks", "category": "Waste Management"},
        {"text": "Garbage bins overflowing near park", "category": "Waste Management"},
        {"text": "Illegal dumping of construction debris", "category": "Waste Management"},
        {"text": "Waste collection missed again", "category": "Waste Management"},
        # Street Lighting
        {"text": "Street lights not working near Shivaji Park", "category": "Street Lighting"},
        {"text": "Multiple street lamps out of order", "category": "Street Lighting"},
        {"text": "Dark area due to faulty street lights", "category": "Street Lighting"},
        {"text": "Street pole sparking dangerously", "category": "Street Lighting"},
        # Sanitation
        {"text": "Open drain overflow flooding the streets", "category": "Sanitation"},
        {"text": "Sewage on Subhash Nagar streets", "category": "Sanitation"},
        {"text": "Drainage blocked causing health hazard", "category": "Sanitation"},
        {"text": "Open sewage near residential area", "category": "Sanitation"},
        # More Road Infrastructure
        {"text": "Pothole causing vehicle damage on highway", "category": "Road Infrastructure"},
        {"text": "Road broken near school junction", "category": "Road Infrastructure"},
        {"text": "Dangerous speed bump needs fixing", "category": "Road Infrastructure"},
        # More Water Supply
        {"text": "Pipeline leakage wasting water", "category": "Water Supply"},
        {"text": "No water since Monday in our area", "category": "Water Supply"},
        # More Waste Management
        {"text": "Trash piling up near bus stop", "category": "Waste Management"},
        {"text": "Garbage truck not coming regularly", "category": "Waste Management"},
        # Sanitation
        {"text": "Blocked drain causing overflow", "category": "Sanitation"},
        {"text": "Mosquito breeding in stagnant water", "category": "Sanitation"},
    ]
    return pd.DataFrame(data)


def build_expanded_dataset() -> pd.DataFrame:
    """~100 Coimbatore-style examples per category across all 7 classes."""

    data: List[Dict[str, str]] = []

    # ── Roads (100) ─────────────────────────────────────────────────────────
    roads = [
        "Pothole on Sathy Road near Hope College junction causing vehicle damage",
        "Road surface broken on Avinashi Road near L&T Bypass repair needed immediately",
        "Deep crater on Mettupalayam Road near Sungam dangerous for night driving",
        "Speed breaker too high on Trichy Road near KNG Pudhur damaging car underside",
        "Road cave-in on Thadagam Road near Vadavalli after recent heavy rain",
        "Patchwork repair on Sathy Road near Saravanampatti collapsed within a week",
        "Loose gravel and broken bitumen on Mettupalayam Road near Ganapathy from lorry traffic",
        "Car tyre burst hitting pothole on Avinashi Road near Lakshmi Mills junction",
        "Speed breaker not painted on Pollachi Road near Kuniyamuthur invisible after dark",
        "Road washed out on Maruthamalai Road near Iyyampalayam after heavy downpour",
        "Buses swerving to avoid craters on Trichy Road near Singanallur stretch very risky",
        "Two-wheeler slipped on loose gravel on Thadagam Road near Rathinapuri resident injured",
        "Half-hearted patch on Sathy Road near Chinnavedampatti failed within two days",
        "Deep pothole near Gandhipuram bus stand causing traffic jams every evening",
        "Broken road on service lane of Sathy Road near Kalapatti no warning signs placed",
        "Road near Ukkadam bus stand completely broken after heavy vehicle movement daily",
        "Waterlogging turning potholes into invisible traps on Trichy Road near Irugur",
        "Road relaying badly needed on Pollachi Road near Eachanari entire stretch affected",
        "Truck damaged road while laying water line on Sathy Road near Thudiyalur",
        "Bikers falling daily on bad stretch near Ganapathy junction no action by authorities",
        "Road completely washed away near Perur temple road after monsoon rains last week",
        "Pothole near Race Course junction causing vehicle tyre damage almost every day",
        "Loose gravel on Maruthamalai Road near Vadavalli making motorcycle riding risky",
        "Road in front of CCMC office in poor condition ironic for corporation road",
        "Footpath near Town Hall encroached by vendors forcing pedestrians onto busy road",
        "Stretch between RS Puram and Gandhipuram completely broken after water line work",
        "Deep pothole on road near Sungam railway crossing cars scraping undercarriage",
        "Road widening debris not cleared on Avinashi Road near Peelamedu causing dust hazard",
        "Crumbled road edge on Sathy Road near Hope College no shoulder for pedestrians",
        "Pothole filled with rainwater on Mettupalayam Road invisible at night biker fell",
        "Road damage near Ganapathy bus stop buses cannot stop safely passengers at risk",
        "Speed breaker on Trichy Road near KNG Pudhur too tall ambulance cannot cross",
        "Road cave-in near Perur temple entrance after water pipe burst last month",
        "Patch laid on Sathy Road near Saravanampatti already sinking after first rain",
        "Pothole near RS Puram signal causing two-wheeler skidding accidents every week",
        "Gravel road inside Vadavalli colony needs tarring terrible dust in summer",
        "Road near Ukkadam lake completely broken after monsoon damage no repair done",
        "Footpath missing on Avinashi Road near Lakshmi Mills pedestrians walking on road",
        "Broken manhole cover on road near Gandhipuram bus stand causing hazard for vehicles",
        "Pothole near Singanallur bus terminus causing damage to bus tires regularly",
        "Road in Kuniyamuthur market area full of craters vendors complaining about access",
        "Bumpy ride on Thadagam Road near Rathinapuri due to undulating road surface",
        "Car damaged due to uncovered excavation on Sathy Road near Thudiyalur colony",
        "Road shoulder collapsed on Pollachi Road near Eachanari after drainage work",
        "Pothole on bridge over canal near Mettupalayam Road dangerous for motorists",
        "Road near Vadavalli school needs speed breaker children crossing at risk",
        "Potholes on service road along Sathy Road near Chinnavedampatti unridable for cycles",
        "Road relaying on Trichy Road near Irugur done poorly already developing cracks",
        "Water stagnation on road near Ganapthy junction from poor drainage and potholes",
        "Deep pothole on inner road near Race Course causing damage to cars every day",
        "Pedestrian crossing on Avinashi Road near Town Hall road markings faded invisible",
        "Road near Kuniyamuthur temple broken pilgrims struggling to walk during festival",
        "Pothole on Perur road near the temple gopuram causing traffic slowdown every day",
        "Road resurfacing on Sathy Road near Kalapatti not completed for over a month",
        "Crumbled footpath on Mettupalayam Road near Sungam forcing elderly onto main road",
        "Open drain on roadside near RS Puram market causing road edge to collapse slowly",
        "Pothole on Trichy Road near Singanallur filled with debris not actually repaired",
        "Road connecting Vadavalli to Thudiyalur in terrible shape no light at night",
        "Speed breaker on school road near Ganapathy faded paint invisible in rain",
        "Pothole near Eachanari temple causing damage to two-wheelers every morning rush",
        "Bus stop approach road near Peelamedu broken passengers alighting in mud and water",
        "Road near Perur lake bund eroded after monsoon no fencing or warning signs",
        "Patchwork on Sathy Road near Saravanampatti done with poor quality material failing",
        "Pothole near Ukkadam market causing water splashing on pedestrians during rain",
        "Road in Gandhipuram commercial area uneven surface causing tripping hazard for shoppers",
        "Deep pothole near KNG Pudhur signal cars lining up to avoid damage",
        "Side road near Race Course colony full of potholes residents unable to drive out",
        "Road near Thudiyalur tank bund damaged after tractor movement during desilting work",
        "Pothole on Mettupalayam Road near Ganapthy bus stop commuters alighting in water",
        "Road near Vellalore cemetery badly damaged hearses struggling to pass during funerals",
        "Speed breaker on road near Singanallur police station too high causing bus damage",
        "Pothole near Ramanathapuram junction growing bigger every week no one repairs it",
        "Road repair debris left on Sathy Road near Chinnavedampatti causing traffic obstruction",
        "Pothole on Avinashi Road near Peelamedu flyover approach causing vehicle damage daily",
        "Road near Kuniyamuthur railway station approach in terrible condition rickshaws damaged",
        "Footpath tiles missing on road near Gandhipuram bus stand elderly person tripped",
        "Pothole near RS Puram vegetable market filled with dirty water breeding mosquitoes",
        "Road near Vadavalli government hospital broken ambulance shaking patients during transport",
        "Pothole covered with thin metal sheet on Trichy Road near Eachanari causing noise",
        "Road near Perur temple tank edge collapsing after rain need retaining wall urgently",
        "Deep pothole on Sathy Road near Thudiyalur bus stop commuters alighting in danger",
        "Pothole near Ganapathy textile market causing traffic slowdown during peak business hours",
        "Road resurfacing on Pollachi Road near Kuniyamuthur partially done rest ignored",
        "Pothole near Mettupalayam Road bypass ramp causing two-wheeler skid accidents regularly",
        "Pitch darkness on road near Vadavalli due to non working streetlight plus potholes",
        "Uneven road surface near Singanallur market causing spillage of goods from auto rickshaws",
        "Pothole near Race Course library damaging vehicles of visitors every single day",
        "Road near Ukkadam mosque broken during utility work not restored properly",
        "Pothole near Saravanampatti signal at junction causing traffic build up every rain",
        "Road near Kalapatti industrial estate full of heavy truck damage no maintenance",
        "Pothole near Eachanari bus stop filled with mud after rain invisible to drivers",
        "Pothole on Sathy Road near Hope College reappeared within days after patch repair",
        "Road near Rathinapuri temple damaged after festival vehicle movement no repair",
        "Pothole near Irugur market growing daily residents throwing stones to warn drivers",
        "Road near Ganapathy lake bund washed out during monsoon no restoration done yet",
    ]
    for t in roads:
        data.append({"text": t, "category": "Roads"})

    # ── Water Supply (100) ──────────────────────────────────────────────────
    water = [
        "No water supply for past 3 days in Thudiyalur entire street affected",
        "Brownish muddy water coming from taps in Saravanampatti since last week",
        "Water supply disrupted due to pipe burst on Sathy Road near Ganapathy",
        "Low water pressure in RS Puram affecting daily routine upper floors get no water",
        "Borewell supplying Vadavalli colony broken motor not working for a full week",
        "Tankers not coming to Kuniyamuthur area for 5 days residents buying water daily",
        "Pipeline laid by TWAD on Avinashi Road already burst again near Peelamedu",
        "Water contamination reported after sewage pipe broke near Ukkadam lake",
        "No regular supply in Singanallur for 15 days despite paying full water bills",
        "Water supplied once in 4 days at 2 AM in Gandhipuram residents cannot collect",
        "Complaint to CCMC water division in Ramanathapuram no response for many days",
        "Water pressure too low to fill overhead tank on fourth floor in RS Puram",
        "Sewage water mixing with drinking water supply in Kuniyamuthur very dangerous situation",
        "Newly laid pipeline in Vellalore has leakage wasting water all day long",
        "TDS levels very high in supplied water in Thudiyalur white deposit on utensils",
        "Water board officials ignoring written complaints in Perur for last 10 days",
        "Water supplied only at 4 AM in Vadavalli when no one awake to collect",
        "Brownish smelly water from taps in Singanallur since festival season started",
        "Pressurised supply causing pipe bursts at multiple homes in Eachanari area",
        "Water stagnation in sump due to irregular supply breeding mosquitoes in Ganapathy",
        "Residents of Saravanampatti forced to buy mineral water for drinking and cooking",
        "No warning before 2 day water cut in Race Course only informed via newspaper",
        "Contaminated water with sewage floaters visible in Peelamedu colony residents worried",
        "Prolonged no water in Kalapatti residents walking 500 metres to public tap",
        "Overhead tank overflowing in Thudiyalur no telemetry system installed in ward",
        "Pipeline leakage on Sathy Road wasting potable water for over three weeks",
        "Borewell motor in Vadavalli area burnt due to voltage fluctuation no water",
        "TWAD officials not attending complaint about contaminated water in Saravanampatti",
        "Water tanker damaged on road near Kuniyamuthur no alternative arrangement made",
        "Water supply timing changed without notice in Ganapathy residents missed collection",
        "Hand pump in Eachanari village dried up villagers walking 2 km for water",
        "Corporation water mixed with sewage near Irugur residents falling sick",
        "No water to overhead tank in Government school in Thudiyalur children sent home",
        "Pipeline laid 2 months ago in RS Puram still not connected to supply",
        "Water pressure dropped to zero in Race Course colony during summer peak",
        "Municipal water supply in Vadavalli contains sand particles damaging washing machines",
        "Tanker water supply stopped in Peelamedu colony without prior intimation to residents",
        "TWAD pipeline burst on Avinashi Road flooding the area for third time this year",
        "RO plant in Singanallur village not working since installation residents frustrated",
        "Water supply line damaged during road work on Perur Road no restoration yet",
        "Unauthorised tapping of water line in Ganapthy causing low pressure in whole street",
        "No water for irrigation in Vadavalli farmlands TWAD canal dry for weeks",
        "Water supplied only during odd hours in Ramanathapuram elderly cannot carry at night",
        "Sump at Thudiyalur water tower not cleaned for months algae growing inside",
        "Pipeline crossing under Mettupalayam Road leaking causing road subsidence danger",
        "Water bill charged despite no supply for 2 months in Saravanampatti locality",
        "Borewell in Kalapatti colony motor seized no water for 200 families",
        "TWAD tanker delivering only half capacity in Eachanari village residents protesting",
        "Tap water in Kovaipudur has strange colour residents afraid to drink or cook",
        "Water supply timing clashes with office hours in RS Puram no alternative shift",
        "Open well in Vellalore polluted by nearby septic tank not usable for months",
        "Pipeline laid on Sathy Road near Chinnavedampatti leaking from day one poor quality",
        "Water tank in Kuniyamuthur area not cleaned for over a year green slime inside",
        "Borewell water in Ganapathy has high iron content staining clothes and utensils",
        "No summer water supply contingency plan in Vadavalli residents suffering severe shortage",
        "Water connection for new house in Thudiyalur delayed by 4 months no reason given",
        "Municipal supply water smells of chlorine in Singanallur residents cannot drink",
        "Pipeline trench on Avinashi Road not closed properly causing accident risk",
        "TWAD not responding to burst pipe complaint in RS Puram for over a week",
        "Water cut announced but no alternative tanker arrangement in Race Course colony",
        "Tap water in Kuniyamuthur has muddy colour especially after every rainfall event",
        "Borewell in Thudiyalur school dried up children forced to bring water from home",
        "Water supply line valve broken near Gandhipuram tower water gushing for days",
        "Pipeline leak on main road near Peelamedu wasting thousands of litres daily",
        "Water tanker bribery rampant in Ramanathapuram residents paying extra for supply",
        "Sump motor at Vadavalli water station burnt no backup pump arranged",
        "Corporation water TDS level dangerously high in Eachanari area health concern",
        "No drinking water facility at Ukkadam bus stand passengers suffering in heat",
        "Pipeline burst near Perur temple flooding the courtyard devotees facing difficulty",
        "Water connection application in Ganapathy pending for 6 months no update from TWAD",
        "Village tank in Saravanampatti drying up livestock drinking from contaminated source",
        "Overhead tank in Kalapatti leaking from rusty bottom water seepage on road",
        "Water supply to apartment in RS Puram restricted to 1 hour per day",
        "TWAD pipeline laid across private land in Singanallur causing dispute no water",
        "Borewell motor replacement in Thudiyalur ward delayed ward councillor not responding",
        "Water supplied in tankers only to VIP areas in Ganapthy common people ignored",
        "Reservoir cleaning schedule in Vadavalli not followed for months green deposits inside",
        "Corporation water meter faulty in Peelamedu overcharging residents for no supply",
        "Tap water in Irugur has foul smell residents storing water for days before use",
        "No summer action plan from TWAD for Kovaipudur area severe water shortage expected",
        "Water tower in Eachanari leaking from top wasting water continuously for weeks",
        "Pipeline blockage in Vellalore due to airlock residents getting only trickle water",
        "TWAD complaint number always busy in Kuniyamuthur no way to report issues",
        "Borewell water in Thudiyalur has high fluoride content dental problems in children",
        "Water tanker supply in Saravanampatti irregular no fixed schedule or route",
        "Pipe burst on main road near Race Course jetting water onto road surface",
        "Rainwater harvesting structure at Vadavalli school broken not collecting any water",
        "Water connection for poor colony in Multinagar delayed councillor not interested",
        "Pipeline laid on footpath in RS Puram blocking pedestrian movement for weeks",
        "Residents of Kalapatti forced to dig borewell due to no corporation water",
        "Tanker water quality poor in Singanallur muddy water supplied after every rain",
        "Water scarcity in Ganapathy textile area workers cannot get drinking water during shift",
        "Sump overflow at Thudiyalur water station due to faulty float valve water wasted",
        "No water for 10 days in Peelamedu colony despite paying advance water tax",
        "Pipeline installed on Perur Road too shallow damaged by vehicle movement multiple times",
        "TWAD pipeline crossing canal in Vadavalli exposed and at risk of damage",
        "Corporation water containing worm like particles in Saravanampatti residents complaining",
    ]
    for t in water:
        data.append({"text": t, "category": "Water Supply"})

    # ── Waste Management (100) ──────────────────────────────────────────────
    waste = [
        "Garbage collection missed for 2 weeks in Saravanampatti streets stinking badly",
        "Overflowing bins at Gandhipuram bus stand very unhygienic foul smell throughout area",
        "Construction debris dumped illegally on service road near Vadavalli bypass road",
        "No garbage pickup in Kovaipudur for over 20 days waste piling up fast",
        "Garbage truck comes only once a month to Thudiyalur west side residents suffering",
        "Wet and dry waste mixed up by collection staff in Ganapathy again this week",
        "Garbage bins missing on Sathy Road near Chinnavedampatti no place to dump waste",
        "Kids falling sick due to rotting garbage near school in RS Puram area",
        "Garbage dump near water tank in Kuniyamuthur residents forced to buy bottled water",
        "Waste contractor not attending phones in Ramanathapuram complaints completely ignored",
        "Overflowing bin near Ukkadam bus stop attracting stray dogs and spreading disease",
        "Residents throwing garbage into storm water drain in Vellalore no collection service",
        "Garbage dumped on vacant site near Perur temple breeding mosquitoes and flies",
        "Waste collection vehicle too small for entire ward in Vadavalli needs bigger truck",
        "Household waste piled near temple entrance in Rathinapuri residents burning it sometimes",
        "CCMC workers come only for photos after media reports no actual ground work",
        "Vegetable market waste piled up near Singanallur bus stop polluting entire road",
        "Collection staff demand extra money for lifting bulk waste in Race Course area",
        "Stray dogs tearing garbage bags near school in Peelamedu every evening scaring kids",
        "Sweepers not coming for past week in Thudiyalur streets stinking in summer heat",
        "Plastic waste dumped near Perur temple tank no segregation done by collection staff",
        "Compost pit overflowing with mixed waste near Vadavalli ward office foul smell",
        "Waste collection time never followed in Gandhipuram truck arrives at random times",
        "Garbage bins shifted from street to empty plot causing blockage in Eachanari",
        "Dead animals not picked up by CCMC near Trichy Road foul smell for days",
        "Mixed waste dumped in open plot near Ganapathy lake polluting groundwater table",
        "No door to door collection in Kalapatti colony residents dumping on roadside",
        "Garbage truck spills waste while collecting on Sathy Road leaving mess every time",
        "Waste segregation awareness board installed but no actual implementation in Kuniyamuthur",
        "Burning garbage near RS Puram residential area causing toxic smoke health hazard",
        "Biomedical waste from clinic dumped in regular bin near Singanallur very dangerous",
        "Street sweepers skip Thudiyalur main road entire stretch of garbage for 3 weeks",
        "Commercial waste from market dumped on residential street in Ramanathapuram foul smell",
        "Night garbage collection announced but truck never came to Vadavalli area ever",
        "Plastic ban not enforced in Gandhipuram shopkeepers still using banned plastic bags",
        "Garbage pile at Eachanari road junction blocking view for drivers accident risk",
        "Food waste from restaurants dumped on roadside in Race Course attracting street dogs",
        "Bulk waste pickup scheduled for Peelamedu never happened residents sitting with waste",
        "Mixed construction debris dumped in storm water drain in Saravanampatti blocking flow",
        "Garbage collection in Kovaipudur uses open truck waste falling along entire route",
        "Dead dog on road near Kuniyamuthur temple not removed for 5 days stinking",
        "Waste collector skips our street every Tuesday in Ganapthy despite repeated requests",
        "Open garbage dump near Ukkadam lake contaminating waterbody serious environmental issue",
        "Cardboard and paper waste piled high near Vellalore recycling centre causing fire risk",
        "Garbage truck breaks down frequently in Thudiyalur no backup vehicle arranged ever",
        "Leaves and garden waste not collected in Vadavalli colony residents burning them",
        "Waste dumped on railway track near RS Puram causing fire hazard from sparks",
        "E waste from office dumped in regular bin near Singanallur no separate collection",
        "Garbage collection timing changed without notice in Saravanampatti residents missed pickup",
        "Marriage hall waste dumped on roadside near Eachanari left to rot in sun",
        "Waste from fish market in Kuniyamuthur not cleared for days unbearable stench",
        "Dustbins installed at Gandhipuram bus stand never emptied overflowing constantly",
        "Plastic waste choking nala in Ramanathapuram area flood risk during monsoon",
        "Waste collection vehicle damaged road side drain in Vadavalli no compensation given",
        "Garbage heap near Perur temple attracting monkeys and stray dogs nuisance increasing",
        "Residents association request for extra bin in Peelamedu colony denied by CCMC",
        "Commercial waste from textile unit dumped in residential bin in Ganapathy area",
        "Garbage collection in our lane happens only when we call repeatedly very unreliable",
        "Waste dumped in vacant plot near Race Course school children playing near garbage",
        "Open burning of waste in Kalapatti industrial area causing respiratory issues for nearby residents",
        "Garden waste dumped on Thudiyalur lake bund blocking walking path for morning walkers",
        "Single use plastic waste littering Sathy Road despite ban on plastic items",
        "Waste from chicken shop dumped in open drain near RS Puram market unsanitary",
        "Garbage pile on road near Mettupalayam Road junction causing vehicles to swerve",
        "Demolition waste dumped on footpath in Eachanari pedestrians forced to walk on road",
        "Dustbin at Saravanampatti bus stop broken garbage spilling onto pavement constantly",
        "Waste collector threw garbage into neighbour yard after argument in Kuniyamuthur",
        "Hospital waste found in regular garbage dump near Singanallur very serious safety risk",
        "Garbage truck splashing waste water on pedestrians in Thudiyalur no consideration",
        "Temple waste flowers dumped in water body near Vadavalli polluting pond",
        "Garbage collection in Ganapathy colony skips lanes with narrow access discrimination",
        "Open waste dump near Race Course railway station passengers complain about smell",
        "Dead cat on road near Peelamedu junction not removed despite multiple complaints",
        "Waste segregation bins installed in Perur but both bins mixed during collection useless",
        "Garbage pile near Kalapatti bus stop children playing among waste health risk",
        "Market waste dumped in residential area in Ramanathapuram causing fly infestation",
        "Waste from hotels thrown into open drain in Kuniyamuthur blocking flow completely",
        "Residents composting kitchen waste but CCMC collects only mixed waste discouraging efforts",
        "Garbage truck uses hooter at 5 AM disturbing sleep in Thudiyalur every day",
        "Mixed waste dumped in organic bin in Vadavalli colony defeating purpose of segregation",
        "Dustbin placement in Saravanampatti market area insufficient for crowd garbage everywhere",
        "Construction debris piled on road near Eachanari temple causing traffic obstruction daily",
        "Waste dumped near water pipeline in RS Puram risk of drinking water contamination",
        "Old furniture and mattress dumped on roadside near Singanallur not collected for weeks",
        "Garbage collection in our street happens only after multiple calls to helpline",
        "Plastic waste burned behind apartment in Ganapathy toxic fumes entering homes",
        "Waste from street food vendors left on road near Ukkadam bus stand every night",
        "Burning of leaves in Vadavalli colony causing smog in evening hours regularly",
        "Garbage heap near Vellalore check post visible from main road eyesore for visitors",
        "Waste collection crew damaged gate while collecting in Kuniyamuthur colony no apology",
        "Oil waste from mechanic shop dumped in drain near Peelamedu causing blockage",
        "Industrial waste dumped in residential area of Kalapatti serious environmental health hazard",
        "Garbage on railway overbridge near Gandhipuram wind blowing litter onto tracks",
        "No garbage collection in newly added ward area in Thudiyalur extension for months",
        "Single bin provided for 100 houses in Vadavalli colony completely inadequate capacity",
        "Construction waste dumped near water tank in Perur contaminating groundwater source",
        "Waste burning in Eachanari open field causing respiratory disease in nearby residents",
    ]
    for t in waste:
        data.append({"text": t, "category": "Waste Management"})

    # ── Sanitation (100) ────────────────────────────────────────────────────
    sanitation = [
        "Drainage outlet clogged with plastic waste on Sathy Road near Saravanampatti area",
        "Open drain overflowing during rains entering homes in Ganapathy colony every year",
        "Drain cover missing on Avinashi Road near Peelamedu hazard for pedestrians at night",
        "Blocked drain causing water stagnation and foul smell near Gandhipuram bus stand",
        "Drainage channel choked with construction debris on Mettupalayam Road bypass stretch",
        "Stagnant water in open drain near school in Vadavalli health risk for children",
        "Manhole cover broken for 3 weeks on Trichy Road near Irugur very dangerous",
        "Rainwater mixing with sewage due to choked drain in RS Puram every monsoon",
        "Encroachment of drain by shopkeepers in Ukkadam causing water logging each rain",
        "Desilting of main drain desperately needed before monsoon in Singanallur area",
        "Stinking drain water on Pollachi Road near Kuniyamuthur market no action taken ever",
        "Drainage clogged by plastic waste after festival in Thudiyalur not cleaned yet",
        "Cover missing on storm water drain near Perur temple entrance danger for kids",
        "Mosquito breeding in standing drain water in Vellalore colony health officials ignore",
        "Child fell into open drain in Rathinapuri cover missing for over a month reported",
        "Choked drain behind apartments in Race Course releasing bad odour throughout day",
        "Rains bring sewage water into ground floor homes in Eachanari western extension colony",
        "Water logging for 3 hours every rain near Vadavalli bus terminus due to choked drain",
        "Overflowing drain near market in Thudiyalur health department requested to inspect",
        "Silt in storm water drain not cleared from past year in Saravanampatti area",
        "Covered drain reopened for utility repair not closed back in Ganapathy bridge area",
        "Drainage maintenance on paper no actual desilting done on ground in Kuniyamuthur",
        "Chicken shop waste thrown into drainage near cinema road in Singanallur blocked",
        "Cross drainage near bridge at Eachanari choked no water outlet during rain",
        "Sewage drain broken near market in Vadavalli causing fly infestation and smell",
        "Open drain in front of RS Puram school children walking near sewage every day",
        "Underground drainage pipe collapsed on Sathy Road sewage leaking onto road surface",
        "Drain cover stolen from Gandhipuram bus stand area open pit risk for pedestrians",
        "Sewage water backing up into bathroom in Thudiyalur house due to main line block",
        "Drainage work incomplete on Avinashi Road trench left open for weeks causing accidents",
        "Open drain next to Perur temple devotees walking through sewage polluted water",
        "Storm water drain blocked by silt at Vadavalli lake outlet water not flowing out",
        "Sewage treatment plant near Eachanari residential area releasing untreated waste smell",
        "Manhole overflowing in Race Course main road sewage flowing on road for days",
        "Drainage connection missing for new houses in Kuniyamuthur extension residents suffering",
        "Open drain in Ganapthy colony breeding mosquitoes during rainy season dangerous",
        "Sewage line broken under Trichy Road causing road subsidence need urgent repair",
        "Drainage channel behind Singanallur market choked with vegetable waste from vendors",
        "Cover slab damaged on main drain near Kalapatti heavy vehicles may collapse it",
        "Stagnant sewage water in Vellalore drain attracting flies and causing bad odour",
        "Rain water drain blocked with garbage in Saravanampatti flooding streets every monsoon",
        "Sewage overflow from manhole near Thudiyalur school creating unhygienic conditions for students",
        "Drainage connection illegally diverted by neighbour in RS Puram causing dispute",
        "Open drain near Ukkadam fish market extremely foul public urinating in area",
        "Drainage water mixing with drinking water pipeline in Peelamedu health emergency",
        "Choked drain at Vadavalli bus stand water pooling passengers unable to board buses",
        "Sewage leak from apartment complex in Race Course flowing into neighbour compound",
        "Drain cleaning not done in Ramanathapuram for over 6 months residents complaining",
        "Storm water drain in Eachanari encroached by building construction causing flooding",
        "Open drain near Mettupalayam Road pedestrian crossing people step into sewage",
        "Drainage overflow during light rain itself indicating chronic blockage in Singanallur",
        "Manhole cover not replaced after cable work in Ganapathy cable company negligent",
        "Sewage water entering park in Thudiyalur children playing in contaminated area",
        "Drain line from market to treatment plant broken in Kuniyamuthur waste exposed",
        "Cover missing on drain near Kalapatti bus stop elderly resident fell and injured",
        "Drainage system not designed for current population in Vadavalli old colony",
        "Sewage flow blocked by tree root infiltration in RS Puram drain line",
        "Open drain near Perur temple tank sewage flowing into holy water devotees upset",
        "Storm water drain outlet to lake blocked in Vellalore water not draining out",
        "Manhole cover cracked near Chinnavedampatti junction heavy traffic may break through",
        "Drainage pipe size insufficient for apartments in Ganapathy sewage backing up",
        "Open drain in front of hospital in Eachanari patients exposed to infection risk",
        "Sewage overflow during festival at Singanallur temple visitors complained about stench",
        "Drain cleaning debris left on road in Saravanampatti not removed for days",
        "Cover slab broken on main road drain in Thudiyalur bus drives over it danger",
        "Untreated sewage water from town flowing into Vadavalli lake killing fish",
        "Drain connection charges collected by CCMC but work never started in Kuniyamuthur",
        "Open drain near Peelamedu industrial estate workers throwing waste into it",
        "Sewage line trench dug but not covered for weeks in Race Course road",
        "Drainage in Ganapathy market area blocked every week due to inadequate size",
        "Manhole cover stolen from Trichy Road near Eachanari risk for night traffic",
        "Drainage water seeping into ground floor homes in RS Puram monsoon season",
        "Toilet waste from railway station flowing into open drain near Thudiyalur area",
        "Sewage overflow at Saravanampatti bus stop commuters forced to walk through it",
        "Drainage repair done on Vadavalli main road not compacted properly road sinking",
        "Open drain near Perur vegetable market attracts dogs and rats into area",
        "Sewage line connection denied for poor colony in Kalapatti no basic sanitation",
        "Drain cleaning chemicals used but not followed by water wash residue on road",
        "Cover slab damaged at Ganapthy junction drain for buses to drive over",
        "Sewage overflow in basement of apartment in Race Course health hazard for residents",
        "Open drain water used for gardening in Singanallur area health risk for consumers",
        "Drainage in Ramanathapuram blocked since festival season waste not removed yet",
        "Manhole overflowing near Kuniyamuthur temple visitors complained about stench and flies",
        "Drainage line laid parallel to water line in Vadavalli risk of cross contamination",
        "Sewage treatment plant in Thudiyalur not operating residents discharge untreated into canal",
        "Drain water entering playground in Eachanari children getting skin infections playing there",
        "Cover slab missing from RS Puram market drain vegetable waste falling inside",
        "Open drain in Kalapatti colony stagnant for months no desilting done by CCMC",
        "Sewage from high rise building in Gandhipuram flowing into neighbour property dispute",
        "Drainage repair on Avinashi Road done with poor material already cracked within month",
        "Manhole at Ganapathy bus stop overflowing every evening during peak hours nuisance",
        "Storm water drain converted to sewage drain in Vadavalli colony illegal connections",
        "Drainage blockage due to silt accumulation in Thudiyalur market area every year",
        "Sewage pipe burst near Perur road causing foul smell and health issues",
        "Open drain in Singanallur colony breeding snakes and rats residents terrified",
        "Drainage work started in Eachanari but abandoned for 2 months incomplete",
        "Manhole cover not fitting properly in RS Puram road making noise when vehicles pass",
    ]
    for t in sanitation:
        data.append({"text": t, "category": "Sanitation"})

    # ── Street Lighting (100) ───────────────────────────────────────────────
    street_light = [
        "LED street light not working for a week near Gandhipuram bus stand road",
        "Multiple street lights out on Sathy Road near Ganapathy for past month",
        "Street light pole bent by vehicle impact on Avinashi Road near Peelamedu",
        "Light pole sparking dangerously during rain near RS Puram junction safety risk",
        "Entire stretch of Maruthamalai Road dark after 8 PM women scared to walk",
        "LED light flickering continuously near Thudiyalur tank disturbing sleep at night",
        "No streetlight on service road near Vadavalli stretch pitch dark after sunset",
        "Street light pole tilting dangerously after lorry hit on Trichy Road junction",
        "Newly installed LED on Sathy Road not working from day one near Saravanampatti",
        "Most streetlights not working on NSTV road near Kalapatti depot total darkness",
        "Fuse box issue causing all 5 lights on lane to go out after rain",
        "Street light cable cut during road digging near Vellalore colony not restored",
        "No light on pedestrian subway near Ukkadam bus stand back entrance very dark",
        "Street light not working for 3 months near Singanallur police station ignored",
        "Half the lights on Mettupalayam Road flicker intermittently near Ganapthy area",
        "Light pole grounding creating electric shock risk near Kovaipudur school children",
        "Complete darkness on Pollachi Road near Kuniyamuthur after 7 PM accident risk high",
        "Streetlight wires hanging low near Eachanari arcot road touching ground dangerous",
        "Only 1 of 4 pole lights working on Perur temple road western end dark",
        "Too dim light near Vadavalli hospital forcing relatives to use mobile phones",
        "Underground cable damaged during road work no light for 2 weeks in Rathinapuri",
        "Street light at Irugur signal dead causing accident risk at night crossing",
        "Kids cannot play safely outside due to no working light in Thudiyalur colony",
        "No light on link road between Saravanampatti and Chinnavedampatti pitch dark area",
        "Multiple damaged poles on road to Eachanari no maintenance since many years",
        "Street light near RS Puram market not working shopkeepers facing safety issues",
        "Lamp post knocked down by vehicle on Avinashi Road not replaced for months",
        "No street lighting on footpath near Town Hall elderly falling in dark",
        "Street light timer set incorrectly lights on at 10 PM instead of 6 PM",
        "Light pole wiring exposed near Gandhipuram bus stop children may get electrocuted",
        "Street light on Sathy Road near Hope College flickering for weeks no repair",
        "Road divider lights all broken on Avinashi Road flyover no illumination at night",
        "Street light covers stolen from poles near Peelamedu station lights exposed to rain",
        "Solar street light installed but not charging in Vadavalli area useless at night",
        "Pedestrian crossing at Ganapathy junction no street light dangerous for crossing",
        "Street light pole at Race Course road shaking in wind may fall anytime",
        "Basketball court light in Thudiyalur park not working kids playing in dark",
        "No street light on bridge over canal near Mettupalayam Road accident waiting to happen",
        "All street lights out in Kuniyamuthur market area after transformer failure last week",
        "Street light on Perur Road casting light into homes residents cannot sleep",
        "LED light in Saravanampatti colony making buzzing noise disturbing elderly residents sleep",
        "Street light pole used for advertisement hoarding causing extra load risk",
        "Underground cable fault in Ganapathy colony 3 lights not working for a month",
        "Road widening removed street lights in Vellalore not reinstalled total darkness",
        "Street light broken by branch fall during storm in Singanallur not repaired yet",
        "No street light on Kalapatti main road heavy vehicles cannot see pedestrians",
        "Park lights not working in Thudiyalur children playground closed after sunset",
        "Street light timer faulty lights on during daytime wasting electricity for weeks",
        "Bus shelter light not working near RS Puram passengers cannot see bus numbers",
        "Newly laid road in Vadavalli extension no street lights installed at all",
        "Street light pole at Eachanari temple road tilted dangerously may fall on someone",
        "Light on Mettupalayam Road near Sungam not working for over 6 months",
        "Street light near Ramanathapuram mosque broken community feeling unsafe at night",
        "Power connection to street lights disconnected by TANGEDCO for dues not our fault",
        "Street light in Peelamedu colony making crackling sound residents scared of fire",
        "No street light near water tank in Kuniyamuthur women afraid to fetch water at night",
        "Decorative lights on Town Hall road not working since festival season ended",
        "Street light glare from new LED too bright for homes along Sathy Road",
        "Light fixture hanging loose from pole in Ganapathy could fall on pedestrian",
        "No illumination on Trichy Road near Irugur village road very dangerous for walking",
        "Street light on Thudiyalur lake bund broken visitors cannot use walking track at night",
        "Street light at RS Puram junction not working signal also affected in dark",
        "Light pole foundation exposed after rain in Vadavalli may collapse in wind",
        "Street light covers not replaced after maintenance in Eachanari bulbs exposed to rain",
        "Garden lights in Perur temple park all broken no night time access for visitors",
        "No lighting on staircase of pedestrian bridge over Avinashi Road elderly struggling",
        "Street light wiring theft in Saravanampatti area lights out for many days",
        "Light dimmer sensor not working in Gandhipuram lights bright all night power waste",
        "Road median lights broken on Sathy Road near Chinnavedampatti glare from oncoming vehicles",
        "No street light near Kalapatti bus stop passengers waiting in complete darkness",
        "Street light pole damaged by truck near Ganapthy leaning onto house wall",
        "LED street light in Thudiyalur colony too dim not illuminating road properly",
        "Solar light battery dead in Vadavalli park light not working for month",
        "Street light in Kuniyamuthur slum area not working drug activity increasing at night",
        "Light pole wires hanging low near school in Singanallur danger for children playing",
        "No street light on Mettupalayam Road service road bikers cannot see potholes at night",
        "Street light on Avinashi Road near L&T Bypass knocked down not replaced for year",
        "Light fixture making buzzing noise in Race Course residents disturbed at night",
        "Narrow lane in RS Puram has no light residents install own bulbs outside home",
        "Street light timer set for 6 AM off time lights on whole day waste",
        "Parking area near Eachanari temple no light vehicles parked in darkness risk",
        "Street light bulbs stolen from poles in Saravanampatti no replacement action taken",
        "No street lighting on link road connecting Vadavalli to Thudiyalur pitch dark at night",
        "Light pole installed in middle of footpath in Ganapathy blocking pedestrian movement",
        "Street light broken during storm in Peelamedu not repaired for over two months",
        "Road markings invisible at night due to no street light on Kalapatti stretch",
        "Light on bus shelter at Kuniyamuthur broken passengers cannot read bus timings",
        "Street light in Ramanathapuram junction not working causing accident near miss incidents",
        "Temple entrance on Perur Road dark after 7 PM elderly devotees falling",
        "Street light on Singanallur main road dimming and brightening randomly electrical fault",
        "No light on playground in Thudiyalur children playing cricket in darkness risk",
        "Street light pole used for tying cattle in Vadavalli pole bent from weight",
        "LED street light in Ganapathy emitting blue light too harsh for residents eyes",
        "Light on Eachanari culvert not working accident waiting to happen at night",
        "Street light at Saravanampatti junction broken after accident not replaced for months",
        "Floodlight at bus terminus in Gandhipuram not working passengers in darkness",
        "Street light wire hanging across road in RS Puram lorry may snag and pull down",
        "Solar street light in Vadavalli village panel stolen light not working",
        "No street lighting on newly constructed road in Thudiyalur extension residents scared",
        "Street light in Kuniyamuthur near canal bank broken women avoiding that route at night",
    ]
    for t in street_light:
        data.append({"text": t, "category": "Street Lighting"})

    # ── Electricity (100) ───────────────────────────────────────────────────
    electricity = [
        "Frequent power cuts during evening hours affecting students in RS Puram area",
        "Transformer failure near Gandhipuram bus stand blackout affecting 100 families",
        "Voltage fluctuation damaging fridge and TV in Ganapathy for past whole week",
        "Street lights not getting power on Town Hall road for many days now",
        "Low voltage causing motor burn in borewell in Vadavalli during morning hours",
        "Entire street dark due to fuse off at midnight near Thudiyalur school road",
        "Underground cable snapped during road work near Peelamedu outage for 3 full days",
        "Power cut for 3 hours every alternate day in Saravanampatti no notice given",
        "Transformer oil leak creating fire risk near Singanallur junction need urgent attention",
        "Electric pole leaning dangerously after heavy rain in Kuniyamuthur may fall",
        "Meter box sparking when plugging geyser in Race Course residents scared to use",
        "Low income families most affected by long power cuts in Vellalore colony area",
        "No street light after transformer blast at Eachanari bridge dark at night",
        "Frequent tripping due to illegal power draw by shop in Ukkadam area",
        "TANGEDCO staff not arriving for scheduled repair in Ramanathapuram since many days",
        "Streetlight dim because of load shedding in Gandhipuram colony dark nights unsafe",
        "Single power line serving 200 homes old infrastructure in Thudiyalur failing frequently",
        "TANGEDCO staff demanding bribe for new connection in Kalapatti residents refused",
        "Overloaded transformer sparking near Perur vegetable market dangerous for vendors",
        "Power cut scheduled at 2 AM unsuitable for students in RS Puram exam season",
        "Underground cable waterlogged due to rain in Vadavalli third outage this month",
        "Power restoration after storm took 18 hours in Saravanampatti unbearable summer heat",
        "Three phase current imbalance causing motor vibration in Ganapathy factory area",
        "Live wire hanging low near Mettupalayam Road junction construction site very risky",
        "Transformer replacement done only after media report no action otherwise in Kuniyamuthur",
        "Power surge during rain damaged laptop in Singanallur house no compensation given",
        "Single phase supply during peak hours in Thudiyalur area appliances not working",
        "Electric meter running fast without reason in Race Course overcharging residents",
        "Power line sagging low over road near Vadavalli school bus may snag it",
        "No electricity in newly constructed houses in Eachanari extension for 6 months",
        "Frequent sparking from main junction box in Gandhipuram fire department called twice",
        "Power transformer station near Peelamedu emitting loud hum disturbing neighbours sleep",
        "Voltage too low for air conditioner to start in RS Puram summer unbearable",
        "Electric pole damaged by truck in Saravanampatti leaning on house roof dangerous",
        "No power for water pump in Ganapthy colony residents without water and electricity",
        "Street light pole live wire exposed near Kuniyamuthur children playing in area",
        "Transformer oil spill near Singanallur road slippery hazard for two wheelers",
        "Overhead wire broken due to tree branch in Vadavalli outage for entire street",
        "Power cut without prior intimation in Kalapatti industrial unit production lost",
        "Electric pole foundation loose in Thudiyalur may fall during next storm",
        "Single street draws power from overloaded transformer in Race Course frequent trip",
        "TANGEDCO helpline busy for hours in Ramanathapuram no way to report fault",
        "Earth leakage causing electric shock from water tap in Eachanari house dangerous",
        "Power line passes too close to building in Peelamedu construction halted for safety",
        "No three phase supply in Saravanampatti industrial area production severely affected",
        "Electricity bill shockingly high last month no increase in usage in RS Puram",
        "Transformer in Kuniyamuthur market area overheating during summer needs replacement",
        "Power cut during surgery at clinic in Vadavalli no generator backup available",
        "Electric pole in middle of road in Ganapathy causing traffic obstruction daily",
        "Meter room flood during rain in Thudiyalur meter board sparking risk of fire",
        "No electricity in Perur temple area during evening aarti devotees used mobile lights",
        "Voltage fluctuation burning LED bulbs in Singanallur colony every week",
        "Overhead cable hanging low near school in Gandhipuram children can touch it",
        "Power line damaged by kite string in Race Course area short circuit",
        "Transformer theft in Vellalore area entire village without power for 3 days",
        "TANGEDCO pole installed blocking house entrance in Kalapatti no permission taken",
        "Power cut for 6 hours daily in Eachanari during summer residents suffering heat",
        "Frequent voltage dips damaging computers in RS Puram business area losses mounting",
        "Electric shock from street light pole in Saravanampatti dog died residents fearful",
        "No power backup for water treatment plant in Thudiyalur water supply disrupted",
        "Three phase line snapped in Ganapathy industrial estate production stopped for day",
        "Meter board fire in Kuniyamuthur apartment electrician saved the day by quick action",
        "Power restoration time not communicated in Vadavalli residents waiting hours in dark",
        "Earth wire missing on pole near Peelamedu school risk of electrocution for kids",
        "Transformer noise causing headache for nearby residents in Singanallur colony every night",
        "Electricity pole in Vellalore leaning on tree branch may fall during wind",
        "No power in newly added area of Saravanampatti TANGEDCO says load not sanctioned",
        "Underground cable age causing frequent faults in Race Course every week tripping",
        "TANGEDCO line man not attending complaint in Kalapatti since 2 weeks",
        "Power quality poor in Eachanari voltage fluctuates between 140 and 260 volts",
        "Electric wire touching telecom cable in Thudiyalur risk of electrocution to line workers",
        "No street light due to missing power connection in Vadavalli extension area",
        "Transformer on Sathy Road near Saravanampatti overloaded sparking during peak hours",
        "Electric pole installed on private land without consent in Ganapthy dispute ongoing",
        "Power supply to borewell in Kuniyamuthur disconnected for bill dispute residents suffer",
        "Electric fire in meter box in RS Puram building fire department arrived timely",
        "No power for common area lights in apartment in Singanallur staircase pitch dark",
        "Voltage regulator needed for whole street in Peelamedu frequent damage to appliances",
        "TANGEDCO vehicle never visits our area in Vadavalli for maintenance works",
        "Overhead line damaged by tree branch during storm in Eachanari not repaired",
        "Power supply intermittent in Gandhipuram commercial area shops losing business daily",
        "Electric pole relocation needed for road widening in Kalapatti but TANGEDCO delaying",
        "Meter reading estimated for 6 months in Thudiyalur overcharging for no reason",
        "No power connection for temple in Perur electricians demanding bribe for new line",
        "Transformer station gate broken in Race Course children playing near dangerous equipment",
        "Power cut every evening at 7 PM in Saravanampatti exactly dinner time frustration",
        "Electric shock risk from exposed wire near Ganapathy bus stop commuters at risk",
        "TANGEDCO not replacing fused meter in Singanallur since 3 months billing stopped",
        "Voltage too high in Kuniyamuthur area bulbs blowing every week residents upset",
        "Power cable stolen from construction site in Vadavalli area theft not investigated",
        "Electric pole blocking driveway in Eachanari house cannot bring car inside",
        "Power restoration took 24 hours after storm in RS Puram unacceptable delay",
        "No electricity for water motor in Thudiyalur colony residents water supply affected",
        "TANGEDCO line inspection never happens in Kalapatti despite multiple requests",
        "Electric line passes dangerously close to balcony in Ganapathy apartment safety concern",
        "Power cut without warning during wedding function in Perur ruined the event",
        "Transformer oil leakage contaminating ground in Peelamedu environmental hazard concern",
        "Electric pole in Saravanampatti market area used for tying animals pole shaking",
        "Low voltage during peak summer in Vellalore fans running like slow motion",
        "No power backup for sewage treatment plant in Kuniyamuthur overflow during power cut",
    ]
    for t in electricity:
        data.append({"text": t, "category": "Electricity"})

    # ── Public Health (100) ─────────────────────────────────────────────────
    public_health = [
        "Stagnant water near Vadavalli colony breeding mosquitoes risk of dengue fever",
        "Public toilet near Gandhipuram bus stand not cleaned regularly very unhygienic",
        "Health hazard due to open garbage near school in RS Puram very serious",
        "Dengue prevention fogging not done in Saravanampatti for over a month now",
        "Drainage water stagnant near Eachanari hospital creating mosquito menace for patients",
        "Stray dog population increasing near Ukkadam market no catch van deployed",
        "Rat infestation in old residential area of Thudiyalur very bad pest situation",
        "Water contamination causing stomach illness in Singanallur locality many affected",
        "No mosquito fogging done in Kuniyamuthur despite repeated dengue cases reported",
        "Overflowing public toilet at Perur temple health department need to act immediately",
        "Pest control needed for termites in government school building in Ganapathy",
        "Construction dust causing breathing trouble in Peelamedu locality no action taken",
        "Stray cattle on road near Vadavalli causing accidents and traffic daily problem",
        "Plastic waste burned openly near residential colony in Kalapatti toxic fumes everywhere",
        "Flies from garbage dump near Kovaipudur clinic making patient recovery difficult",
        "Sewage treatment plant near Nanjundapuram not working residents suffering since months",
        "Open drain with sewage right in front of apartment entrance in Race Course",
        "Methane gas smell near dump yard in Vellalore residents severely affected by odour",
        "Water stagnation near Eachanari road breeding mosquitoes in large numbers daily",
        "Public health camp needed for workers at SIDCO industrial estate area",
        "Stray dogs entering garbage dump in Rathinapuri spreading waste on entire road",
        "No dustbins near Thudiyalur bus stand causing littering and health risk for public",
        "Waterborne disease spreading in Kuniyamuthur slum needs medical team urgently deployed",
        "Accumulated hospital waste behind private nursing home in Ganapathy very unsanitary",
        "Air quality poor near SIDCO estate due to industrial smoke residents falling sick",
        "Open defecation near railway track in Thudiyalur unhygienic and unsafe for women",
        "Fogging machine broken in Saravanampatti mosquito spraying not happening for weeks",
        "Stagnant water in unused construction site in RS Puram breeding mosquitoes daily",
        "Food stall near Gandhipuram bus stand operating without hygiene license health risk",
        "Community toilet in Vadavalli locked for months residents forced to go outside",
        "Dengue patient reported in Kuniyamuthur street fogging still not done by authorities",
        "Tyre burning in Kalapatti industrial area causing black smoke respiratory issues",
        "Stray dogs chasing children near school in Singanallur municipality not catching them",
        "Open garbage attracting flies into restaurant in Ganapathy health department ignore",
        "No clean drinking water facility at Eachanari bus stand passengers suffering in heat",
        "Rat burrows along drain in Race Course park dangerous for children playing",
        "Mosquito net distribution not done in Vellalore malaria prone area",
        "Public health nurse not visiting Thudiyalur colony despite pregnancy cases in area",
        "Dead animals rotting on roadside in Saravanampatti not cleared by CCMC for days",
        "Uncovered manhole near Perur temple breeding flies and mosquitoes health risk",
        "Plastic waste burning in Peelamedu residential area causing coughing and eye irritation",
        "Sewage overflow near playground in Vadavalli children playing in contaminated water",
        "Stray dog bite cases in Ramanathapuram not reported to health department",
        "Toilet facility missing for women at Ukkadam market unhygienic conditions",
        "Fumigation not done in Kuniyamuthur market despite cholera scare in area",
        "Dust from construction site in Ganapathy not controlled respiratory problems for neighbours",
        "Open drain near Singanallur school children exposed to sewage daily health hazard",
        "Public health awareness camp never conducted in Kalapatti colony residents ignorant",
        "Burning of waste in Eachanari fields causing smog in evening hours regularly",
        "Stray cow injured on road in Thudiyalur no animal rescue team deployed",
        "Mosquito breeding in discarded tyres at RS Puram garage serious dengue risk",
        "Overflowing septic tank in Vadavalli apartment sewage flowing on road unhygienic",
        "Pest control spray in Gandhipuram market not done flies sitting on food items",
        "No health inspection of eateries in Saravanampatti for months hygiene poor",
        "Dead bird found near water tank in Kuniyamuthur possible bird flu concern",
        "Fogging vehicle passes but does not spray in interior lanes of Ganapathy",
        "Stray dog pack in Vellalore attacking two wheeler riders municipality must act",
        "Public toilet at Eachanari bus stand locked for months passengers suffer",
        "Water storage tank in Thudiyalur not chlorinated regularly residents getting stomach infection",
        "Industrial smoke from Kalapatti factory causing asthma attacks in nearby children",
        "Mosquito breeding in open well in Peelamedu not covered residents worried about dengue",
        "Rat infestation in Perur temple kitchen food hygiene concern for devotees",
        "No garbage collection in RS Puram market for week rotting vegetables health hazard",
        "Community health centre in Vadavalli lacks basic medicines patients referred elsewhere",
        "Stray dogs barking all night in Race Course colony residents deprived of sleep",
        "Flies and mosquitoes from dump yard near Singanallur colony unbearable in evening",
        "Dengue larva found in water samples from Kuniyamuthur action taken only after report",
        "Tobacco products sold near school in Ganapathy no enforcement of Cigarettes Act",
        "Open drain in Thudiyalur market has dead rat floating health department not bothered",
        "Child vaccination camp not held in Saravanampatti area for 3 months",
        "Plastic waste dumped near water body in Vellalore toxins leaching into pond",
        "Fogging chemical causing skin irritation in Vadavalli residents complaining about side effects",
        "Sewage water used for vegetable farming in Eachanari health risk for consumers",
        "No anti rabies vaccine at RS Puram government hospital dog bite victim referred",
        "Stagnant water in Ganapthy construction site breeding thousands of mosquitoes daily",
        "Public health inspector never visits Peelamedu colony despite repeated complaints about hygiene",
        "Hospital waste incinerator in Kuniyamuthur emitting black smoke residents worried",
        "Dust from stone crusher near Singanallur causing lung problems in workers",
        "Open urination near Thudiyalur bus stand foul smell health hazard for commuters",
        "Mosquito fogging time inconvenient for elderly in Vadavalli done at late night",
        "Stray dog sterilization program not implemented in Kalapatti dog population exploding",
        "Water sample from Perur tap tested positive for coliform bacteria health emergency",
        "No hygienic toilet facility for auto drivers at Gandhipuram stand they use roadside",
        "Rat poison placed in open areas of Race Course park risk for children and pets",
        "Dust from road construction in Saravanampatti not controlled by water sprinkling",
        "Flies in operating room at government clinic in Thudiyalur infection risk for patients",
        "Open garbage heap in Ganapathy residential area causing asthma and skin allergy",
        "Uncollected biomedical waste from Eachanari clinic dumped in regular bin very dangerous",
        "Mosquito breeding in coconut shells and discarded containers in RS Puram garden",
        "Public health department not responding to complaints in Vellalore for over month",
        "Children in Kuniyamuthur slum showing symptoms of waterborne disease needs investigation",
        "Stray cattle eating from garbage dump in Singanallur then milk sold in market",
        "Fogging machine operator sleeping during duty in Saravanampatti colony ineffective spraying",
        "Open drain cleaning causing cockroach infestation in nearby homes in Peelamedu",
        "No sanitary napkin vending machine in girls school in Vadavalli health concern",
        "Dead fish in lake near Thudiyalur possible water contamination health warning needed",
        "Pig rearing in residential area of Eachanari foul smell and health hazard",
        "Mosquitoes entering homes despite closed windows in Ganapthy severe infestation problem",
    ]
    for t in public_health:
        data.append({"text": t, "category": "Public Health"})

    return pd.DataFrame(data)


def evaluate(texts, labels, min_df: int, title: str, use_expanded: bool):
    """Train a classifier and report detailed per-class metrics."""
    le = LabelEncoder()
    y = le.fit_transform(labels)

    X_train, X_test, y_train, y_test = train_test_split(
        texts, y, test_size=0.2, random_state=42, stratify=y
    )

    vec = TfidfVectorizer(
        max_features=10000, ngram_range=(1, 2), min_df=min_df,
        max_df=0.95, stop_words='english', lowercase=True, strip_accents='unicode'
    )
    X_train_vec = vec.fit_transform(X_train)
    X_test_vec = vec.transform(X_test)

    clf = LogisticRegression(max_iter=1000, random_state=42, solver='lbfgs', n_jobs=-1)
    clf.fit(X_train_vec, y_train)
    y_pred = clf.predict(X_test_vec)

    accuracy = accuracy_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)
    report = classification_report(y_test, y_pred, target_names=le.classes_, zero_division=0, output_dict=True)

    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}")
    print(f"Dataset: {'Expanded (7 classes, ~700 samples)' if use_expanded else 'Original (5 classes, 32 samples)'}")
    print(f"min_df={min_df}, Train/Test: {len(X_train)}/{len(X_test)}")
    print(f"Accuracy: {accuracy * 100:.2f}%")
    print(f"\nPer-class metrics:")
    print(f"{'Category':<20s} {'Precision':>10s} {'Recall':>10s} {'F1':>10s} {'Support':>10s}")
    print("-" * 60)
    for cls in le.classes_:
        r = report[cls]
        print(f"{cls:<20s} {r['precision']:>10.2f} {r['recall']:>10.2f} {r['f1-score']:>10.2f} {r['support']:>10.0f}")

    # Print misclassified samples
    mis_mask = y_pred != y_test
    mis_texts = X_test[mis_mask]
    mis_true = le.inverse_transform(y_test[mis_mask])
    mis_pred = le.inverse_transform(y_pred[mis_mask])
    print(f"\nMisclassified samples ({len(mis_texts)} of {len(X_test)}):")
    for i in range(min(len(mis_texts), 15)):
        t = mis_texts.iloc[i] if hasattr(mis_texts, 'iloc') else mis_texts[i]
        print(f"  TRUE={mis_true[i]:20s} PRED={mis_pred[i]:20s}  \"{t[:70]}...\"" if len(t) > 70 else f"  TRUE={mis_true[i]:20s} PRED={mis_pred[i]:20s}  \"{t}\"")

    return {
        'vectorizer': vec, 'classifier': clf, 'label_encoder': le,
        'accuracy': accuracy, 'classes': list(le.classes_), 'report': report
    }


def main():
    output_dir = Path(__file__).parent.parent / 'ai-engine' / 'models' / 'classification'

    # ── BEFORE: Original 32-sample dataset with min_df=2 ────────────────
    old_df = build_old_dataset()
    old_df['text'] = old_df['text'].apply(clean_text)

    old_result = evaluate(
        old_df['text'], old_df['category'],
        min_df=2, title="BEFORE: 32 samples, min_df=2, 5 classes", use_expanded=False
    )

    # ── AFTER: Expanded dataset with min_df=1 ──────────────────────────
    new_df = build_expanded_dataset()
    new_df['text'] = new_df['text'].apply(clean_text)

    new_result = evaluate(
        new_df['text'], new_df['category'],
        min_df=1, title="AFTER: ~700 samples, min_df=1, 7 classes", use_expanded=True
    )

    # ── Summary ─────────────────────────────────────────────────────────
    old_rep = old_result['report']
    new_rep = new_result['report']

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f" {'':20s} {'Before':>10s} {'After':>10s}")
    print("-" * 42)
    print(f" {'Accuracy':20s} {old_result['accuracy']*100:>9.2f}% {new_result['accuracy']*100:>9.2f}%")
    print(f" {'Classes':20s} {len(old_result['classes']):>10d} {len(new_result['classes']):>10d}")
    print(f" {'Train samples':20s} {int(len(old_df) * 0.8):>10d} {int(len(new_df) * 0.8):>10d}")
    print(f" {'Test samples':20s} {int(len(old_df) * 0.2):>10d} {int(len(new_df) * 0.2):>10d}")

    # Per-class comparison for overlapping classes
    overlap = set(old_result['classes']) & set(new_result['classes'])
    if overlap:
        print(f"\nPer-class F1 (overlapping classes):")
        print(f" {'Category':<20s} {'Before':>10s} {'After':>10s}")
        print("-" * 42)
        for cls in sorted(overlap):
            old_f1 = old_rep[cls]['f1-score']
            new_f1 = new_rep[cls]['f1-score']
            delta = new_f1 - old_f1
            arrow = "+" if delta > 0 else ("-" if delta < 0 else "=")
            print(f" {cls:<20s} {old_f1:>10.2f} {new_f1:>10.2f}  {arrow}")

    # New classes only in after
    new_only = set(new_result['classes']) - set(old_result['classes'])
    if new_only:
        print(f"\nNew classes (no before comparison):")
        for cls in sorted(new_only):
            print(f"  {cls}: F1={new_rep[cls]['f1-score']:.2f}, Recall={new_rep[cls]['recall']:.2f}")

    # ── Save NEW model only ──────────────────────────────────────────────
    print(f"\n[SAVING] New model artifacts to {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / 'vectorizer.pkl', 'wb') as f:
        pickle.dump(new_result['vectorizer'], f)
    with open(output_dir / 'classifier.pkl', 'wb') as f:
        pickle.dump(new_result['classifier'], f)
    with open(output_dir / 'label_encoder.pkl', 'wb') as f:
        pickle.dump(new_result['label_encoder'], f)

    metadata = {
        'accuracy': new_result['accuracy'],
        'num_classes': len(new_result['classes']),
        'classes': new_result['classes'],
        'num_train_samples': int(len(new_df) * 0.8),
        'num_test_samples': int(len(new_df) * 0.2),
        'total_samples': len(new_df),
        'model_type': 'TF-IDF + Logistic Regression',
        'feature_params': {
            'min_df': 1,
            'max_features': 10000,
            'ngram_range': '(1,2)'
        },
        'trained_at': datetime.now().isoformat()
    }
    with open(output_dir / 'metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)

    print("[SAVED] Model artifacts to", output_dir)
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f" Before (5 classes, min_df=2, 32 samples): {old_result['accuracy']*100:.2f}%")
    print(f" After  (7 classes, min_df=1, {len(new_df)} samples): {new_result['accuracy']*100:.2f}%")
    old_masked = 3  # Electricity, Public Health, Roads (Roads mislabeled as "Road Infrastructure" so no match)
    print(f" Old model masked {old_masked} classes at 0% recall (Electricity, Public Health not trained at all, Roads mislabeled as 'Road Infrastructure')")
    print(f" New model covers all 7 categories with per-class recall >= {min(new_rep[c]['recall'] for c in new_result['classes']):.0%}")


if __name__ == '__main__':
    main()
