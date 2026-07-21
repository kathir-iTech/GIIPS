from pypdf import PdfReader
import json, re, os

base = r'C:\Users\jeeva\Desktop\GIIPS-opencode'
json_path = os.path.join(base, r'ai-engine\data\ccmc_officer_directory.json')
pdf2_path = os.path.join(base, r'c_1\ccmc.gov.in\img\upload\Property_Tax_-_Top_Defualters_List1.pdf')

r2 = PdfReader(pdf2_path)
text2 = ''
for page in r2.pages:
    text2 += page.extract_text() + '\n'

lines = text2.split('\n')

defaulters = []
i = 0
while i < len(lines):
    line = lines[i].strip()
    i += 1
    
    # Start of entry: "N WARD-..."
    m = re.match(r'(\d+)\s+WARD-(\d{3})', line)
    if not m:
        continue
    
    ward_str = m.group(2)  # e.g., "048"
    ward = int(ward_str)   # e.g., 48
    
    # Collect lines until we see the zone line or next entry
    entry_lines = [line]
    while i < len(lines):
        next_line = lines[i].strip()
        if not next_line:
            i += 1
            continue
        if re.match(r'\d+\s+WARD-\d{3}', next_line):
            break
        # Check if we've gone too far (next page header)
        entry_lines.append(next_line)
        i += 1
    
    # Find phone number - it's a 10-digit number
    all_text = ' '.join(entry_lines)
    phones = re.findall(r'(\d{10})', all_text)
    
    # Find zone
    zone_m = re.search(r'(NORTH|SOUTH|EAST|WEST|CENTRAL)\s+ZONE', all_text)
    zone = zone_m.group(1) if zone_m else 'UNKNOWN'
    
    if phones:
        # Get owner name: after the WARD- line, before the phone line
        # Find which line has the phone number
        phone_line_idx = -1
        for idx, el in enumerate(entry_lines):
            if phones[0] in el.replace(' ', ''):
                phone_line_idx = idx
                break
        
        # Owner name is between entry start and phone line
        owner_parts = []
        for j in range(1, phone_line_idx if phone_line_idx > 0 else len(entry_lines)-1):
            el_text = entry_lines[j]
            # Skip assessment continuation (just numbers and /)
            if re.match(r'^[\d/\-\s]+$', el_text) and len(el_text) < 30:
                continue
            # Skip zone line
            if 'ZONE' in el_text:
                continue
            owner_parts.append(el_text)
        
        owner_name = ' '.join(owner_parts).strip()
        owner_name = re.sub(r'\s+', ' ', owner_name).strip().rstrip(',').strip()
        
        # Get address from the phone line
        phone_line = entry_lines[phone_line_idx] if phone_line_idx > 0 else ''
        address = phone_line.replace(phones[0], '', 1).strip()
        address = re.sub(r'^\d+', '', address).strip().lstrip('-').strip()
        
        defaulters.append({
            'ward_number': ward,
            'owner_name': owner_name[:150],
            'phone': phones[0],
            'zone': zone,
            'address': address[:200],
            'source': 'property_tax_defaulter_list_2025-26'
        })

# Read existing JSON
with open(json_path, 'r', encoding='utf-8-sig') as f:
    data = json.load(f)

# Replace defaulters
data['property_tax_defaulters'] = defaulters

with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print(f'Fixed: {len(defaulters)} defaulters parsed with correct ward numbers')

# Verify some
for d in defaulters[:5]:
    print(f'  Ward {d["ward_number"]:3d} ({d["zone"]}): {d["owner_name"][:40]:40s} -> {d["phone"]}')
