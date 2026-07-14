"""
Mapping of civic complaint categories to the REAL bodies responsible
for Coimbatore City Municipal Corporation (CCMC) jurisdiction.

Narrowed from the generic 43-department Tamil Nadu Secretariat list
to only those departments with actual Coimbatore-relevant authority
for public-service / civic infrastructure complaints.
"""

from typing import Optional

# ── Category → Coimbatore-specific Department Slug ───────────────────────────
# Only civic/public-service categories.  Each maps to the real operational
# body that handles that service in Coimbatore.
CATEGORY_DEPT_MAP: dict[str, str] = {
    "Roads":                "ccmc_engineering",
    "Water Supply":         "twad_coimbatore",
    "Waste Management":     "ccmc_health",
    "Sanitation":           "ccmc_engineering",
    "Street Lighting":      "tangedco_coimbatore",
    "Electricity":          "tangedco_coimbatore",
    "Public Health":        "ccmc_health",
}

DEFAULT_DEPT_SLUG = "ccmc_engineering"

# ── Coimbatore-relevant Department Slugs ─────────────────────────────────────
DEPARTMENT_SLUGS: list[str] = [
    "ccmc_engineering",          # CCMC Engineering Wing — roads, drainage, sanitation infrastructure
    "ccmc_health",               # CCMC Health Department — waste management, public health, sanitation
    "ccmc_planning",             # CCMC Town Planning — building violations, encroachments
    "ccmc_parks",                # CCMC Parks & Recreation
    "twad_coimbatore",           # TWAD Board — Coimbatore Division (water supply, sewage)
    "tangedco_coimbatore",       # TANGEDCO — Coimbatore Region (electricity, street lighting)
    "tnpcb_coimbatore",          # TN Pollution Control Board — Coimbatore
    "coimbatore_traffic_police", # Coimbatore City Traffic Police
    "coimbatore_fire",           # Tamil Nadu Fire & Rescue Services — Coimbatore
    "coimbatore_district_admin", # Coimbatore District Administration
]

# ── Slug → English Display Name ──────────────────────────────────────────────
SLUG_TO_DISPLAY: dict[str, str] = {
    "ccmc_engineering":          "CCMC Engineering Wing",
    "ccmc_health":               "CCMC Health Department",
    "ccmc_planning":             "CCMC Town Planning Department",
    "ccmc_parks":                "CCMC Parks and Recreation",
    "twad_coimbatore":           "TWAD Board - Coimbatore Division",
    "tangedco_coimbatore":       "TANGEDCO - Coimbatore Region",
    "tnpcb_coimbatore":          "Tamil Nadu Pollution Control Board - Coimbatore",
    "coimbatore_traffic_police": "Coimbatore City Traffic Police",
    "coimbatore_fire":           "Tamil Nadu Fire and Rescue Services - Coimbatore",
    "coimbatore_district_admin": "Coimbatore District Administration",
}

# ── Reverse lookup ───────────────────────────────────────────────────────────
DISPLAY_TO_SLUG: dict[str, str] = {v: k for k, v in SLUG_TO_DISPLAY.items()}

# ── Old → New department name migration (Coimbatore-specific) ───────────────
OLD_TO_NEW_DEPT: dict[str, str] = {
    "Highways Department, Government of Tamil Nadu":
        "CCMC Engineering Wing",
    "Highways Department":
        "CCMC Engineering Wing",
    "TWAD Board (Tamil Nadu Water Supply and Drainage Board)":
        "TWAD Board - Coimbatore Division",
    "TWAD Board":
        "TWAD Board - Coimbatore Division",
    "Municipal Electrical Department":
        "TANGEDCO - Coimbatore Region",
    "Solid Waste Management Department, Directorate of Municipal Administration":
        "CCMC Health Department",
    "Solid Waste Management Department":
        "CCMC Health Department",
    "Directorate of Public Health and Preventive Medicine":
        "CCMC Health Department",
    "TANGEDCO (Tamil Nadu Generation and Distribution Corporation)":
        "TANGEDCO - Coimbatore Region",
    "TANGEDCO":
        "TANGEDCO - Coimbatore Region",
    "Municipal Administration Department":
        "CCMC Engineering Wing",
    "Chennai Metropolitan Water Supply and Sewerage Board (CMWSSB)":
        "TWAD Board - Coimbatore Division",
    "Tamil Nadu Pollution Control Board (TNPCB)":
        "Tamil Nadu Pollution Control Board - Coimbatore",
    "Traffic Police Department":
        "Coimbatore City Traffic Police",
    "Tamil Nadu Fire and Rescue Services":
        "Tamil Nadu Fire and Rescue Services - Coimbatore",
    "Public Works Department (PWD)":
        "CCMC Engineering Wing",
}


# ── Helper Functions ─────────────────────────────────────────────────────────

def get_department_slug(category: Optional[str]) -> str:
    """Return the department slug for a complaint category."""
    if category and category in CATEGORY_DEPT_MAP:
        return CATEGORY_DEPT_MAP[category]
    return DEFAULT_DEPT_SLUG


def get_department(category: Optional[str]) -> str:
    """Return the English display name of the department for a category."""
    slug = get_department_slug(category)
    return SLUG_TO_DISPLAY.get(slug, SLUG_TO_DISPLAY[DEFAULT_DEPT_SLUG])


def get_slug_for_department(display_name: Optional[str]) -> str:
    """Return the slug corresponding to a department display name."""
    if display_name and display_name in DISPLAY_TO_SLUG:
        return DISPLAY_TO_SLUG[display_name]
    for old, new in OLD_TO_NEW_DEPT.items():
        if display_name == old:
            return DISPLAY_TO_SLUG.get(new, DEFAULT_DEPT_SLUG)
    return DEFAULT_DEPT_SLUG


def get_i18n_key(slug: str) -> str:
    """Return the i18n translation key for a department slug."""
    return f"departments.{slug}"


def migrate_old_department(old_dept: Optional[str]) -> str:
    """Map old department names to new standardised Coimbatore names."""
    if old_dept and old_dept in OLD_TO_NEW_DEPT:
        return OLD_TO_NEW_DEPT[old_dept]
    if old_dept and old_dept in SLUG_TO_DISPLAY.values():
        return old_dept
    return SLUG_TO_DISPLAY[DEFAULT_DEPT_SLUG]
