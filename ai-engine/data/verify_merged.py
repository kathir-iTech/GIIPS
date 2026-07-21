import json
with open(r'C:\Users\jeeva\Desktop\GIIPS-opencode\ai-engine\data\ccmc_officer_directory.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('JSON valid')
print(f'Top-level keys: {list(data.keys())}')

c = data['councilors']
print(f'\nCouncilors: {len(c)}')
wards = set(x['ward_number'] for x in c)
print(f'  Unique wards: {len(wards)}')
print(f'  Ward 1: {c[0]}')

d = data['property_tax_defaulters']
print(f'\nDefaulters: {len(d)}')
print(f'  Wards: {sorted(set(x["ward_number"] for x in d))}')
print(f'  Zones: {set(x["zone"] for x in d)}')

print('\nSample defaulters:')
for e in d[:5]:
    print(f'  Ward {e["ward_number"]}: {e["owner_name"][:40]:40s} {e["phone"]}  {e["address"][:30]}')

# Check entry 56 (ward 8): R SOUNDARARAJAN 7708012229
for e in d:
    if 'SOUNDARARAJAN' in e['owner_name']:
        print(f'  Found: Ward {e["ward_number"]}: {e["owner_name"]} {e["phone"]} {e["address"][:30]}')

size = len(json.dumps(data))
print(f'\nTotal file size: {size} chars')

all_phones = set()
for x in c:
    all_phones.add(x['phone'])
for x in d:
    all_phones.add(x['phone'])
print(f'Unique phone numbers: {len(all_phones)}')
