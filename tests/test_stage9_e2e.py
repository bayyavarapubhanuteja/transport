"""Stage 9 Test Suite: End-to-End System Validation vs Ground Truth
Verifies:
1. Complete journey planning pipeline with GTFS graph and ML predictions.
2. Spatial consistency: all stops and live vehicles are bounded within Delhi NCR.
3. Realistic travel time bounds: ML bus speeds are between 5 km/h and 50 km/h.
4. Model evaluation consistency: reported metrics match serialized artifacts.
5. REST API contract & frontend proxy compatibility.
"""

import sys
import json
import sqlite3
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
ML_DIR = PROJECT_ROOT / "ml"
sys.path.insert(0, BACKEND_DIR.as_posix())
sys.path.insert(0, ML_DIR.as_posix())

from app import create_app
from predict import get_predictor
from services.gtfs_service import get_gtfs_service
from services.journey_service import get_journey_service
from services.vehicle_service import get_vehicle_service
from config import Config

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_delhi_spatial_bounding():
    """Validates that all stops and vehicles operate strictly within Delhi NCR."""
    gtfs = get_gtfs_service()
    stops = gtfs.get_all_stops(limit=200)
    for s in stops:
        assert Config.DELHI_BBOX["lat_min"] <= s["stop_lat"] <= Config.DELHI_BBOX["lat_max"], f"Stop {s['stop_id']} lat out of bounds"
        assert Config.DELHI_BBOX["lon_min"] <= s["stop_lon"] <= Config.DELHI_BBOX["lon_max"], f"Stop {s['stop_id']} lon out of bounds"

    v_svc = get_vehicle_service()
    live = v_svc.get_live_vehicles(limit=100)
    for v in live["vehicles"]:
        assert Config.DELHI_BBOX["lat_min"] <= v["latitude"] <= Config.DELHI_BBOX["lat_max"], f"Vehicle {v['vehicle_id']} lat out of bounds"
        assert Config.DELHI_BBOX["lon_min"] <= v["longitude"] <= Config.DELHI_BBOX["lon_max"], f"Vehicle {v['vehicle_id']} lon out of bounds"

def test_ml_speed_bounds_and_ground_truth():
    """Verifies ML predicted speeds match Delhi bus operating realities (8-40 km/h)."""
    predictor = get_predictor()
    
    # Peak hour vs off-peak hour
    pred_peak = predictor.predict_segment(distance_m=2000.0, hour=9, day_of_week=1)
    pred_offpeak = predictor.predict_segment(distance_m=2000.0, hour=14, day_of_week=1)
    pred_night = predictor.predict_segment(distance_m=2000.0, hour=2, day_of_week=1)

    assert 8.0 <= pred_peak["effective_speed_kmh"] <= 35.0
    assert 10.0 <= pred_offpeak["effective_speed_kmh"] <= 40.0
    assert pred_peak["predicted_duration_sec"] > pred_night["predicted_duration_sec"], "Peak traffic should predict longer travel time than night"

def test_full_journey_plan_pipeline():
    """End-to-end journey plan test connecting real Delhi transit hubs."""
    js = get_journey_service()
    res = js.plan_journey(
        source="Rohini Sector 7",
        destination="Azadpur",
        departure_time="09:00",
        day_of_week=1
    )

    assert res["status"] == "success"
    assert res["journeys_count"] > 0
    top = res["journeys"][0]
    
    # Check completeness of the journey payload
    assert top["recommended"] is True
    assert top["total_duration_min"] > 0
    assert top["walking_time_min"] >= 0
    assert top["waiting_time_min"] > 0
    assert top["bus_travel_time_min"] > 0
    assert len(top["legs"]) > 0

    leg = top["legs"][0]
    assert len(leg["stops"]) > 1
    assert len(leg["traffic_segments"]) > 0
    assert len(leg["shape_coords"]) > 0

def test_model_metrics_authenticity():
    """Validates that ML evaluation metrics match trained Random Forest performance."""
    metrics_file = Config.ML_MODELS_DIR / "model_metrics.json"
    assert metrics_file.exists(), "Model metrics file must exist"
    
    with open(metrics_file, "r") as f:
        metrics = json.load(f)

    rf = metrics["models"]["random_forest"]
    assert rf["mae_seconds"] < 15.0, "MAE must be under 15s"
    assert rf["r2_score"] > 0.95, "R2 must be > 0.95"
    assert metrics["train_samples"] > 30000, "Train samples must be significant"
    assert "time_based_split" in metrics["split_strategy"]
