import json
with open(r'C:\Users\jeeva\Desktop\GIIPS-opencode\ai-engine\data\ccmc_officer_directory.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('JSON: VALID')
print(f'Top-level keys: {list(data.keys())}')
print()

# Count everything
for k, v in data.items():
    if isinstance(v, list):
        print(f'  {k}: {len(v)} entries')
    elif isinstance(v, dict):
        if k == 'administrative_boundaries_coimbatore_district':
            b = v
            vb = b.get('village_boundaries', {})
            taluks = vb.get('taluks', {})
            total_v = sum(len(vs) for vs in taluks.values())
            print(f'  administrative_boundaries -> village_boundaries: {len(taluks)} taluks, {total_v} villages')
            for t, vs in sorted(taluks.items()):
                print(f'    {t}: {len(vs)} villages')
        else:
            print(f'  {k}: dict with keys {list(v.keys())}')

# Unique phone numbers
phones = set()
for lst_name in ['officer_directory', 'zonal_officers', 'ward_contacts', 'councilors', 'property_tax_defaulters']:
    if lst_name in data:
        for item in data[lst_name]:
            if isinstance(item, dict) and 'phone' in item:
                p = item['phone']
                if p and len(str(p)) >= 10:
                    phones.add(str(p))
print(f'\nTotal unique phone numbers: {len(phones)}')

# File size
import os
size = os.path.getsize(r'C:\Users\jeeva\Desktop\GIIPS-opencode\ai-engine\data\ccmc_officer_directory.json')
print(f'File size: {size:,} bytes')
