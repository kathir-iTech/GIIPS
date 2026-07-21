from pypdf import PdfReader
import re, json, os

base = r'C:\Users\jeeva\Desktop\GIIPS-opencode'
json_path = os.path.join(base, r'ai-engine\data\ccmc_officer_directory.json')

taluk_files = {
    3: 'Madukkarai', 4: 'Perur', 5: 'Sulur', 6: 'Coimbatore North',
    7: 'Mettupalayam', 8: 'Annur', 9: 'Pollachi', 10: 'Kinathukadavu',
    12: 'Valparai', 13: 'Anaimalai'
}

taluk_rdo = {
    'Madukkarai': 'Coimbatore', 'Perur': 'Coimbatore', 'Sulur': 'Coimbatore',
    'Coimbatore North': 'Coimbatore North', 'Mettupalayam': 'Coimbatore North',
    'Annur': 'Coimbatore North',
    'Pollachi': 'Pollachi', 'Kinathukadavu': 'Pollachi', 'Valparai': 'Pollachi',
    'Anaimalai': 'Pollachi'
}

all_villages = {}

for fid, tname in sorted(taluk_files.items()):
    path = os.path.join(base, f'c__{fid}.pdf')
    p = PdfReader(path)
    text = ''
    for page in p.pages:
        text += page.extract_text() + '\n'
    
    lines = text.strip().split('\n')
    taluk = tname
    for line in lines:
        if 'TALUK' in line.upper() and 'NAME' not in line.upper():
            taluk = line.strip().replace('TALUK', '').replace('Taluk', '').strip()
            break
    
    rdo = taluk_rdo.get(taluk, 'Coimbatore')
    
    villages = set()
    firka_villages = {}
    
    for line in lines:
        line = line.strip()
        if not line or re.match(r'^S\.?No', line) or 'District' in line or 'Village' in line:
            continue
        
        m = re.match(r'(\d+)\s+(.*)', line)
        if not m:
            continue
        
        rest = m.group(2).strip()
        
        if rest.startswith(rdo):
            rest = rest[len(rdo):].strip()
        
        if rest.upper().startswith(taluk.upper()):
            rest = rest[len(taluk):].strip()
        
        words = rest.split()
        if len(words) < 2:
            continue
        
        # Find village: scan from end
        v_idx = len(words)
        for j in range(len(words) - 1, -1, -1):
            w = words[j].rstrip('.')
            if w.isupper() or re.match(r'^[A-Z][A-Z\s]*\([EWNS]\)$', w):
                v_idx = j
            elif j == len(words) - 1 and not w.isupper():
                v_idx = j
            elif j < len(words) - 2:
                break
        
        village = ' '.join(words[v_idx:]).rstrip('.')
        
        if village and len(village) > 2:
            villages.add(village)
            # Firka: words between zone-start and village
            firka_parts = words[:v_idx]
            if firka_parts:
                firka = ' '.join(firka_parts[-2:]) if len(firka_parts) >= 2 else firka_parts[0]
                if firka not in firka_villages:
                    firka_villages[firka] = []
                if village not in firka_villages[firka]:
                    firka_villages[firka].append(village)
    
    all_villages[taluk] = {
        'villages': sorted(villages),
        'firka_villages': {f: sorted(vs) for f, vs in firka_villages.items()}
    }
    vcount = len(all_villages[taluk]['villages'])
    fcount = len(all_villages[taluk]['firka_villages'])
    print(f'{taluk}: {vcount} villages, {fcount} firkas')

total_villages = sum(len(v['villages']) for v in all_villages.values())
print(f'\nTotal: {total_villages} villages')

# c__1.pdf lease cases
r = PdfReader(base + '/c__1.pdf')
lease_text = ''
for page in r.pages:
    lease_text += page.extract_text() + '\n'
print(f'\nc__1.pdf (Lease Cases): {len(r.pages)} pages')

# c__2.pdf old villages
r2 = PdfReader(base + '/c__2.pdf')
old_text = ''
for page in r2.pages:
    old_text += page.extract_text() + '\n'
first_line = old_text.strip().split('\n')[0] if old_text.strip() else '(empty)'
print(f'c__2.pdf (Old Villages): {first_line[:200]}')

# Merge into JSON
with open(json_path, 'r', encoding='utf-8-sig') as f:
    data = json.load(f)

boundaries = data.get('administrative_boundaries_coimbatore_district', {})
boundaries['village_boundaries'] = {
    'source': 'c__3.pdf through c__13.pdf',
    'taluks': {
        taluk: info['villages'] for taluk, info in sorted(all_villages.items())
    },
    'firka_details': {
        taluk: info['firka_villages'] for taluk, info in sorted(all_villages.items())
    }
}

data['administrative_boundaries_coimbatore_district'] = boundaries

# Save lease data too
lease_lines = lease_text.strip().split('\n')
lease_data = []
current_taluk = ''
for line in lease_lines[:200]:
    if 'TALUK' in line.upper() or 'Taluk' in line:
        current_taluk = line.strip()
    elif re.match(r'^\d+\.?\s+\d', line):
        parts = re.split(r'\s{2,}', line)
        if len(parts) >= 4:
            lease_data.append({'line': line.strip()[:100]})

data['lease_cases'] = {
    'source': 'c__1.pdf',
    'description': 'List of lease cases - Coimbatore District',
    'details': lease_lines[:20]
}

with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print('Merged into JSON successfully')
