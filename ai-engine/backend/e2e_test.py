"""
E2E test: photo duplicate detection.
Starts the server, registers a user, uploads same photo twice,
verifies photo_duplicate_flag is set on second upload.
"""
import os, sys, time, json, io, uuid, subprocess, signal

# Set env vars BEFORE starting server
os.environ["GIIPS_JWT_SECRET"] = "test-secret-key"
os.environ["DATABASE_URL"] = "sqlite:///C:/Users/jeeva/Desktop/GIIPS-opencode/ai-engine/data/giips.db"

BASE = "http://localhost:8001"
PORT = 8001
SERVER_DIR = r"C:\Users\jeeva\Desktop\GIIPS-opencode\ai-engine\backend"
LOG_FILE = r"C:\Users\jeeva\AppData\Local\Temp\opencode\server_e2e.log"

import requests

# ── 1. Start server ──────────────────────────────────────────────────────
print("=" * 60)
print("E2E TEST: PHOTO DUPLICATE DETECTION")
print("=" * 60)

# Ensure log file is clean
try: os.remove(LOG_FILE)
except FileNotFoundError: pass

server_env = os.environ.copy()
server_env["GIIPS_JWT_SECRET"] = "test-secret-key"
server_env["DATABASE_URL"] = "sqlite:///C:/Users/jeeva/Desktop/GIIPS-opencode/ai-engine/data/giips.db"
# Set a dummy allowed origin so CORS doesn't block localhost
server_env["GIIPS_ALLOWED_ORIGINS"] = "http://localhost:8001"

print(f"\nStarting uvicorn on port {PORT}...")
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", str(PORT)],
    cwd=SERVER_DIR,
    env=server_env,
    stdout=open(LOG_FILE, "w"),
    stderr=subprocess.STDOUT,
)

# Wait for server
for i in range(40):
    try:
        r = requests.get(f"{BASE}/docs", timeout=2)
        if r.status_code == 200:
            print(f"Server up after ~{i+1}s")
            break
    except requests.RequestException:
        pass
    time.sleep(1)
else:
    print("SERVER FAILED TO START IN TIME")
    with open(LOG_FILE) as f:
        print(f.read())
    proc.kill()
    sys.exit(1)

def read_server_log():
    with open(LOG_FILE) as f:
        return f.read()

# ── 2. Register test user ───────────────────────────────────────────────
suffix = str(uuid.uuid4())[:8]
email = f"dup-test-{suffix}@test.com"
password = "testpass123"

print(f"\nRegistering {email}...")
r = requests.post(f"{BASE}/auth/register", json={
    "email": email, "password": password, "full_name": "Duplicate Test User",
})
print(f"  Register: {r.status_code}", end="")
if r.status_code == 200:
    print(f" user_id={r.json().get('user_id','?')[:8]}...")
else:
    print(f" {r.text[:200]}")
    # If already registered, that's fine — try login below

# ── 3. Login and extract token manually ─────────────────────────────────
print(f"Logging in...")
r = requests.post(f"{BASE}/auth/login", json={
    "email": email, "password": password,
})
print(f"  Login: {r.status_code}", end="")
if r.status_code != 200:
    print(f" {r.text[:300]}")
    proc.kill()
    sys.exit(1)
print(f" user_id={r.json().get('user_id','?')[:8]}...")

# Extract token from the Set-Cookie header manually
# The cookie is httpOnly and Secure, so requests.Session won't send it over HTTP
# We need to manually parse the token from the cookie
set_cookie = r.headers.get("Set-Cookie", "")
print(f"  Set-Cookie: {set_cookie[:100]}...")
token = None
for part in set_cookie.split(";"):
    part = part.strip()
    if part.startswith("access_token="):
        token = part.split("=", 1)[1]
        break

if not token:
    # Try the response body
    print(f"  No cookie found, checking response body...")
    print(f"  Response: {r.text[:300]}")
    proc.kill()
    sys.exit(1)

headers = {"Authorization": f"Bearer {token}"}
print(f"  Token: {token[:30]}...")

# ── 4. Create test photo ────────────────────────────────────────────────
from PIL import Image, ImageDraw
import random

img = Image.new("RGB", (400, 300), (35, 35, 35))
draw = ImageDraw.Draw(img)
draw.ellipse([50, 50, 350, 250], fill=(90, 90, 90), outline=(170, 170, 170), width=5)
for _ in range(25):
    x, y = random.randint(60, 340), random.randint(60, 240)
    draw.ellipse([x-3, y-3, x+3, y+3], fill=(random.randint(150,220),)*3)
buf = io.BytesIO()
img.save(buf, format="PNG")
photo_data = buf.getvalue()
print(f"\nTest photo created: {len(photo_data)} bytes")

