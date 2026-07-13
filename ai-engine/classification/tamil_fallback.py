"""
Phase 1.5 TEMPORARY: Tamil keyword fallback layer for pure-Tamil-script complaints.

This is a lightweight rule-based safety net for when the TF-IDF + Logistic
Regression model has zero vocabulary overlap with Tamil Unicode text.
To be replaced by a proper multilingual model (IndicBERT/LaBSE) in Phase 3
with real Tamil complaint data.
"""

import re
from typing import Dict, List, Tuple, Optional

TAMIL_KEYWORDS: Dict[str, List[str]] = {
    # ═══════════════════════════════════════════════════════════════════════
    # Road Infrastructure  —  சாலை உள்கட்டமைப்பு
    # ═══════════════════════════════════════════════════════════════════════
    'Road Infrastructure': [
        # Core terms (preserved from v1)
        'சாலை', 'குழி', 'பள்ளம்', 'நடைபாதை',
        'சாலை சீரமைப்பு', 'சாலை பழுது', 'தார் சாலை',
        'பாலம்', 'போக்குவரத்து', 'சாலை அமைப்பு',
        # Colloquial / Tanglish borrowings
        'ரோடு',
        # Road surfaces & types
        'சாலை மேற்பரப்பு', 'நெடுஞ்சாலை', 'மண் சாலை', 'கிராம சாலை',
        # Road features
        'சாலை ஓரம்', 'சாலை வளைவு', 'சாலை இறக்கம்', 'சாலை மேம்பாலம்',
        # Infrastructure damage & repair
        'நடைபாதை சீரமைப்பு', 'பாலம் பழுது', 'சாலை புனரமைப்பு',
        'சாலை தடை',
        # Broader terms
        'பாதை', 'சாலை சமிக்ஞை', 'சாலை அடையாளம்',
    ],
    # ═══════════════════════════════════════════════════════════════════════
    # Water Supply  —  நீர் விநியோகம்
    # ═══════════════════════════════════════════════════════════════════════
    'Water Supply': [
        # Core terms (preserved from v1)
        'தண்ணீர்', 'குடிநீர்', 'நீர்', 'குழாய்',
        'தண்ணீர் இணைப்பு', 'நீர் வினியோகம்', 'தண்ணீர் கசிவு',
        'தண்ணீர் பற்றாக்குறை', 'தண்ணீர் வரவில்லை', 'குடிநீர் குழாய்',
        # Colloquial / spoken forms
        'தண்ணி', 'தண்ணீர் கிடையாது',
        # Equipment & infrastructure
        'கிணறு', 'மோட்டார்', 'நீர் தொட்டி', 'பம்ப்', 'டேங்கர்',
        # Distribution & supply
        'நீர் விநியோகம்', 'தண்ணீர் விநியோகம்', 'குடிநீர் திட்டம்',
        # Quality & pressure
        'நீர் பிரஷர்', 'நீர் சுத்திகரிப்பு', 'தண்ணீர் அழுத்தம்',
        # Institutional
        'நீர் வாரியம்', 'குடிநீர் வாரியம்', 'தண்ணீர் கட்டணம்',
        # Storage & management
        'நீர் சேமிப்பு', 'நீர் மேலாண்மை',
    ],
    # ═══════════════════════════════════════════════════════════════════════
    # Waste Management  —  கழிவு மேலாண்மை
    # ═══════════════════════════════════════════════════════════════════════
    'Waste Management': [
        # Core terms (preserved from v1)
        'குப்பை', 'கழிவு', 'குப்பை தொட்டி', 'குப்பை சேகரிப்பு',
        'திடக்கழிவு', 'குப்பை மேலாண்மை', 'குப்பை அகற்றல்',
        'குப்பை கொட்டுதல்', 'மாசு', 'குப்பை எடுக்கவில்லை',
        # Waste types
        'பிளாஸ்டிக் கழிவு', 'உணவு கழிவு', 'கட்டுமான கழிவு',
        # Collection & transport
        'குப்பை வண்டி', 'குப்பை கிடங்கு', 'குப்பை கொள்கலன்',
        # Cleaning & disposal
        'தெரு குப்பை', 'குப்பை சுத்தம்', 'கழிவு நீக்கம்',
        'குப்பை முறையின்மை',
        # Recycling & environment
        'மறுசுழற்சி', 'சுற்றுச்சூழல்',
        # Specific complaint phrasings
        'குப்பை சேர்ந்துள்ளது', 'குப்பை அகலவில்லை', 'குப்பை மணம்',
    ],
    # ═══════════════════════════════════════════════════════════════════════
    # Sanitation  —  சுகாதாரம் (also covers Drainage)
    # ═══════════════════════════════════════════════════════════════════════
    'Sanitation': [
        # Core terms (preserved from v1)
        'சாக்கடை', 'சுகாதாரம்', 'வடிகால்', 'கழிப்பறை',
        'தூய்மை', 'அசுத்தம்', 'சாக்கடை நீர்',
        'வடிகால் அமைப்பு', 'சாக்கடை அடைப்பு', 'கழிவு நீர்',
        # Drainage infrastructure
        'சாக்கடை வாய்', 'சாக்கடை மூடி', 'வடிகால் கால்வாய்',
        'திறந்த சாக்கடை', 'சாக்கடை அமைப்பு',
        # Repair & maintenance
        'வடிகால் சீரமைப்பு', 'சாக்கடை சுத்தம்', 'வடிகால் தூய்மை',
        # Specific nuisances
        'சாக்கடை நாற்றம்', 'சாக்கடை தண்ணீர் தேக்கம்',
        'கழிவு நீர் வெளியேற்றம்',
        # Toilet / restroom
        'கழிப்பிடம்', 'கழிவறை',
        # Broader sanitation
        'சாக்கடை மேலாண்மை', 'தூய்மை பணி',
    ],
    # ═══════════════════════════════════════════════════════════════════════
    # Street Lighting  —  தெரு விளக்கு
    # ═══════════════════════════════════════════════════════════════════════
    'Street Lighting': [
        # Core terms (preserved from v1)
        'விளக்கு', 'தெரு விளக்கு', 'மின் விளக்கு', 'மின்சாரம்',
        'விளக்கு எரியவில்லை', 'தெரு விளக்கு பழுது', 'விளக்கு கம்பம்',
        'இருள்', 'மின் கம்பம்', 'விளக்கு பல்பு',
        # Colloquial / Tanglish
        'லைட்', 'இருட்டு',
        # Specific faults
        'தெரு விளக்கு எரியவில்லை', 'விளக்கு உடைந்தது',
        'விளக்கு கம்பம் சாய்ந்தது', 'விளக்கு பழுது',
        # Types of lights
        'எல்இடி விளக்கு', 'சோலார் விளக்கு', 'மின்சார விளக்கு',
        # Maintenance & installation
        'தெரு விளக்கு சீரமைப்பு', 'விளக்கு மாற்றுதல்',
        'விளக்கு பராமரிப்பு', 'தெரு விளக்கு அமைப்பு',
        # General
        'விளக்கு இல்லை', 'விளக்கு கம்பி',
    ],
    # ═══════════════════════════════════════════════════════════════════════
    # Electricity  —  மின்சாரம்  (NEW)
    # ═══════════════════════════════════════════════════════════════════════
    'Electricity': [
        'மின்சாரம்', 'மின்',
        # Supply & connection
        'மின் இணைப்பு', 'மின் இணைப்பு கோரிக்கை', 'மின் விநியோகம்',
        # Interruptions & faults
        'மின்சாரம் இல்லை', 'மின்சாரம் வரவில்லை', 'மின் தடை',
        'மின்சார பற்றாக்குறை', 'மின் கோளாறு', 'மின் பழுது',
        # Infrastructure
        'மின் கம்பம்', 'மின் கம்பி', 'மின்மாற்றி',
        # Billing & metering
        'மின் கட்டணம்', 'மின் மீட்டர்', 'மின் அளவி',
        # Institutional
        'மின் வாரியம்', 'மின்சார வாரியம்',
        # Repairs
        'மின் சீரமைப்பு', 'மின்சார கசிவு', 'மின்சார மோட்டார்',
    ],
    # ═══════════════════════════════════════════════════════════════════════
    # Public Health  —  பொது சுகாதாரம்  (NEW)
    # ═══════════════════════════════════════════════════════════════════════
    'Public Health': [
        # Core health & hygiene
        'சுகாதாரம்', 'பொது சுகாதாரம்',
        # Disease & infection
        'நோய்', 'தொற்று', 'தொற்று நோய்', 'நோய் பரவல்',
        'கிருமி', 'நோய் பாதிப்பு',
        # Mosquito-related
        'கொசு', 'கொசுத்தொல்லை', 'கொசு ஒழிப்பு', 'கொசு மருந்து',
        # Animal nuisance
        'நாய்', 'தெரு நாய்', 'நாய் கடி', 'வெறிநாய்',
        'எலி', 'எலி தொல்லை', 'ஈ', 'ஈ தொல்லை',
        # Environmental health
        'சுகாதாரமற்ற', 'சுகாதார பிரச்சினை',
        # Health services
        'சுகாதார அலுவலர்', 'சுகாதார பரிசோதனை',
        # Water & food safety
        'உணவு பாதுகாப்பு', 'குடிநீர் தூய்மை',
    ],
}

RE_TAMIL = re.compile(r'[\u0B80-\u0BFF]')


def is_tamil_text(text: str, threshold: float = 0.2) -> bool:
    tamil_chars = RE_TAMIL.findall(text)
    if not tamil_chars:
        return False
    total_alpha = sum(1 for c in text if c.isalpha())
    return tamil_chars and (len(tamil_chars) / max(total_alpha, 1) >= threshold)


def tamil_keyword_classify(text: str) -> Tuple[Optional[str], List[str], float]:
    scores: Dict[str, int] = {}
    matched_terms: Dict[str, List[str]] = {}
    for category, keywords in TAMIL_KEYWORDS.items():
        hits = [kw for kw in keywords if kw in text]
        if hits:
            scores[category] = len(hits)
            matched_terms[category] = hits
    if not scores:
        return None, [], 0.0
    best_category = max(scores, key=scores.get)
    confidence = min(0.4 + (scores[best_category] * 0.03), 0.55)
    return best_category, matched_terms[best_category], round(confidence, 3)
