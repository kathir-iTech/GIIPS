import json
with open(r'C:\Users\jeeva\Desktop\GIIPS-opencode\ai-engine\data\ccmc_officer_directory.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('JSON valid')
print(f'Top-level keys ({len(data)}): {list(data.keys())}')

for c in data['councilors'][:5]:
    print(f'  Ward {c["ward_number"]}: {c["councilor_name"]} -> {c["phone"]}')

print()
for d in data['property_tax_defaulters'][:5]:
    print(f'  Ward {d["ward_number"]} ({d["zone"]}): {d["owner_name"][:40]} -> {d["phone"]}')

all_phones = set()
for c in data['councilors']:
    all_phones.add(c['phone'])
for d in data['property_tax_defaulters']:
    all_phones.add(d['phone'])
print(f'\nTotal unique contact numbers: {len(all_phones)}')
print(f'Total entries: {sum(len(v) for v in data.values() if isinstance(v, list))}')
