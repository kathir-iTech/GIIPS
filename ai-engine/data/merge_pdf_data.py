from pypdf import PdfReader
import json, re, os

base = r'C:\Users\jeeva\Desktop\GIIPS-opencode'
json_path = os.path.join(base, r'ai-engine\data\ccmc_officer_directory.json')

with open(json_path, 'r', encoding='utf-8-sig') as f:
    data = json.load(f)

# ── 1. PARSE COUNCILOR PDF ──
pdf_path = os.path.join(base, r'c_1\ccmc.gov.in\img\upload\MCs_List_Offical_Mobile_Number_1.4_.2022_.pdf')
r = PdfReader(pdf_path)
full_text = ''
for page in r.pages:
    full_text += page.extract_text() + '\n'

# Strategy: find lines with 'வ ' prefix (zone pages) = zone-wise councilors
# Or use regex to match patterns like: serial_number ward_number . name . phone
# The cleaner zone-wise pages (7-11) have: serial ward name phone

councilors = []
# Try matching on zone-wise pages: serial_number (1-2 digits) ward_number (1-3 digits) followed by name and phone
# Pattern: after page break, lines like "1 10 name phone"
lines = full_text.split('\n')
current_zone = ''

for line in lines:
    line = line.strip()
    if not line:
        continue
    
    # Detect zone zone_name in Tamil (from pages 7-11 headers)
    if 'வடக்ஶ' in line or 'வடக்கு' in line:
        current_zone = 'NORTH'
    elif 'ழழக்ஶ' in line or 'தெற்கு' in line or 'ெதற்ஶ வார்' in line:
        current_zone = 'SOUTH'
    elif 'ேமற்ஶ' in line or 'மேற்கு' in line:
        current_zone = 'WEST'
    elif 'மத்ொயம' in line or 'மத்திய' in line:
        current_zone = 'CENTRAL'
    elif 'கணக்ஶகள' in line or 'கணக்கு' in line:
        current_zone = 'EAST'
    elif 'கல' in line:
        current_zone = 'EAST'
    
    # Try to extract: serial ward phone
    # Find all 10-digit phones
    phones = re.findall(r'(\d{10})', line)
    if not phones:
        continue
    
    # Try to find ward number and serial number at start of line
    # Pattern: "N M" at start where N is serial (1-2 digits) and M is ward number
    m = re.match(r'(\d{1,2})\s+(\d{1,3})\s', line)
    if m:
        serial = int(m.group(1))
        ward = int(m.group(2))
        if 1 <= ward <= 100:
            # Extract name between ward number and phone
            rest = line[m.end():]
            phone = phones[0]
            # Name is everything before phone minus trailing garbage
            name_raw = rest.rsplit(str(phone), 1)[0].strip().rstrip('.')
            # Clean up
            name_raw = re.sub(r'[?\s\.]+', ' ', name_raw).strip()
            if name_raw and len(name_raw) > 2:
                councilors.append({
                    'ward_number': ward,
                    'councilor_name': name_raw,
                    'phone': phone,
                    'zone': current_zone
                })

# Also parse pages 1-5 (ward-wise with different format)
# On these pages, the serial and ward are separated differently
current_zone_p1 = ''
for line in lines:
    line = line.strip()
    if not line:
        continue
    
    phones = re.findall(r'(\d{10})', line)
    if not phones:
        continue
    
    # Pattern on page 1: "1 வ 10 ொ? . name . phone"
    # More general: starts with digit, has Tamil character, then ward number
    m = re.match(r'(\d{1,2})\s+[^\d]+\s+(\d{1,3})\s', line)
    if not m:
        # Try without Tamil char: "N  M"
        m = re.match(r'(\d{1,2})\s+(\d{1,3})\s', line)
    if m:
        serial = int(m.group(1))
        ward = int(m.group(2))
        if 1 <= ward <= 100:
            rest = line[m.end():]
            phone = phones[0]
            name_raw = rest.rsplit(str(phone), 1)[0].strip().rstrip('.')
            name_raw = re.sub(r'[?\s\.]+', ' ', name_raw).strip()
            # Check if this ward already found
            existing = [c for c in councilors if c['ward_number'] == ward]
            if name_raw and len(name_raw) > 2 and not existing:
                councilors.append({
                    'ward_number': ward,
                    'councilor_name': name_raw,
                    'phone': phone,
                    'zone': current_zone
                })

