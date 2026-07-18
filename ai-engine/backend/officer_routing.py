"""
CCMC Officer Routing for Coimbatore.

Replaces the earlier Bangalore BBMP officer_routing.py (which called a
nonexistent get_officer_role() in department_map and broke both
GET /complaints/{id} and GET /complaints/my).

Loads the real CCMC officer directory (ai-engine/data/ccmc_officer_directory.json)
and maps complaint category + ward number to the specific officer responsible.

Data sources (all from the CCMC directory):
  - ward_contacts: 100 entries, one per ward, with AE/JE, WS AE/JE,
    Sanitary Inspector, and Bill Collector names + phones
  - zonal_officers: 36 zone-level officers (Assistant Commissioner, etc.)
  - officer_directory: 21 department-level officers (City Engineer, etc.)
  - councilors: 100 ward councillors
"""

import json
import logging
from pathlib import Path
from typing import Optional

from department_map import get_department, CATEGORY_DEPT_MAP

logger = logging.getLogger(__name__)

_JSON_PATH = Path(__file__).parent.parent / 'data' / 'ccmc_officer_directory.json'

_dir_cache = None

def _load_directory():
    global _dir_cache
    if _dir_cache is not None:
        return _dir_cache
    if not _JSON_PATH.exists():
        logger.warning("CCMC officer directory not found at %s", _JSON_PATH)
        _dir_cache = {}
        return _dir_cache
    try:
        with open(_JSON_PATH, 'r', encoding='utf-8') as f:
            _dir_cache = json.load(f)
        logger.info("Loaded CCMC officer directory (%d ward contacts, %d zonal officers, %d councilors)",
                     len(_dir_cache.get('ward_contacts', [])),
                     len(_dir_cache.get('zonal_officers', [])),
                     len(_dir_cache.get('councilors', [])))
    except Exception as e:
        logger.error("Failed to load CCMC officer directory: %s", e)
        _dir_cache = {}
    return _dir_cache


# ── Category → responsible role in ward_contacts ──────────────────────────

CATEGORY_ROLE_MAP = {
    "Roads":           "ae_je",          # CCMC Engineering — road maintenance
    "Sanitation":      "ae_je",          # CCMC Engineering — drainage, sanitation infrastructure
    "Water Supply":    "ws_ae_je",       # TWAD — water supply (Water Supply AE/JE)
    "Waste Management":"sanitary_inspector",  # CCMC Health — solid waste
    "Public Health":   "sanitary_inspector",  # CCMC Health — public health, fogging
    "Street Lighting": "ae_je",          # TANGEDCO — handled via CCMC engineering coordination
    "Electricity":     "ae_je",          # TANGEDCO — handled via CCMC engineering
}

CATEGORY_ROLE_LABEL = {
    "ae_je":              "Assistant Engineer / Junior Engineer",
    "ws_ae_je":           "Water Supply Assistant Engineer / Junior Engineer",
    "sanitary_inspector": "Sanitary Inspector",
    "bc":                 "Bill Collector",
}


def route_complaint(ward: str, category: str) -> dict:
    """Return the responsible officer for a complaint based on ward + category.

    Looks up the CCMC ward directory for the ward-specific contact, then
    enriches with department info.  Falls back to zone-level or department-level
    officers when no ward-specific match exists.
    """
    directory = _load_directory()
    ward_contacts = directory.get('ward_contacts', [])
    zonal_officers = directory.get('zonal_officers', [])
    officer_directory = directory.get('officer_directory', [])

    # Parse ward number (handles "27", "Ward 27", "Ward 27 (text)")
    ward_num = None
    try:
        cleaned = ward.strip().lower().replace('ward ', '')
        ward_num = int(cleaned)
    except (ValueError, AttributeError):
        pass

    # Get the zone from coimbatore_wards if possible
    zone = None
    if ward_num is not None:
        try:
            from coimbatore_wards import ZONE_BY_WARD
            zone = ZONE_BY_WARD.get(ward_num)
        except ImportError:
            pass

    # ── 1. Find ward-specific contact from ward_contacts ──────────────
    role_key = CATEGORY_ROLE_MAP.get(category, "ae_je")
    officer_name = None
    officer_phone = None
    officer_role = None

    for wc in ward_contacts:
        w_ward = wc.get('ward')
        if w_ward == ward_num:
            role_phone_key = role_key + '_phone'
            officer_name = wc.get(role_key)
            officer_phone = wc.get(role_phone_key)
            officer_role = CATEGORY_ROLE_LABEL.get(role_key, role_key)
            if zone is None:
                zone = wc.get('zone')
            break

    # ── 2. Fallback to zonal officer if no ward match ─────────────────
    if not officer_name and zone and zonal_officers:
        for zo in zonal_officers:
            if zo.get('zone', '').upper() == zone.upper() and 'Assistant Commissioner' in zo.get('designation', ''):
                officer_name = zo.get('name')
                officer_phone = zo.get('phone')
                officer_role = zo.get('designation')
                break
        if not officer_name:
            for zo in zonal_officers:
                if zo.get('zone', '').upper() == zone.upper():
                    officer_name = zo.get('name')
                    officer_phone = zo.get('phone')
                    officer_role = zo.get('designation')
                    break

    # ── 3. Fallback to department-level City Engineer/Health Officer ──
    if not officer_name:
        dept_slug = CATEGORY_DEPT_MAP.get(category, "ccmc_engineering")
        # Map department slug to CCMC department name
        ccmc_dept_map = {
            "ccmc_engineering":     "Engineering",
            "ccmc_health":          "Public Health",
            "twad_coimbatore":      "Engineering",
            "tangedco_coimbatore":  "Engineering",
        }
        target_dept = ccmc_dept_map.get(dept_slug, "Engineering")
        for o in officer_directory:
            if o.get('department') == target_dept:
                officer_name = o.get('officer_name')
                officer_phone = o.get('phone')
                officer_role = o.get('designation')
                zone = None
                break

    return {
        "name": officer_name or "Not assigned",
        "phone": officer_phone or "",
        "designation": officer_role or "Duty Officer",
        "department": get_department(category),
        "category": category,
        "ward": str(ward_num) if ward_num else ward,
        "zone": zone or "",
    }
