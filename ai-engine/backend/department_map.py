"""
Comprehensive mapping of complaint categories to Tamil Nadu government departments.
Includes all 43 Secretariat departments per the official Government of Tamil Nadu list.
Supports i18n slugs, old→new migration, and backward-compatible display names.
"""

from typing import Optional

# ── Category → Department Slug ──────────────────────────────────────────────
# Maps complaint categories (used by the ML classifier and seed data) to the
# correct department slug from the 43 official Secretariat departments.
CATEGORY_DEPT_MAP: dict[str, str] = {
    # Original categories (kept for backward compat with existing complaints/ML model)
    "Roads": "highways_minor_ports",
    "Road Infrastructure": "highways_minor_ports",
    "Water Supply": "municipal_admin_water_supply",
    "Drainage": "municipal_admin_water_supply",
    "Streetlights": "energy",
    "Street Lighting": "energy",
    "Garbage": "municipal_admin_water_supply",
    "Waste Management": "municipal_admin_water_supply",
    "Public Health": "health_family_welfare",
    "Electricity": "energy",
    # New categories
    "Sewage": "municipal_admin_water_supply",
    "Pollution": "environment_forests",
    "Traffic": "home_prohibition_excise",
    "Animal Nuisance": "animal_husbandry_dairying_fisheries",
    "Fire Safety": "home_prohibition_excise",
    "Building Violation": "housing_urban_development",
    "Encroachment": "revenue_disaster_management",
    "Parks and Gardens": "tourism_culture_religious",
    "Sanitation": "municipal_admin_water_supply",
    "Street Vendor": "municipal_admin_water_supply",
    "Water Logging": "water_resources",
    "Road Safety": "transport",
    "Public Transport": "transport",
}

DEFAULT_DEPT_SLUG = "municipal_admin_water_supply"

# ── All 43 Official Secretariat Department Slugs ─────────────────────────────
DEPARTMENT_SLUGS: list[str] = [
    "agriculture",
    "animal_husbandry_dairying_fisheries",
    "it_digital_services",
    "backward_classes_minorities_welfare",
    "commercial_taxes_registration",
    "cooperation_food_consumer_protection",
    "energy",
    "environment_forests",
    "finance",
    "handlooms_handicrafts_textiles_khadi",
    "health_family_welfare",
    "higher_education",
    "highways_minor_ports",
    "home_prohibition_excise",
    "housing_urban_development",
    "human_resources_management",
    "industries",
    "labour_employment",
    "law",
    "legislative_assembly",
    "msme",
    "miscellaneous_officers_secretariat",
    "mudalvarin_mugavari",
    "municipal_admin_water_supply",
    "natural_resources",
    "other_states_government",
    "planning_development_special_initiatives",
    "public",
    "public_elections",
    "public_works",
    "revenue_disaster_management",
    "rural_development_panchayat_raj",
    "school_education",
    "social_justice",
    "social_reforms",
    "social_welfare_women_empowerment",
    "special_programme_implementation",
    "tamil_development_information",
    "tourism_culture_religious",
    "transport",
    "water_resources",
    "welfare_differently_abled",
    "youth_welfare_sports",
]

# ── Slug → English Display Name (used in API responses and DB) ──────────────
SLUG_TO_DISPLAY: dict[str, str] = {
    "agriculture": "Agriculture Department",
    "animal_husbandry_dairying_fisheries": "Animal Husbandry, Dairying and Fisheries Department",
    "it_digital_services": "Information Technology and Digital Services Department",
    "backward_classes_minorities_welfare": "Backward Classes, Most Backward Classes and Minorities Welfare Department",
    "commercial_taxes_registration": "Commercial Taxes and Registration Department",
    "cooperation_food_consumer_protection": "Co-operation, Food and Consumer Protection Department",
    "energy": "Energy Department",
    "environment_forests": "Environment and Forests Department",
    "finance": "Finance Department",
    "handlooms_handicrafts_textiles_khadi": "Handlooms, Handicrafts, Textiles and Khadi Department",
    "health_family_welfare": "Health and Family Welfare Department",
    "higher_education": "Higher Education Department",
    "highways_minor_ports": "Highways and Minor Ports Department",
    "home_prohibition_excise": "Home, Prohibition and Excise Department",
    "housing_urban_development": "Housing and Urban Development Department",
    "human_resources_management": "Human Resources Management Department",
    "industries": "Industries Department",
    "labour_employment": "Labour and Employment Department",
    "law": "Law Department",
    "legislative_assembly": "Legislative Assembly Department",
    "msme": "Micro, Small and Medium Enterprises Department",
    "miscellaneous_officers_secretariat": "Miscellaneous Officers, Secretariat Department",
    "mudalvarin_mugavari": "Mudalvarin Mugavari Department",
    "municipal_admin_water_supply": "Municipal Administration and Water Supply Department",
    "natural_resources": "Natural Resources Department",
    "other_states_government": "Other States Government Department",
    "planning_development_special_initiatives": "Planning, Development and Special Initiatives Department",
    "public": "Public Department",
    "public_elections": "Public (Elections) Department",
    "public_works": "Public Works Department",
    "revenue_disaster_management": "Revenue and Disaster Management Department",
    "rural_development_panchayat_raj": "Rural Development and Panchayat Raj Department",
    "school_education": "School Education Department",
    "social_justice": "Social Justice Department",
    "social_reforms": "Social Reforms Department",
    "social_welfare_women_empowerment": "Social Welfare and Women Empowerment Department",
    "special_programme_implementation": "Special Programme Implementation Department",
    "tamil_development_information": "Tamil Development and Information Department",
    "tourism_culture_religious": "Tourism, Culture and Religious Endowments Department",
    "transport": "Transport Department",
    "water_resources": "Water Resources Department",
    "welfare_differently_abled": "Welfare of Differently Abled Persons Department",
    "youth_welfare_sports": "Youth Welfare and Sports Development Department",
}

