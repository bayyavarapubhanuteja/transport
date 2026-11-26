"""Stage 5 Test Suite: Flask REST APIs
Verifies:
1. App healthcheck & root discovery endpoints.
2. Bus stops API (search & proximity).
3. Bus routes API (listing & route detail).
4. Live vehicle telemetry API.
5. Traffic overview & ML prediction API.
6. Multi-modal Journey Planning API.
7. Analytics & ML evaluation reporting API.
"""

import sys
import json
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, BACKEND_DIR.as_posix())

from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_health_and_root(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["db_exists"] is True
    assert data["model_ready"] is True

    root_res = client.get("/")
    assert root_res.status_code == 200
    root_data = root_res.get_json()
    assert "DelhiMove AI" in root_data["name"]

def test_stops_api(client):
    # Search stops
    res = client.get("/api/stops?q=Kashmere")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert len(data["stops"]) > 0
    first_stop = data["stops"][0]
    assert "stop_name" in first_stop

    # Stop detail
    stop_id = first_stop["stop_id"]
    detail_res = client.get(f"/api/stops/{stop_id}")
    assert detail_res.status_code == 200
    assert detail_res.get_json()["stop"]["stop_id"] == stop_id

def test_routes_api(client):
    res = client.get("/api/routes?limit=5")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert len(data["routes"]) > 0

    first_route_id = data["routes"][0]["route_id"]
    detail_res = client.get(f"/api/routes/{first_route_id}")
    assert detail_res.status_code == 200
    detail = detail_res.get_json()
    assert "stops" in detail["route"]
    assert "shape_coords" in detail["route"]

def test_vehicles_live_api(client):
    res = client.get("/api/vehicles/live?limit=10")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["count"] > 0
    first_v = data["vehicles"][0]
    assert "vehicle_id" in first_v
    assert "latitude" in first_v
    assert "longitude" in first_v
    assert "speed_kmh" in first_v

def test_traffic_api(client):
    # Overview
    res = client.get("/api/traffic/overview")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "average_network_speed_kmh" in data
    assert len(data["congested_corridors"]) > 0

    # Predict
    pred_res = client.get("/api/traffic/predict?distance_m=1200&hour=9&day_of_week=1")
    assert pred_res.status_code == 200
    pred_data = pred_res.get_json()
    assert pred_data["status"] == "success"
    assert "predicted_duration_sec" in pred_data["prediction"]
    assert pred_data["prediction"]["predicted_duration_sec"] > 0

def test_journey_plan_api(client):
    payload = {
        "source": "Rohini Sector 7",
        "destination": "Azadpur",
        "departure_time": "08:30",
        "day_of_week": 1
    }
    res = client.post("/api/journey/plan", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["journeys_count"] > 0
    top = data["journeys"][0]
    assert top["recommended"] is True
    assert top["total_duration_min"] > 0
    assert len(top["legs"]) > 0

def test_analytics_api(client):
    res = client.get("/api/analytics/overview")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["network_stats"]["total_routes"] > 2000
    assert data["network_stats"]["total_stops"] > 6000
    assert "random_forest" in data["ml_evaluation"]["models"]
    assert data["ml_evaluation"]["models"]["random_forest"]["mae_seconds"] < 15.0
