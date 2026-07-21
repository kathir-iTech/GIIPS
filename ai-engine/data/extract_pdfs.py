from pypdf import PdfReader
import os, re

c1_base = os.path.join(os.environ['USERPROFILE'], r'Desktop\GIIPS-opencode\c_1\ccmc.gov.in')
out_base = os.path.join(os.environ['USERPROFILE'], r'Desktop\GIIPS-opencode\ai-engine\data\pdf_extracts')
os.makedirs(out_base, exist_ok=True)

pdfs = []
for root, dirs, files in os.walk(c1_base):
    for f in files:
        if f.lower().endswith('.pdf'):
            path = os.path.join(root, f)
            size_mb = os.path.getsize(path) / (1024*1024)
            if size_mb > 10:
                rel = path.replace(c1_base, '').lstrip('\\/')
                print(f'[SKIP >10MB] {rel} ({size_mb:.0f}MB)')
                continue
            pdfs.append(path)

print(f'Processing {len(pdfs)} PDFs...')
pdfs.sort()

for path in pdfs:
    rel = path.replace(c1_base, '').lstrip('\\/')
    size_kb = os.path.getsize(path) / 1024
    try:
        r = PdfReader(path)
        pages = len(r.pages)
        all_text = ''
        for i, page in enumerate(r.pages):
            txt = page.extract_text()
            clean = ''.join(c if c.isprintable() or c in '\n\r\t' else '?' for c in txt)
            all_text += clean + '\n---PAGE BREAK---\n'
        total_chars = len(all_text)
        if total_chars < 20:
            print(f'[SCANNED] {pages:3d}p {size_kb:7.1f}KB {rel}')
        else:
            safe_name = rel.replace('\\', '_').replace('/', '_').replace(':', '_')
            out_path = os.path.join(out_base, safe_name + '.txt')
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(all_text)
            first = all_text.strip().split('\n')[0][:120]
            print(f'[OK] {pages:3d}p {size_kb:7.1f}KB {rel}')
            print(f'  -> {first}')
    except Exception as e:
        print(f'[ERR] {size_kb:7.1f}KB {rel}  {str(e)[:80]}')
