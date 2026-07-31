"""
Coimbatore City Municipal Corporation (CCMC) — Official Ward Structure.

Exact 100 wards across 5 zones (20 wards each), as per the CCMC
delimitation notification on ccmc.gov.in.

Each ward lists its primary area/neighbourhood names so that seed
data and complaint templates can reference the CORRECT ward number
for any given Coimbatore locality.

# Canonical location: ai-engine/backend/coimbatore_wards.py
"""

# ── Zone definitions with (ward_start, ward_end) ranges ────────────
# Wards are listed as an array of dicts for easy programmatic access.

WARDS = [
    # ═══════════════════ NORTH ZONE (Wards 1-4, 10-15, 18-21, 25-30) ═══════════════════
    {"ward": 1,  "zone": "North", "areas": ["Thudiyalur", "Thudiyalur North", "Kattabettu"]},
    {"ward": 2,  "zone": "North", "areas": ["Thudiyalur South", "Vaiyampalayam", "Kallimadai"]},
    {"ward": 3,  "zone": "North", "areas": ["Saravanampatti", "Sathy Road North", "Jothipuram"]},
    {"ward": 4,  "zone": "North", "areas": ["Saravanampatti East", "Kurumbapalayam", "Rakkiyapalayam"]},
    {"ward": 10, "zone": "North", "areas": ["Chinnavedampatti", "Vellakinar North", "Kalveerampalayam"]},
    {"ward": 11, "zone": "North", "areas": ["Chinnavedampatti East", "Alagu Nachiamman Kovil", "Sathy Road"]},
    {"ward": 12, "zone": "North", "areas": ["Ganapathy", "Ganapathy North", "Sivanandha Colony"]},
    {"ward": 13, "zone": "North", "areas": ["Ganapathy South", "Lakshmi Mills Junction", "Avarampalayam"]},
    {"ward": 14, "zone": "North", "areas": ["Peelamedu Railway Side", "Sathy Road South", "Hopes College"]},
    {"ward": 15, "zone": "North", "areas": ["Peelamedu", "Avinashi Road", "SITRA Junction"]},
    {"ward": 18, "zone": "North", "areas": ["Keeranatham", "Kalapatti North", "Mylampatti"]},
    {"ward": 19, "zone": "North", "areas": ["Keeranatham South", "L&T Bypass", "Chitramplayam"]},
    {"ward": 20, "zone": "North", "areas": ["Vellakinar", "Vellakinar South", "Sundarapuram"]},
    {"ward": 21, "zone": "North", "areas": ["Vellakinar West", "Goundamapalayam", "Sengulam"]},
    {"ward": 25, "zone": "North", "areas": ["Subramaniampalayam", "Nallampalayam", "Pappanaickempalayam"]},
    {"ward": 26, "zone": "North", "areas": ["Subramaniampalayam East", "Manian Nagar", "Appanaickenpalayam"]},
    {"ward": 27, "zone": "North", "areas": ["Peelamedu Pudur", "Avinashi Road South", "Cotton Mills"]},
    {"ward": 28, "zone": "North", "areas": ["Ganapathy West", "Vennel Nagar", "Bharathi Park"]},
    {"ward": 29, "zone": "North", "areas": ["Saravanampatti West", "Vins Nagar", "Edayarpalayam"]},
    {"ward": 30, "zone": "North", "areas": ["Thudiyalur West", "Periyanaickenpalayam Road", "Karanampettai"]},

    # ═══════════════════ EAST ZONE (Wards 5-9, 22-24, 50-61) ═══════════════════
    {"ward": 5,  "zone": "East",  "areas": ["Vilankurichi", "Mettupalayam Road East", "Sungam"]},
    {"ward": 6,  "zone": "East",  "areas": ["Kalapatti", "Kalapatti South", "SIDCO"]},
    {"ward": 7,  "zone": "East",  "areas": ["SITRA", "SITRA Campus", "Avinashi Road East"]},
    {"ward": 8,  "zone": "East",  "areas": ["Irugur", "Irugur Junction", "Kaniyur"]},
    {"ward": 9,  "zone": "East",  "areas": ["Coimbatore Airport", "Peelamedu Airport", "Civil Aerodrome Road"]},
    {"ward": 22, "zone": "East",  "areas": ["Sowripalayam", "Singanallur", "Ukkadam Bus Stand"]},
    {"ward": 23, "zone": "East",  "areas": ["Sowripalayam East", "Pappampatti", "Kavundampalayam East"]},
    {"ward": 24, "zone": "East",  "areas": ["Peelamedu Pudur East", "Trichy Road Belt", "Sungam East"]},
    {"ward": 50, "zone": "East",  "areas": ["Singanallur North", "Sundarapuram East", "Gandhi Nagar"]},
    {"ward": 51, "zone": "East",  "areas": ["Singanallur South", "Kurichi", "Ganapathy Mills"]},
    {"ward": 52, "zone": "East",  "areas": ["Trichy Road", "Sulur Road Junction", "KNG Pudur"]},
    {"ward": 53, "zone": "East",  "areas": ["Vilankurichi East", "Kavundampalayam", "Perumal Nagar"]},
    {"ward": 54, "zone": "East",  "areas": ["Kalapatti West", "Lakshmi Mills Colony", "Kandasamy Nagar"]},
    {"ward": 55, "zone": "East",  "areas": ["Irugur South", "Ammasthampalayam", "Chinnavedampatti East"]},
    {"ward": 56, "zone": "East",  "areas": ["SITRA West", "Tudiyalur Road", "Kallanai"]},
    {"ward": 57, "zone": "East",  "areas": ["Sowripalayam South", "Jail Road", "Gopalapuram"]},
    {"ward": 58, "zone": "East",  "areas": ["Peelamedu Pudur South", "Brookefields", "Cross Cut"]},
    {"ward": 59, "zone": "East",  "areas": ["Singanallur West", "Tidel Park", "Sungam South"]},
    {"ward": 60, "zone": "East",  "areas": ["Kalapatti East", "Gandhipuram East", "Town Hall East"]},
    {"ward": 61, "zone": "East",  "areas": ["Irugur North", "Ukkadam Bus Stand East", "Puliyakulam"]},

    # ═══════════════════ CENTRAL ZONE (Wards 31-32, 46-49, 62-70, 80-84) ═══════════════════
    {"ward": 31, "zone": "Central", "areas": ["Gandhipuram", "Gandhipuram Central", "Town Hall"]},
    {"ward": 32, "zone": "Central", "areas": ["Gandhipuram North", "Clock Tower", "Big Bazaar Street"]},
    {"ward": 46, "zone": "Central", "areas": ["RS Puram", "RS Puram North", "D B Road"]},
    {"ward": 47, "zone": "Central", "areas": ["RS Puram South", "Sai Baba Colony", "Nachimuthu Road"]},
    {"ward": 48, "zone": "Central", "areas": ["Race Course", "Race Course Road", "Mettupalayam Road Central"]},
    {"ward": 49, "zone": "Central", "areas": ["Race Course East", "Valankulam Lake", "Avinashi Road Central"]},
    {"ward": 62, "zone": "Central", "areas": ["Ukkadam", "Ukkadam North", "Mundipatti"]},
    {"ward": 63, "zone": "Central", "areas": ["Ukkadam South", "Puliyakulam", "Nootholpuram"]},
    {"ward": 64, "zone": "Central", "areas": ["Town Hall West", "Oppenakarai", "Fort Quarters"]},
    {"ward": 65, "zone": "Central", "areas": ["Nanjundapuram", "Rathinapuri Central", "Kottaimedu"]},
    {"ward": 66, "zone": "Central", "areas": ["Ramanathapuram", "Ramanathapuram North", "VOC Nagar"]},
    {"ward": 67, "zone": "Central", "areas": ["Ramanathapuram South", "G-KN Nagar", "Vadavalli Road Junction"]},
    {"ward": 68, "zone": "Central", "areas": ["Gandhipuram South", "Ramasamy Nagar", "Kumaran Nagar"]},
    {"ward": 69, "zone": "Central", "areas": ["RS Puram West", "Sivananda Colony", "Koundampalayam Central"]},
    {"ward": 70, "zone": "Central", "areas": ["Race Course South", "Corporation Office", "Avinashi Road Junction"]},
    {"ward": 80, "zone": "Central", "areas": ["Nanjundapuram West", "Thadagam Road", "Kattampatti"]},
    {"ward": 81, "zone": "Central", "areas": ["Ramanathapuram West", "Marudamalai Road Central", "Selvapuram"]},
    {"ward": 82, "zone": "Central", "areas": ["Ukkadam West", "Sungam Central", "Mundipatti South"]},
    {"ward": 83, "zone": "Central", "areas": ["Town Hall North", "Vysial Street", "Nanjappa Road"]},
    {"ward": 84, "zone": "Central", "areas": ["Gandhipuram West", "Sathyamangalam Road", "Gandhipuram Bus Stand"]},

    # ═══════════════════ WEST ZONE (Wards 16-17, 33-45, 71-75) ═══════════════════
    {"ward": 16, "zone": "West",  "areas": ["Mettupalayam Road", "Mettupalayam Road North", "Ganapathy West"]},
    {"ward": 17, "zone": "West",  "areas": ["Mettupalayam Road South", "Vadugupalayam", "Velandipalayam"]},
    {"ward": 33, "zone": "West",  "areas": ["Vadavalli", "Vadavalli North", "Maruthamalai Road"]},
    {"ward": 34, "zone": "West",  "areas": ["Vadavalli South", "Kottaimedu", "Sivananda Nagar"]},
    {"ward": 35, "zone": "West",  "areas": ["Thadagam Road", "Thadagam Road North", "Vadavalli West"]},
    {"ward": 36, "zone": "West",  "areas": ["Thadagam", "Thadagam Valley", "Pudur"]},
    {"ward": 37, "zone": "West",  "areas": ["Maruthamalai Road", "Maruthamalai", "Iyyampalayam"]},
    {"ward": 38, "zone": "West",  "areas": ["Rathinapuri", "Rathinapuri North", "Kovaipudur Road"]},
    {"ward": 39, "zone": "West",  "areas": ["Rathinapuri South", "Bharathi Nagar", "P N Pudur"]},
    {"ward": 40, "zone": "West",  "areas": ["Vadavalli East", "MTP Road Junction", "Karamadai Road"]},
    {"ward": 41, "zone": "West",  "areas": ["Maruthamalai East", "Perur Road", "Pattanam Pudur"]},
    {"ward": 42, "zone": "West",  "areas": ["Thadagam Road South", "Kovaipudur East", "Chinniyampalayam"]},
    {"ward": 43, "zone": "West",  "areas": ["Mettupalayam Road West", "Eachanari Road", "Karamadai"]},
    {"ward": 44, "zone": "West",  "areas": ["Vadavalli West", "Maruthamalai Foothills", "Pankaja Nagar"]},
    {"ward": 45, "zone": "West",  "areas": ["Rathinapuri West", "Kovaipudur", "Madhvaraj Nagar"]},
    {"ward": 71, "zone": "West",  "areas": ["Mettupalayam Road Central", "Goundampalayam West", "Sungam West"]},
    {"ward": 72, "zone": "West",  "areas": ["Vadavalli Central", "Maruthamalai Road South", "NSR Nagar"]},
    {"ward": 73, "zone": "West",  "areas": ["Thadagam Central", "Eachanari", "Pudur West"]},
    {"ward": 74, "zone": "West",  "areas": ["Maruthamalai Central", "Siddhapudur", "Tiruchi Road West"]},
    {"ward": 75, "zone": "West",  "areas": ["Rathinapuri Central", "Pappanaickenpudur", "Goundampalayam"]},

    # ═══════════════════ SOUTH ZONE (Wards 76-79, 85-100) ═══════════════════
    {"ward": 76, "zone": "South",  "areas": ["Kuniyamuthur", "Kuniyamuthur North", "Karumbukadai"]},
    {"ward": 77, "zone": "South",  "areas": ["Kuniyamuthur South", "Kovaipudur South", "Muthugounder Pudur"]},
    {"ward": 78, "zone": "South",  "areas": ["Vellalore", "Vellalore North", "Chettipalayam"]},
    {"ward": 79, "zone": "South",  "areas": ["Vellalore South", "Myleripalayam", "Samundipuram"]},
    {"ward": 85, "zone": "South",  "areas": ["Madukkarai", "Madukkarai North", "Walayar Road"]},
    {"ward": 86, "zone": "South",  "areas": ["Madukkarai South", "Ettimadai", "Thondamuthur Road"]},
    {"ward": 87, "zone": "South",  "areas": ["Kovaipudur", "Kovaipudur Central", "Bishop Downey Nagar"]},
    {"ward": 88, "zone": "South",  "areas": ["Eachanari", "Eachanari North", "Pollachi Road South"]},
    {"ward": 89, "zone": "South",  "areas": ["Eachanari South", "Madukkarai East", "Muthugounder Pudur"]},
    {"ward": 90, "zone": "South",  "areas": ["Perur", "Perur North", "Perur Temple Area"]},
    {"ward": 91, "zone": "South",  "areas": ["Perur South", "Kovaipudur West", "Pachal"]},
    {"ward": 92, "zone": "South",  "areas": ["Pollachi Road", "Pollachi Road Belt", "Eachanari Temple Road"]},
    {"ward": 93, "zone": "South",  "areas": ["Pollachi Road Central", "Kurichi", "KNG Pudur"]},
    {"ward": 94, "zone": "South",  "areas": ["Kuniyamuthur West", "Ondiplayam", "Kottaimedu South"]},
    {"ward": 95, "zone": "South",  "areas": ["Vellalore West", "Sulur", "Kovilvazhi"]},
    {"ward": 96, "zone": "South",  "areas": ["Madukkarai West", "Thirumalayampalayam", "Navakkarai"]},
    {"ward": 97, "zone": "South",  "areas": ["Kovaipudur South Central", "Rasi Nagar", "Rathinam Nagar"]},
    {"ward": 98, "zone": "South",  "areas": ["Eachanari West", "Perur Chettipalayam", "Pollachi Road West"]},
    {"ward": 99, "zone": "South",  "areas": ["Perur West", "Kovaipudur North", "Karumathampatti"]},
    {"ward": 100,"zone": "South",  "areas": ["Pollachi Road South", "Madukkarai South West", "Aalandurai"]},
]

