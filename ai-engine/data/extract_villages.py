from pypdf import PdfReader
import json, re, os

base = r'C:\Users\jeeva\Desktop\GIIPS-opencode'
json_path = os.path.join(base, r'ai-engine\data\ccmc_officer_directory.json')

taluk_files = {
    3: 'Madukkarai', 4: 'Perur', 5: 'Sulur', 6: 'Coimbatore North',
    7: 'Mettupalayam', 8: 'Annur', 9: 'Pollachi', 10: 'Kinathukadavu',
    11: 'Kinathukadavu', 12: 'Valparai', 13: 'Anaimalai'
}

all_villages = {}
duplicate_check = set()

for fid, tname in sorted(taluk_files.items()):
    path = os.path.join(base, f'c__{fid}.pdf')
    if not os.path.exists(path):
        continue
    
    r = PdfReader(path)
    text = ''
    for page in r.pages:
        txt = page.extract_text()
        clean = ''.join(c if c.isprintable() or c in '\n\r\t' else '?' for c in txt)
        text += clean + '\n'
    
    lines = text.strip().split('\n')
    
    # Get actual taluk name from PDF
    actual_taluk = tname
    for line in lines:
        if 'TALUK' in line.upper() and 'NAME' not in line.upper():
            actual_taluk = line.strip().replace('TALUK', '').replace('Taluk', '').strip()
            break
    
    firka_villages = {}  # firka -> [villages]
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip header
        if re.match(r'^S\.?No', line) or 'District' in line or 'Village' in line:
            continue
        if re.match(r'^[A-Z][A-Z\s]+$', line) and len(line) < 30:
            continue  # Skip header-like lines
        
        # Match: serial district rdo taluk zone firka village
        # Split by 2+ spaces
        parts = re.split(r'\s{2,}', line)
        if len(parts) >= 5:
            # First part is serial+district+rdo+taluk merged (single-spaced)
            # Try to extract village from last part
            village = parts[-1].strip().rstrip('.')
            firka = parts[-2].strip()
            
            # Try alternative: split single-spaced entries
            if len(parts) == 5:
                # parts[0] could be "N Coimbatore Coimbatore TALUKNAME"
                first_parts = parts[0].split()
                if len(first_parts) >= 4:
                    firka = parts[-3]
                    village = parts[-1].strip().rstrip('.')
            
            if village and village != firka:
                if firka not in firka_villages:
                    firka_villages[firka] = []
                if village not in firka_villages[firka]:
                    firka_villages[firka].append(village)
        elif len(parts) >= 3:
            # Simpler: just take last 3 columns
            firka = parts[-2].strip()
            village = parts[-1].strip().rstrip('.')
            if village and village != firka:
                if firka not in firka_villages:
                    firka_villages[firka] = []
                if village not in firka_villages[firka]:
                    firka_villages[firka].append(village)
    
    if actual_taluk not in all_villages or fid not in [10, 11]:  # Skip duplicate Kinathukadavu
        all_villages[actual_taluk] = firka_villages

# Print summary
total_villages = 0
for taluk, firkas in sorted(all_villages.items()):
    vcount = sum(len(v) for v in firkas.values())
    total_villages += vcount
    fcount = len(firkas)
    print(f'{taluk}: {fcount} firkas, {vcount} villages')
    for f, vs in sorted(firkas.items()):
        print(f'   {f}: {", ".join(vs[:5])}{"..." if len(vs) > 5 else ""}')

print(f'\nTotal villages: {total_villages}')

# ─── Merge into JSON ───
with open(json_path, 'r', encoding='utf-8-sig') as f:
    data = json.load(f)

if 'administrative_boundaries_coimbatore_district' not in data:
    data['administrative_boundaries_coimbatore_district'] = {}

boundaries = data['administrative_boundaries_coimbatore_district']
if 'village_boundaries' not in boundaries:
    boundaries['village_boundaries'] = {}

boundaries['village_boundaries'] = {
    'source': 'c__3.pdf through c__13.pdf (Coimbatore district taluk-wise village lists)',
    'taluks': {}
}

for taluk, firkas in sorted(all_villages.items()):
    boundaries['village_boundaries']['taluks'][taluk] = {
        'firkas': {f: sorted(vs) for f, vs in sorted(firkas.items())}
    }

with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print(f'\nMerged into JSON successfully')
