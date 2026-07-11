"""
Static mapping of complaint categories to Tamil Nadu government departments.
No AI — simple lookup table.
"""

DEPARTMENT_MAP: dict[str, str] = {
    "Roads": "Highways Department, Government of Tamil Nadu",
    "Water Supply": "TWAD Board (Tamil Nadu Water Supply and Drainage Board)",
    "Drainage": "TWAD Board (Tamil Nadu Water Supply and Drainage Board)",
    "Streetlights": "Municipal Electrical Department",
    "Garbage": "Solid Waste Management Department, Directorate of Municipal Administration",
    "Public Health": "Directorate of Public Health and Preventive Medicine",
    "Electricity": "TANGEDCO (Tamil Nadu Generation and Distribution Corporation)",
}

DEFAULT_DEPARTMENT = "Municipal Administration Department"


def get_department(category: str | None) -> str:
    """Return the TN government department responsible for a complaint category."""
    if category and category in DEPARTMENT_MAP:
        return DEPARTMENT_MAP[category]
    return DEFAULT_DEPARTMENT
