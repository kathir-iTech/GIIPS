import sqlite3

DB = r'C:\Users\jeeva\Desktop\GIIPS-opencode\ai-engine\data\giips.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

for col in ['photo_hash', 'photo_duplicate_flag', 'photo_duplicate_of']:
    try:
        c.execute('ALTER TABLE complaints ADD COLUMN ' + col + ' VARCHAR')
        conn.commit()
        print('MIGRATION: added', col)
    except Exception as e:
        print('MIGRATION:', col, 'already exists:', e)

row = c.execute(
    "SELECT sql FROM sqlite_master WHERE type='table' AND name='complaints'"
).fetchone()
print()
print('=== SCHEMA ===')
print(row[0])
conn.close()
