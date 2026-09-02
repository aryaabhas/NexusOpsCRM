import os

import pytest
import routers.crm as crm_router
from fastapi.testclient import TestClient
from main import app
from middleware.firebase_auth import get_current_user

# Redirect interactions database to test data directory
crm_router.INTERACTIONS_FILE = os.path.join(os.environ["VECTOR_STORE_DIR"], "crm_interactions_test.json")

# Mock authentication
def mock_get_current_user():
    return {"uid": "test_agent_123", "email": "agent@nexusopscrm.com"}

app.dependency_overrides[get_current_user] = mock_get_current_user

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_interactions_file():
    if os.path.exists(crm_router.INTERACTIONS_FILE):
        os.remove(crm_router.INTERACTIONS_FILE)
    yield
    if os.path.exists(crm_router.INTERACTIONS_FILE):
        os.remove(crm_router.INTERACTIONS_FILE)

def test_add_and_get_crm_interactions():
    # 1. Verify interactions start empty
    res = client.get("/api/crm/interactions?client_email=customer@scaletech.com")
    assert res.status_code == 200
    assert len(res.json()["interactions"]) == 0
    
    # 2. Log a new touchpoint without grievance
    payload = {
        "client_email": "customer@scaletech.com",
        "date": "2026-08-17",
        "topic": "Followup call",
        "outcome": "Customer is happy, discussed feature updates",
        "has_grievance": False
    }
    res = client.post("/api/crm/interactions", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["interaction"]["topic"] == "Followup call"
    interaction_id = data["interaction"]["id"]
    
    # 3. Retrieve interactions list
    res = client.get("/api/crm/interactions?client_email=customer@scaletech.com")
    assert res.status_code == 200
    interactions = res.json()["interactions"]
    assert len(interactions) == 1
    assert interactions[0]["id"] == interaction_id
    assert interactions[0]["has_grievance"] is False

def test_crm_analytics_grievances():
    # 1. Post touchpoint with grievance
    payload1 = {
        "client_email": "angry_client@figmalabs.com",
        "date": "2026-08-17",
        "topic": "Complaint call",
        "outcome": "Client complained about billing error",
        "has_grievance": True
    }
    res1 = client.post("/api/crm/interactions", json=payload1)
    assert res1.status_code == 200
    
    # 2. Verify analytics registers 1 active grievance
    res_analytics = client.get("/api/crm/analytics")
    assert res_analytics.status_code == 200
    analytics = res_analytics.json()
    assert analytics["active_grievances"] == 1
    assert "angry_client@figmalabs.com" in analytics["grievance_emails"]
    
    # 3. Log a resolving touchpoint for same client
    payload2 = {
        "client_email": "angry_client@figmalabs.com",
        "date": "2026-08-17",
        "topic": "Resolved bill",
        "outcome": "Corrected invoice and applied credit",
        "has_grievance": False
    }
    res2 = client.post("/api/crm/interactions", json=payload2)
    assert res2.status_code == 200
    
    # 4. Verify analytics registers 0 active grievances now
    res_analytics2 = client.get("/api/crm/analytics")
    assert res_analytics2.json()["active_grievances"] == 0
    assert "angry_client@figmalabs.com" not in res_analytics2.json()["grievance_emails"]

def test_edit_crm_interaction():
    # 1. Create touchpoint
    payload = {
        "client_email": "edit_client@test.com",
        "date": "2026-08-17",
        "topic": "Initial touch",
        "outcome": "Spoke briefly",
        "has_grievance": False
    }
    res = client.post("/api/crm/interactions", json=payload)
    int_id = res.json()["interaction"]["id"]
    
    # 2. Edit touchpoint
    updated_payload = {
        "client_email": "edit_client@test.com",
        "date": "2026-08-17",
        "topic": "Updated touch",
        "outcome": "Spoke at length, logged grievance",
        "has_grievance": True
    }
    res_put = client.put(f"/api/crm/interactions/{int_id}", json=updated_payload)
    assert res_put.status_code == 200
    assert res_put.json()["interaction"]["topic"] == "Updated touch"
    assert res_put.json()["interaction"]["has_grievance"] is True
    
    # 3. Verify analytics updated
    res_analytics = client.get("/api/crm/analytics")
    assert res_analytics.json()["active_grievances"] == 1
