"""
Shared constants for GIIPS backend.
Single source of truth for aging thresholds and SLA limits.
"""

AGING_WARNING_DAYS = 4
AGING_CRITICAL_DAYS = 8

# SLA auto-escalation thresholds (in hours)
SLA_WARD_HOURS = 48          # Ward-level: escalate if no status change in 48 hours
SLA_ZONE_HOURS = 120         # Zonal-level: escalate further if no status change in 5 days (120h)
SLA_PRIORITY_BUMP = 15       # Points added to priority_score on each auto-escalation