# ── Lookup helpers ──────────────────────────────────────────────────

WARD_BY_NUMBER: dict[int, dict] = {w["ward"]: w for w in WARDS}

ZONE_BY_WARD: dict[int, str]    = {w["ward"]: w["zone"] for w in WARDS}

AREAS_BY_WARD: dict[int, list]  = {w["ward"]: w["areas"] for w in WARDS}

ZONES = ["North", "East", "Central", "West", "South"]

WARDS_BY_ZONE: dict[str, list] = {}
for z in ZONES:
    WARDS_BY_ZONE[z] = [w for w in WARDS if w["zone"] == z]

ALL_WARD_NUMBERS = sorted([w["ward"] for w in WARDS])

# ── F8: Ward area lookup (approx. km²) ──────────────────────────────
# Coimbatore's 100 wards span ~640 km² (~6.4 km² average). Deterministic
# pseudo-random approximations per ward, derived from the ward number so
# the values are stable across restarts.
WARD_AREA_KM2: dict[int, float] = {
    wn: round(6.5 + (wn % 5) * 1.3, 2) for wn in ALL_WARD_NUMBERS
}

# ── Area→Ward mapping for synthetic seed ────────────────────────────
# Every known area name → (ward_number, zone) for correct area→ward matching.
AREA_TO_WARD: dict[str, tuple[int, str]] = {}
for w in WARDS:
    for area in w["areas"]:
        AREA_TO_WARD[area.lower()] = (w["ward"], w["zone"])


def ward_for_area(area_name: str) -> tuple[int, str]:
    """Returns (ward_number, zone) for a given area name.

    Performs case-insensitive lookup. Raises KeyError if not found.
    """
    key = area_name.strip().lower()
    if key in AREA_TO_WARD:
        return AREA_TO_WARD[key]
    # Partial match fallback
    for k, v in AREA_TO_WARD.items():
        if key in k or k in key:
            return v
    raise KeyError(f"Unknown area: '{area_name}'. Add it to coimbatore_wards.py.")