# ── Reverse lookup: Display Name → Slug ──────────────────────────────────────
DISPLAY_TO_SLUG: dict[str, str] = {v: k for k, v in SLUG_TO_DISPLAY.items()}

# ── Old → New department name migration ──────────────────────────────────────
# Maps the previous department names to the new standardised names
# so existing officers / DepartmentMetrics / notifications are not orphaned.
OLD_TO_NEW_DEPT: dict[str, str] = {
    "Highways Department, Government of Tamil Nadu":
        "Highways and Minor Ports Department",
    "Highways Department":
        "Highways and Minor Ports Department",
    "TWAD Board (Tamil Nadu Water Supply and Drainage Board)":
        "Municipal Administration and Water Supply Department",
    "TWAD Board":
        "Municipal Administration and Water Supply Department",
    "Municipal Electrical Department":
        "Energy Department",
    "Solid Waste Management Department, Directorate of Municipal Administration":
        "Municipal Administration and Water Supply Department",
    "Solid Waste Management Department":
        "Municipal Administration and Water Supply Department",
    "Directorate of Public Health and Preventive Medicine":
        "Health and Family Welfare Department",
    "TANGEDCO (Tamil Nadu Generation and Distribution Corporation)":
        "Energy Department",
    "TANGEDCO":
        "Energy Department",
    "Municipal Administration Department":
        "Municipal Administration and Water Supply Department",
    "Chennai Metropolitan Water Supply and Sewerage Board (CMWSSB)":
        "Municipal Administration and Water Supply Department",
    "Tamil Nadu Pollution Control Board (TNPCB)":
        "Environment and Forests Department",
    "Traffic Police Department":
        "Home, Prohibition and Excise Department",
    "Animal Husbandry Department":
        "Animal Husbandry, Dairying and Fisheries Department",
    "Tamil Nadu Fire and Rescue Services":
        "Home, Prohibition and Excise Department",
    "Chennai Metropolitan Development Authority (CMDA)":
        "Housing and Urban Development Department",
    "Revenue Department":
        "Revenue and Disaster Management Department",
    "Municipal Parks and Recreation Department":
        "Tourism, Culture and Religious Endowments Department",
    "Town and Country Planning Department":
        "Housing and Urban Development Department",
    "Public Works Department (PWD)":
        "Public Works Department",
    "Tamil Nadu Housing Board":
        "Housing and Urban Development Department",
}


# ── Helper Functions ─────────────────────────────────────────────────────────

def get_department_slug(category: Optional[str]) -> str:
    """Return the department slug for a complaint category."""
    if category and category in CATEGORY_DEPT_MAP:
        return CATEGORY_DEPT_MAP[category]
    return DEFAULT_DEPT_SLUG


def get_department(category: Optional[str]) -> str:
    """Return the English display name of the department for a category.
    This is the backward-compatible function used throughout the backend."""
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
    """Map old department names to new standardised names.
    Returns the new name, or the default if old_dept is None/empty."""
    if old_dept and old_dept in OLD_TO_NEW_DEPT:
        return OLD_TO_NEW_DEPT[old_dept]
    if old_dept and old_dept in SLUG_TO_DISPLAY.values():
        return old_dept
    return SLUG_TO_DISPLAY[DEFAULT_DEPT_SLUG]
