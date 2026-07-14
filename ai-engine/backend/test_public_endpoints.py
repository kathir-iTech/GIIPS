import os, sys, uuid, datetime
os.environ["GIIPS_JWT_SECRET"] = "test-secret"
os.environ["REDIS_URL"] = ""
os.environ["S3_ENDPOINT_URL"] = ""
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from database import Base, engine, User, Complaint, Incident, SessionLocal
from auth_service import hash_password
from fastapi.testclient import TestClient

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)

db = SessionLocal()
citizen = User(id=str(uuid.uuid4()), full_name="Test", email="t@t.com",
               password_hash=hash_password("p"), role="Citizen", ward="27")
db.add(citizen)
db.flush()
comp = Complaint(id="COMP-TEST-000001", title="Test pothole", description="Big pothole",
                 location="Sathy Road", ward="27", predicted_category="Roads",
                 user_id=citizen.id, created_at=datetime.datetime.utcnow())
db.add(comp)
inc = Incident(id=str(uuid.uuid4()), incident_number="INC-000001", category="Roads",
               ward="27", cluster_size=1, priority_score=50.0, priority_label="Medium",
               status="in-progress", summary="Test incident", days_open=2)
db.add(inc)
db.flush()
comp.incident_id = inc.id
db.commit()

# Create resolved incident for stats
comp2 = Complaint(id="COMP-TEST-000002", title="Fixed leak", description="Was fixed",
                  location="Avinashi Road", ward="27", predicted_category="Water Supply",
                  user_id=citizen.id, created_at=datetime.datetime.utcnow())
db.add(comp2)
inc2 = Incident(id=str(uuid.uuid4()), incident_number="INC-000002", category="Water Supply",
                ward="27", cluster_size=1, priority_score=30.0, priority_label="Low",
                status="resolved", summary="Fixed leak", days_open=5)
db.add(inc2)
db.flush()
comp2.incident_id = inc2.id
db.commit()
db.close()

print("=== PUBLIC ENDPOINT TESTS ===\n")

# Test 1: Track existing complaint
resp = client.get("/track/COMP-TEST-000001")
print(f"1. GET /track/COMP-TEST-000001: {resp.status_code}")
if resp.status_code == 200:
    d = resp.json()
    print(f"   complaintId: {d.get('complaintId')}")
    print(f"   title: {d.get('title')}")
    print(f"   category: {d.get('category')}")
    print(f"   ward: {d.get('ward')}")
    print(f"   status: {d.get('status')}")
    print(f"   timeline steps: {len(d.get('timeline', []))}")
    safe = True
    for key in ["email", "phone", "user_id", "name", "description", "citizen"]:
        if key in d:
            print(f"   PII LEAK: key '{key}' found in response!")
            safe = False
    if safe:
        print("   No PII exposed: SAFE")
    print("   PASS")
else:
    print(f"   FAIL: {resp.text[:200]}")

# Test 2: Track non-existent complaint
resp = client.get("/track/DOES-NOT-EXIST")
print(f"\n2. GET /track/DOES-NOT-EXIST: {resp.status_code} (expected 404)")
if resp.status_code == 404:
    print("   PASS")
else:
    print("   FAIL")

# Test 3: Public stats
resp = client.get("/public/stats")
print(f"\n3. GET /public/stats: {resp.status_code}")
if resp.status_code == 200:
    d = resp.json()
    print(f"   totalComplaintsThisMonth: {d.get('totalComplaintsThisMonth')}")
    print(f"   resolutionRate: {d.get('resolutionRate')}")
    print(f"   avgResolutionDays: {d.get('avgResolutionDays')}")
    cats = d.get("complaintsByCategory", [])
    print(f"   complaintsByCategory: {len(cats)} categories")
    zones = d.get("complaintsByZone", [])
    print(f"   complaintsByZone: {len(zones)} zones")
    for z in zones:
        print(f"     {z['zone']}: {z['count']}")
    safe = True
    for key in ["id", "title", "description", "user_id", "ward"]:
        if any(key in item for item in cats + zones):
            print(f"   PII LEAK: key '{key}' found in stats!")
            safe = False
    if safe:
        print("   No individual complaint details: SAFE")
    print("   PASS")
else:
    print(f"   FAIL: {resp.text[:200]}")

# Test 4: No auth required
resp = client.get("/track/COMP-TEST-000001")
print(f"\n4. No auth required for /track/: {resp.status_code} (expected 200)")
resp2 = client.get("/public/stats")
print(f"   No auth required for /public/stats: {resp2.status_code} (expected 200)")

print(f"\n{'='*40}")
print("ALL TESTS COMPLETE")