# ── 5. Submit first complaint ───────────────────────────────────────────
print(f"\n--- COMPLAINT 1 (first upload) ---")
r = requests.post(f"{BASE}/complaints", json={
    "title": "Deep pothole near bus stop",
    "description": "Large pothole on main road near the bus stop causing traffic hazard",
    "location": "Bus Stop Road, Coimbatore",
    "ward": "Ward-42",
}, headers=headers)
print(f"  Submit: {r.status_code}", end="")
if r.status_code >= 400:
    print(f" {r.text[:500]}")
    print(f"\n--- SERVER LOGS ---")
    print(read_server_log()[-3000:])
    proc.kill()
    sys.exit(1)

resp1 = r.json()
cid1 = resp1.get("complaintId")
print(f"  complaintId={cid1}")

# Upload photo to first complaint
print(f"Uploading photo to complaint 1...")
r = requests.post(
    f"{BASE}/complaints/{cid1}/upload",
    files={"file": ("pothole.png", io.BytesIO(photo_data), "image/png")},
    headers=headers,
)
print(f"  Upload 1: {r.status_code}", end="")
if r.status_code >= 400:
    print(f" {r.text[:500]}")
    print(f"\n--- SERVER LOGS ---")
    print(read_server_log()[-3000:])
    proc.kill()
    sys.exit(1)

resp_upload1 = r.json()
print(f"  Response: {json.dumps(resp_upload1, indent=2)}")
hash1 = resp_upload1.get("photoHash")

# Wait for ML pipeline
print("Waiting for pipeline...")
time.sleep(5)

# ── 6. Submit second complaint with SAME photo ──────────────────────────
print(f"\n--- COMPLAINT 2 (same photo, should flag duplicate) ---")
r = requests.post(f"{BASE}/complaints", json={
    "title": "Road damage at bus stop",
    "description": "There is a big hole near the bus stop that needs repair",
    "location": "Near Bus Stop, Coimbatore",
    "ward": "Ward-42",
}, headers=headers)
print(f"  Submit: {r.status_code}", end="")
if r.status_code >= 400:
    print(f" {r.text[:500]}")
    print(f"\n--- SERVER LOGS ---")
    print(read_server_log()[-3000:])
    proc.kill()
    sys.exit(1)

resp2 = r.json()
cid2 = resp2.get("complaintId")
print(f"  complaintId={cid2}")

# Upload SAME photo to second complaint
print(f"Uploading SAME photo to complaint 2...")
r = requests.post(
    f"{BASE}/complaints/{cid2}/upload",
    files={"file": ("pothole.png", io.BytesIO(photo_data), "image/png")},
    headers=headers,
)
print(f"  Upload 2: {r.status_code}", end="")
if r.status_code >= 400:
    print(f" {r.text[:500]}")
    print(f"\n--- SERVER LOGS ---")
    print(read_server_log()[-3000:])
    proc.kill()
    sys.exit(1)

resp_upload2 = r.json()
print(f"  Response: {json.dumps(resp_upload2, indent=2)}")

# ── 7. Also verify via /my endpoint ──────────────────────────────────────
print(f"\n--- VERIFY via /my endpoint ---")
r = requests.get(f"{BASE}/my", headers=headers)
if r.status_code == 200:
    data = r.json()
    complaints_list = data if isinstance(data, list) else data.get("complaints", data.get("data", []))
    for c in complaints_list:
        if isinstance(c, dict) and c.get("id") == cid2:
            print(f"  /my says: flag={c.get('photo_duplicate_flag')!r} of={c.get('photo_duplicate_of')!r}")

# ── 8. Verify via /incidents ────────────────────────────────────────────
print(f"\n--- VERIFY via /incidents endpoint ---")
r = requests.get(f"{BASE}/incidents", headers=headers)
if r.status_code == 200:
    for inc in r.json().get("incidents", []):
        for c in inc.get("complaints", []):
            if c.get("id") in (cid1, cid2):
                print(f"  Incident {inc.get('incident_number')}: complaint {c['id'][:8]}... flag={c.get('photo_duplicate_flag')!r} of={c.get('photo_duplicate_of')!r}")

# ── 9. PASS/FAIL ────────────────────────────────────────────────────────
print(f"\n{'=' * 60}")
flag = resp_upload2.get("photoDuplicateFlag")
if flag in ("possible_duplicate_submission", "reused_image"):
    print(f"RESULT: PASS - photo_duplicate_flag='{flag}' confirmed")
else:
    print(f"RESULT: FAIL - photo_duplicate_flag='{flag}' (expected one of: possible_duplicate_submission, reused_image)")

# Cleanup
proc.kill()
proc.wait()
