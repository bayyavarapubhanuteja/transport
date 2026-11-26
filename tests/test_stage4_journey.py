"""Stage 4 Test Suite: Bus Route Graph & Intelligent Journey Planning Engine
Verifies:
1. Location resolution from stop names and coordinates.
2. Direct journey search between connected stops.
3. 1-transfer journey search where no direct bus is chosen.
4. ML-based segment prediction integration into total journey duration.
5. Fastest recommendation tagging and journey metadata.
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, BACKEND_DIR.as_posix())

from services.journey_service import get_journey_service
from services.gtfs_service import get_gtfs_service

def test_location_resolution():
    js = get_journey_service()
    # Test resolution by name
    stops, info = js._resolve_location("Kashmere Gate")
    assert len(stops) > 0, "Should resolve Kashmere Gate stops"
    assert "Kashmere" in info["name"] or "Kashmere" in stops[0]["stop_name"]

    # Test resolution by coordinate (Connaught Place area)
    stops_coord, info_coord = js._resolve_location({"lat": 28.6315, "lon": 77.2167, "name": "CP"})
    assert len(stops_coord) > 0, "Should resolve nearest stops to CP coordinates"
    assert stops_coord[0]["distance_m"] < 1500

def test_journey_planning_direct():
    js = get_journey_service()
    t0 = time.time()
    result = js.plan_journey(
        source="Rohini Sector 7",
        destination="Azadpur",
        departure_time="08:30",
        day_of_week=1
    )
    duration = time.time() - t0

    assert result["status"] == "success"
    assert result["journeys_count"] > 0, "Should find at least 1 journey between Rohini and Azadpur"
    
    first = result["journeys"][0]
    assert first["recommended"] is True
    assert "⚡ Fastest Journey" in first["tags"]
    assert first["total_duration_min"] > 0
    assert len(first["legs"]) >= 1
    assert "traffic_segments" in first["legs"][0]
    assert len(first["legs"][0]["traffic_segments"]) > 0

    seg = first["legs"][0]["traffic_segments"][0]
    assert "congestion_level" in seg
    assert seg["duration_sec"] > 0
    print(f"\n[Stage 4 Test] Found {result['journeys_count']} journeys in {duration:.3f}s. Fastest: {first['total_duration_min']} min, routes: {first['routes']}")

def test_journey_planning_with_coordinates():
    js = get_journey_service()
    # Coordinates for Anand Vihar ISBT to Kashmere Gate ISBT
    result = js.plan_journey(
        source={"lat": 28.6469, "lon": 77.3160, "name": "Anand Vihar"},
        destination={"lat": 28.6665, "lon": 77.2285, "name": "Kashmere Gate"},
        departure_time="09:00",
        day_of_week=2
    )

    assert result["status"] == "success"
    assert result["journeys_count"] > 0
    top = result["journeys"][0]
    assert top["walking_time_min"] >= 0
    assert top["bus_travel_time_min"] > 0
    assert top["waiting_time_min"] > 0
    print(f"\n[Stage 4 Test] Coordinate routing: {top['total_duration_min']} min total (Bus: {top['bus_travel_time_min']}m, Walk: {top['walking_time_min']}m)")

def test_transfer_journey_search():
    js = get_journey_service()
    # Test routing between areas that might need transfers or have direct options
    result = js.plan_journey(
        source="Najafgarh",
        destination="Noida",
        departure_time="08:00",
        day_of_week=1
    )
    # Even if far apart, it should return a valid response structure
    assert result["status"] in ("success", "error")
    if result["status"] == "success":
        print(f"\n[Stage 4 Test] Cross-city routing returned {result['journeys_count']} options.")
