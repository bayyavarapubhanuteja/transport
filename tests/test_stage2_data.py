"""Unit tests for Stage 2 - GTFS Data Import & Preprocessing."""

import os
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, BACKEND_DIR.as_posix())

from database.models import Stop, Route, Trip, StopTime, TrafficSegment
from database.connection import SessionLocal

def test_database_populated():
    db = SessionLocal()
    
    # 1. Verify stops count
    stops_count = db.query(Stop).count()
    assert stops_count > 6000, f"Expected > 6000 stops, got {stops_count}"

    # 2. Verify routes count
    routes_count = db.query(Route).count()
    assert routes_count > 2000, f"Expected > 2000 routes, got {routes_count}"

    # 3. Verify trips count
    trips_count = db.query(Trip).count()
    assert trips_count > 10000, f"Expected > 10000 trips, got {trips_count}"

    # 4. Verify stop times count
    st_count = db.query(StopTime).count()
    assert st_count > 100000, f"Expected > 100,000 stop times, got {st_count}"

    # 5. Check Delhi NCR coordinate boundaries
    sample_stops = db.query(Stop).limit(100).all()
    for s in sample_stops:
        assert 28.25 <= s.stop_lat <= 29.05, f"Stop lat out of Delhi bounds: {s.stop_lat}"
        assert 76.75 <= s.stop_lon <= 77.65, f"Stop lon out of Delhi bounds: {s.stop_lon}"

    db.close()

def test_shapes_summary_exists():
    shapes_path = PROJECT_ROOT / "data" / "processed" / "shapes_summary.json"
    assert shapes_path.exists(), "shapes_summary.json not found"
    assert shapes_path.stat().st_size > 1000, "shapes_summary.json is empty"
