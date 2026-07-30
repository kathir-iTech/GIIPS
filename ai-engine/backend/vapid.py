import os
import base64

VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_CLAIM_EMAIL = os.environ.get("VAPID_CLAIM_EMAIL", "push@giips.gov.in")

def get_vapid_keys():
    return {
        "public_key": VAPID_PUBLIC_KEY,
        "private_key": VAPID_PRIVATE_KEY,
        "claim_email": VAPID_CLAIM_EMAIL,
    }
