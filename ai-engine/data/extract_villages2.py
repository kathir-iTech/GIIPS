from pypdf import PdfReader
import json, re, os

base = r'C:\Users\jeeva\Desktop\GIIPS-opencode'
json_path = os.path.join(base, r'ai-engine\data\ccmc_officer_directory.json')

taluk_files = {
    3: 'Madukkarai', 4: 'Perur', 5: 'Sulur', 6: 'Coimbatore North',
    7: 'Mettupalayam', 8: 'Annur', 9: 'Pollachi', 10: 'Kinathukadavu',
    12: 'Valparai', 13: 'Anaimalai'
}

all_villages = {}

for fid, tname in sorted(taluk_files.items()):
    path = os.path.join(base, f'c__{fid}.pdf')
    if not os.path.exists(path):
        continue
    
    r = PdfReader(path)
    text = ''
    for page in r.pages:
        txt = page.extract_text()
        text += txt + '\n'
    
    lines = text.strip().split('\n')
    
    # Get taluk name from first line
    taluk = tname
    for line in lines:
        if 'TALUK' in line.upper():
            taluk = line.strip().replace('TALUK', '').replace('Taluk', '').strip()
            break
    
    # Extract villages: each data line ends with the village name
    # Strategy: skip header, take lines that start with a number
    # Split by whitespace, reconstruct village as content after "Coimbatore ..."
    # Or: village is everything after the KNOWN prefix
    
    villages = set()
    firka_map = {}
    
    for line in lines:
        line = line.strip()
        if not line or re.match(r'^S\.?No', line) or 'District' in line:
            continue
        
        m = re.match(r'(\d+)\s+(.*)', line)
        if not m:
            continue
        
        rest = m.group(2).strip()
        
        # Remove known "Coimbatore" prefix (district)
        # After district, the next words contain RDO + Taluk + Zone + Firka + Village
        # We know: after RDO comes zone/firka/village
        # Village is the LAST element that ends with optional period
        
        # Find village: look for the last ALL-CAPS word/group that may have (E)/(W)/(N)/(S) suffix
        # Village ends with optional period
        parts = rest.split()
        
        # The village is the last content before end-of-string
        # It might be multiple words like "KALAPATTY (EAST)"
        # Find where the zone starts by looking at known RDO/taluk patterns
        
        # Simple approach: try known RDO patterns
        rdo_prefixes = ['Coimbatore North', 'Coimbatore', 'Pollachi']
        
        stripped = rest
        
        # Remove RDO from the beginning
        rdo_found = None
        for rdo in rdo_prefixes:
            if stripped.startswith(rdo):
                rdo_found = rdo
                stripped = stripped[len(rdo):].strip()
                break
        
        # Remove taluk name from the beginning
        if stripped.upper().startswith(taluk.upper()):
            stripped = stripped[len(taluk):].strip()
        
        if rdo_found == 'Coimbatore':
            # The RDO is "Coimbatore" and taluk was already consumed
            # What remains: ZONE FIRKA VILLAGE
            # Try to split into parts
            remaining = stripped.split()
            if len(remaining) >= 3:
                # Zone could be first word, firka could be next 1-2 words, village is last 1-3 words
                # Actually let me just try to detect the village pattern
                pass
        
        # Simpler - just take the LAST word as village (it's all-caps with optional period)
        words = rest.split()
        
        # Reconstruct: find village by looking backwards
        # Village is all-caps, often followed by period
        village_parts = []
        for w in reversed(words):
            clean_w = w.rstrip('.')
            if clean_w.isupper() or '(' in w:
                village_parts.insert(0, w)
            else:
                # If we hit a lowercase word before finding the village, stop
                if not village_parts:
                    village_parts.insert(0, w)
                break
        
        village = ' '.join(village_parts).rstrip('.')
        
        if village and len(village) > 1:
            villages.add(village)
    
    all_villages[taluk] = sorted(villages)
    print(f'{taluk}: {len(villages)} villages')

total = sum(len(v) for v in all_villages.values())
print(f'\nTotal: {total} villages')

# ─── Merge into JSON ───
with open(json_path, 'r', encoding='utf-8-sig') as f:
    data = json.load(f)

boundaries = data.get('administrative_boundaries_coimbatore_district', {})
if 'village_boundaries' not in boundaries:
    boundaries['village_boundaries'] = {}

boundaries['village_boundaries'] = {
    'source': 'c__3.pdf through c__13.pdf (taluk-wise village lists)',
    'taluks': {}
}
for taluk in sorted(all_villages.keys()):
    boundaries['village_boundaries']['taluks'][taluk] = all_villages[taluk]

data['administrative_boundaries_coimbatore_district'] = boundaries

with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print('Merged into JSON')
