import pytest
import uuid
from database import SessionLocal, Complaint, Incident
from datetime import datetime


def _classify_complaint(client, text):
    resp = client.post("/classify", json={"text": text})
    assert resp.status_code == 200
    return resp.json()["predicted_category"]


def _create_test_incident(db, complaint_id, category, ward):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    inc_id = str(uuid.uuid4())
    incident = Incident(
        id=inc_id,
        incident_number=f"INC-TEST-{inc_id[:6].upper()}",
        category=category,
        ward=ward or "27",
        cluster_size=1,
        priority_score=50.0,
        priority_label="Medium",
        status="open",
        summary=complaint.title,
        days_open=0,
    )
    db.add(incident)
    db.flush()
    complaint.predicted_category = category
    complaint.confidence = 0.85
    complaint.priority = "Medium"
    complaint.incident_id = incident.id
    db.commit()
    return inc_id


class TestAuthFlow:

    def test_register_new_citizen(self, client):
        email = f"testuser_{uuid.uuid4().hex[:8]}@example.com"
        resp = client.post("/auth/register", json={
            "full_name": "Test User",
            "email": email,
            "password": "testpass123",
            "district": "Coimbatore",
            "ward": "27",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "Citizen"
        assert "user_id" in data

    def test_register_duplicate_email_fails(self, client):
        resp = client.post("/auth/register", json={
            "full_name": "Duplicate",
            "email": "citizen@giips.gov.in",
            "password": "password123",
        })
        assert resp.status_code == 400
        assert "already" in resp.json()["detail"].lower()

    def test_register_gov_email_fails(self, client):
        resp = client.post("/auth/register", json={
            "full_name": "Gov User",
            "email": "someuser@gov.in",
            "password": "password123",
        })
        assert resp.status_code == 400
        assert "government" in resp.json()["detail"].lower()

    def test_login_returns_user_info(self, client, citizen_token):
        resp = client.post("/auth/login", json={
            "email": "citizen@giips.gov.in",
            "password": "password123",
        })
        assert resp.status_code == 200
        login_data = resp.json()
        assert login_data["role"] == "Citizen"
        assert login_data["full_name"] == "Ravi Krishnan"

    def test_get_profile_with_token(self, client, citizen_auth):
        me_resp = client.get("/auth/me", headers=citizen_auth)
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "citizen@giips.gov.in"
        assert me_resp.json()["role"] == "Citizen"

    def test_login_invalid_credentials_fails(self, client):
        resp = client.post("/auth/login", json={
            "email": "citizen@giips.gov.in",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_register_government_email_blocked(self, client):
        resp = client.post("/auth/register", json={
            "full_name": "Blocked",
            "email": "official@gov.in",
            "password": "password123",
        })
        assert resp.status_code == 400
        assert "government" in resp.json()["detail"].lower()


class TestComplaintFlow:

    def test_submit_complaint_and_check_status(self, client, citizen_auth):
        resp = client.post("/complaints", json={
            "title": "Large pothole on Sathy Road",
            "description": "There is a deep pothole near Hope College junction causing accidents",
            "location": "Sathy Road, Near Hope College, Coimbatore",
            "ward": "27",
        }, headers=citizen_auth)
        assert resp.status_code == 202
        data = resp.json()
        complaint_id = data["complaintId"]
        assert data["statusUrl"] == f"/complaints/{complaint_id}/status"

        category = _classify_complaint(client,
            "Large pothole on Sathy Road near Hope College junction damaging vehicles")
        assert category == "Roads"

        db = SessionLocal()
        try:
            incident_id = _create_test_incident(db, complaint_id, category, "27")
        finally:
            db.close()

        status_resp = client.get(f"/complaints/{complaint_id}/status", headers=citizen_auth)
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["status"] == "completed"
        assert status_data["result"]["predictedCategory"] == "Roads"

    def test_submit_complaint_without_auth_fails(self, client):
        resp = client.post("/complaints", json={
            "title": "Test complaint",
            "description": "Test description",
            "location": "Test location",
        })
        assert resp.status_code == 401

    def test_submit_complaint_with_invalid_data_fails(self, client, citizen_auth):
        resp = client.post("/complaints", json={
            "title": "",
            "description": "",
            "location": "",
        }, headers=citizen_auth)
        assert resp.status_code == 422


class TestOfficerFlow:

    def test_officer_updates_incident_status(self, client, citizen_auth, officer_auth):
        resp = client.post("/complaints", json={
            "title": "Broken street light near junction",
            "description": "Street light has been broken for a week creating safety hazard at night",
            "location": "Gandhipuram, Coimbatore",
            "ward": "48",
        }, headers=citizen_auth)
        complaint_id = resp.json()["complaintId"]
        category = _classify_complaint(client,
            "Street light broken near Gandhipuram junction not working at night")
        db = SessionLocal()
        try:
            incident_id = _create_test_incident(db, complaint_id, category, "48")
        finally:
            db.close()

        update_resp = client.patch(
            f"/incidents/{incident_id}/status",
            json={"status": "in-progress"},
            headers=officer_auth,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["status"] == "in-progress"

        track_resp = client.get(f"/track/{complaint_id}")
        assert track_resp.status_code == 200
        track_data = track_resp.json()
        assert track_data["status"] == "in-progress"
        assert track_data["complaintId"] == complaint_id

    def test_citizen_cannot_update_status(self, client, citizen_auth, officer_auth):
        resp = client.post("/complaints", json={
            "title": "Garbage not collected",
            "description": "Garbage bins overflowing in our area for two weeks",
            "location": "RS Puram, Coimbatore",
            "ward": "46",
        }, headers=citizen_auth)
        complaint_id = resp.json()["complaintId"]
        category = _classify_complaint(client,
            "Garbage bins overflowing RS Puram not collected")
        db = SessionLocal()
        try:
            incident_id = _create_test_incident(db, complaint_id, category, "46")
        finally:
            db.close()

        update_resp = client.patch(
            f"/incidents/{incident_id}/status",
            json={"status": "in-progress"},
            headers=citizen_auth,
        )
        assert update_resp.status_code == 403


class TestVerifyResolutionFlow:

    def test_verify_resolution_full_flow(self, client, citizen_auth, officer_auth):
        resp = client.post("/complaints", json={
            "title": "Water pipe burst on Main Road",
            "description": "A water pipe has burst and water is flooding the street since yesterday",
            "location": "Avinashi Road, Peelamedu, Coimbatore",
            "ward": "27",
        }, headers=citizen_auth)
        complaint_id = resp.json()["complaintId"]
        category = _classify_complaint(client,
            "Water pipe burst flooding Avinashi Road")
        db = SessionLocal()
        try:
            incident_id = _create_test_incident(db, complaint_id, category, "27")
        finally:
            db.close()

        patch_resp = client.patch(
            f"/incidents/{incident_id}/status",
            json={"status": "resolved", "resolution_note": "Pipe repaired and road restored"},
            headers=officer_auth,
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["status"] == "pending_verification"

        db = SessionLocal()
        try:
            inc = db.query(Incident).filter(Incident.id == incident_id).first()
            code = inc.verification_code
            assert code is not None
        finally:
            db.close()

        verify_resp = client.post(
            f"/incidents/{incident_id}/verify-resolution",
            json={"code": code},
            headers=citizen_auth,
        )
        assert verify_resp.status_code == 200
        assert verify_resp.json()["status"] == "resolved"

        track_resp = client.get(f"/track/{complaint_id}")
        assert track_resp.status_code == 200
        assert track_resp.json()["status"] == "resolved"

        verify_resp2 = client.post(
            f"/incidents/{incident_id}/verify-resolution",
            json={"code": "000000"},
            headers=citizen_auth,
        )
        assert verify_resp2.status_code == 400


class TestRatingFlow:

    def test_rate_resolved_complaint(self, client, citizen_auth, officer_auth):
        resp = client.post("/complaints", json={
            "title": "Mosquito menace in our area",
            "description": "Stagnant water everywhere breeding mosquitoes, risk of dengue",
            "location": "Saravanampatti, Coimbatore",
            "ward": "3",
        }, headers=citizen_auth)
        complaint_id = resp.json()["complaintId"]
        category = _classify_complaint(client,
            "Mosquito breeding in stagnant water Saravanampatti dengue risk")

        db = SessionLocal()
        try:
            incident_id = _create_test_incident(db, complaint_id, category, "3")
        finally:
            db.close()

        client.patch(
            f"/incidents/{incident_id}/status",
            json={"status": "resolved", "resolution_note": "Fogging done and drains cleared"},
            headers=officer_auth,
        )
        db = SessionLocal()
        try:
            inc = db.query(Incident).filter(Incident.id == incident_id).first()
            code = inc.verification_code
        finally:
            db.close()
        client.post(
            f"/incidents/{incident_id}/verify-resolution",
            json={"code": code},
            headers=citizen_auth,
        )

        rate_resp = client.post(
            f"/complaints/{complaint_id}/rate",
            json={"rating": 4},
            headers=citizen_auth,
        )
        assert rate_resp.status_code == 200
        assert rate_resp.json()["rating"] == 4

        db = SessionLocal()
        try:
            comp = db.query(Complaint).filter(Complaint.id == complaint_id).first()
            assert comp.citizen_rating == 4
        finally:
            db.close()

        rate_resp2 = client.post(
            f"/complaints/{complaint_id}/rate",
            json={"rating": 5},
            headers=citizen_auth,
        )
        assert rate_resp2.status_code == 400
        assert "already" in rate_resp2.json()["detail"].lower()

    def test_rate_unresolved_complaint_fails(self, client, citizen_auth):
        resp = client.post("/complaints", json={
            "title": "Test unrated complaint",
            "description": "This complaint will not be resolved",
            "location": "Test location",
            "ward": "1",
        }, headers=citizen_auth)
        complaint_id = resp.json()["complaintId"]
        category = _classify_complaint(client,
            "Test complaint for rating test")
        db = SessionLocal()
        try:
            incident_id = _create_test_incident(db, complaint_id, category, "1")
        finally:
            db.close()

        rate_resp = client.post(
            f"/complaints/{complaint_id}/rate",
            json={"rating": 3},
            headers=citizen_auth,
        )
        assert rate_resp.status_code == 400


class TestAppealFlow:

    def test_appeal_resolved_incident(self, client, citizen_auth, officer_auth):
        resp = client.post("/complaints", json={
            "title": "Road cave-in dangerous for commuters",
            "description": "Road has caved in near the bus stop creating a deep hole",
            "location": "Mettupalayam Road, Sungam, Coimbatore",
            "ward": "1",
        }, headers=citizen_auth)
        complaint_id = resp.json()["complaintId"]
        category = _classify_complaint(client,
            "Road cave-in near bus stop Mettupalayam Road")
        db = SessionLocal()
        try:
            incident_id = _create_test_incident(db, complaint_id, category, "1")
        finally:
            db.close()

        client.patch(
            f"/incidents/{incident_id}/status",
            json={"status": "resolved", "resolution_note": "Road patched temporarily"},
            headers=officer_auth,
        )
        db = SessionLocal()
        try:
            inc = db.query(Incident).filter(Incident.id == incident_id).first()
            code = inc.verification_code
        finally:
            db.close()

        client.post(
            f"/incidents/{incident_id}/verify-resolution",
            json={"code": code},
            headers=citizen_auth,
        )

        appeal_resp = client.post(
            f"/incidents/{incident_id}/appeal",
            json={"reason": ("The road was only patched temporarily and has already caved in "
                             "again. Permanent repair needed urgently to prevent accidents.")},
            headers=citizen_auth,
        )
        assert appeal_resp.status_code == 200
        assert appeal_resp.json()["status"] == "open"
        assert appeal_resp.json()["appealed"] is True

        db = SessionLocal()
        try:
            inc = db.query(Incident).filter(Incident.id == incident_id).first()
            assert inc.appealed is True
            assert inc.appeal_reason is not None
            assert inc.status == "open"
        finally:
            db.close()

    def test_non_citizen_cannot_appeal(self, client, officer_auth):
        resp = client.post(
            f"/incidents/nonexistent/appeal",
            json={"reason": "This is a test appeal reason that is long enough to pass validation"},
            headers=officer_auth,
        )
        assert resp.status_code == 403


class TestPublicEndpoints:

    def test_track_nonexistent_complaint(self, client):
        resp = client.get("/track/DOES-NOT-EXIST-999")
        assert resp.status_code == 404

    def test_public_stats(self, client):
        resp = client.get("/public/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "totalComplaintsThisMonth" in data
        assert "resolutionRate" in data

    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