# Deduplicate by ward
seen_wards = set()
unique_councilors = []
for c in councilors:
    if c['ward_number'] not in seen_wards:
        seen_wards.add(c['ward_number'])
        unique_councilors.append(c)

councilors = unique_councilors
print(f'Parsed {len(councilors)} councilors from PDF')

# ── 2. PARSE PROPERTY TAX DEFAULTERS PDF ──
pdf2_path = os.path.join(base, r'c_1\ccmc.gov.in\img\upload\Property_Tax_-_Top_Defualters_List1.pdf')
r2 = PdfReader(pdf2_path)
text2 = ''
for page in r2.pages:
    text2 += page.extract_text() + '\n'

defaulters = []
# Pattern: serial WARD-XXX assessment owner-name phone address zone amounts
# Each entry starts with "N WARD-XXX" pattern
parts = re.split(r'(?=\d+\s+WARD-\d+)', text2)
for part in parts:
    if 'WARD-' not in part:
        continue
    lines_p = part.strip().split('\n')
    first = lines_p[0] if lines_p else ''
    
    m = re.match(r'(\d+)\s+WARD-(\d+)', first)
    if not m:
        continue
    
    serial = int(m.group(1))
    ward = int(m.group(2))
    
    # Extract phone numbers
    phones = re.findall(r'(\d{10})', part)
    
    # Extract zone
    zone_m = re.search(r'(NORTH|SOUTH|EAST|WEST|CENTRAL)\s+ZONE', part)
    zone = zone_m.group(1) if zone_m else ''
    
    # Extract owner name: between assessment number and "   " (double space then phone)
    full_text_clean = part.replace('\n', ' ')
    # Remove assessment number pattern
    full_text_clean = re.sub(r'\d+/\d+/[\d/-]+', '', full_text_clean)
    
    owner_name = ''
    # Try to get owner name - it's before first phone number
    if phones:
        idx = full_text_clean.find(phones[0])
        if idx > 0:
            before = full_text_clean[:idx].strip()
            # Remove serial and WARD prefix
            before = re.sub(r'^\d+\s+WARD-\d+\s*', '', before)
            # Remove zone at end
            before = re.sub(r'(NORTH|SOUTH|EAST|WEST|CENTRAL)\s+ZONE.*$', '', before)
            owner_name = before.strip().rstrip(',').strip()
    
    # Get address - after owner name, before zone
    address = ''
    if zone:
        addr_m = re.search(r'(NORTH|SOUTH|EAST|WEST|CENTRAL)\s+ZONE\s*\d*\s*(.*?)(?:\d+\s+\d+|$)', part)
        if addr_m:
            address = addr_m.group(2).strip()[:200]
    
    if phones:
        defaulters.append({
            'ward_number': ward,
            'owner_name': owner_name[:100] if owner_name else '',
            'phone': phones[0],
            'zone': zone,
            'address': address,
            'source': 'property_tax_defaulter_list_2025-26'
        })

print(f'Parsed {len(defaulters)} property tax defaulters from PDF')

# ── 3. MERGE INTO JSON ──

# Add councilors section
councilor_list = []
for c in councilors:
    councilor_list.append({
        'ward_number': c['ward_number'],
        'councilor_name': c['councilor_name'],
        'phone': c['phone'],
        'role': 'Ward Councilor',
        'source': 'MCs_List_Offical_Mobile_Number_1.4_.2022_.pdf'
    })

data['councilors'] = councilor_list

# Add property defaulters section
data['property_tax_defaulters'] = defaulters

# Update meta
data['meta']['extraction_date'] = '2026-07-15'
data['meta']['description'] = 'Structured grievance routing directory extracted from CCMC mirrored website and PDF documents'
data['meta']['sites_used'] = list(set(data['meta']['sites_used'] + [
    'c_1/ccmc.gov.in/img/upload/MCs_List_Offical_Mobile_Number_1.4_.2022_.pdf',
    'c_1/ccmc.gov.in/img/upload/Property_Tax_-_Top_Defualters_List1.pdf'
]))

# Write back
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print(f'\n✅ Merged successfully!')
print(f'   RTI Officers: {len(data["officer_directory"])}')
print(f'   Zonal Officers: {len(data["zonal_officers"])}')
print(f'   Ward Contacts: {len(data["ward_contacts"])}')
print(f'   Councilors (NEW): {len(data["councilors"])}')
print(f'   Property Defaulters (NEW): {len(data["property_tax_defaulters"])}')
print(f'   Payment Centers: {len(data["payment_collection_centers"])}')
