from pypdf import PdfReader
import json, re, os

base = r'C:\Users\jeeva\Desktop\GIIPS-opencode'
json_path = os.path.join(base, r'ai-engine\data\ccmc_officer_directory.json')

# ─── Extract taluk village data (c__3 through c__13) ───
taluk_data = {}
for i in range(3, 14):
    path = os.path.join(base, f'c__{i}.pdf')
    if not os.path.exists(path):
        continue
    try:
        r = PdfReader(path)
        text = ''
        for page in r.pages:
            txt = page.extract_text()
            clean = ''.join(c if c.isprintable() or c in '\n\r\t' else '?' for c in txt)
            text += clean + '\n'
        
        # Get taluk name from first line
        lines = text.strip().split('\n')
        taluk_name = ''
        for line in lines:
            if 'Taluk' in line or 'TALUK' in line:
                taluk_name = line.strip()
                break
        
        # Parse village entries: find lines with patterns like
        # "N Coimbatore ... VillageName"
        villages = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Skip header lines
            if 'S.No' in line or 'Sl.No' in line or 'District' in line or 'RDO' in line or 'Taluk' in line or 'Firka' in line or 'Zone' in line or 'Village' in line:
                continue
            # Match: Serial District RDO Taluk Zone Firka Village
            m = re.match(r'(\d+)\s+([A-Za-z\s]+?)(?:\s+(Coimbatore|Pollachi))', line)
            if m:
                parts = re.split(r'\s{2,}', line)
                if len(parts) >= 6:
                    village = parts[-1].strip().rstrip('.')
                    firka = parts[-2].strip()
                    zone = parts[-3].strip() if len(parts) >= 7 else ''
                    if village and village not in villages:
                        villages.append(village)
        
        # Simpler approach: extract villages from lines with village names
        # Villages are at the end, often with a period suffix
        for line in lines:
            line = line.strip()
            # Find entries that end with a village name in caps
            # Villages end with . at the end of the line
            if re.search(r'[A-Z][A-Z\s]+\w\.$', line) and not re.match(r'^\d', line):
                continue
            
        taluk_data[i] = {
            'taluk': taluk_name,
            'villages': villages,
            'raw_text': text[:2000]
        }
    except Exception as e:
        print(f'c__{i}.pdf: ERROR - {e}')

for i in sorted(taluk_data.keys()):
    print(f'c__{i}.pdf: {taluk_data[i]["taluk"]} - {len(taluk_data[i]["villages"])} villages')
