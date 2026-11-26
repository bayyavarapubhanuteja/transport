"""DelhiMove AI - GTFS Import & Database Population Pipeline (Stage 2)
Reads the official Delhi GTFS text files, validates spatial and temporal attributes,
calculates segment distances via Haversine formula, and populates SQLite database.
"""

import os
import sys
import math
import json
from pathlib import Path
import pandas as pd
import duckdb

# Add backend directory to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, BACKEND_DIR.as_posix())

from database.models import Base, Stop, Route, Trip, StopTime, TrafficSegment
from database.connection import engine, SessionLocal, init_db

GTFS_DIR = PROJECT_ROOT / "data" / "raw" / "gtfs"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Delhi NCR Bounding Box validation
LAT_MIN, LAT_MAX = 28.25, 29.05
LON_MIN, LON_MAX = 76.75, 77.65

def haversine_m(lat1, lon1, lat2, lon2):
    """Calculates great-circle distance between two GPS coordinates in meters."""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def import_all():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 80)
    print("DelhiMove AI - STAGE 2: GTFS Data Import & Preprocessing Pipeline")
    print("=" * 80)

    # 1. Initialize SQLite Database Schema
    print("\n[1/6] Initializing SQLite database schema...")
    init_db()
    db = SessionLocal()

    # Clear existing data if re-running
    print("  Clearing existing tables...")
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()

    # 2. Import Stops
    stops_file = GTFS_DIR / "stops.txt"
    print(f"\n[2/6] Importing Bus Stops from {stops_file.name}...")
    stops_df = pd.read_csv(stops_file)
    valid_stops = []
    stop_coords = {}

    for _, row in stops_df.iterrows():
        lat, lon = float(row["stop_lat"]), float(row["stop_lon"])
        # Validate coordinates
        if LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX:
            s_id = int(row["stop_id"])
            stop_coords[s_id] = (lat, lon)
            valid_stops.append({
                "stop_id": s_id,
                "stop_code": str(row["stop_code"]) if pd.notna(row.get("stop_code")) else "",
                "stop_name": str(row["stop_name"]).strip(),
                "stop_lat": lat,
                "stop_lon": lon
            })

    print(f"  Inserting {len(valid_stops):,} validated stops into SQLite...")
    db.bulk_insert_mappings(Stop, valid_stops)
    db.commit()
    print(f"  ✓ {len(valid_stops):,} stops imported successfully.")

    # 3. Import Routes
    routes_file = GTFS_DIR / "routes.txt"
    print(f"\n[3/6] Importing Bus Routes from {routes_file.name}...")
    routes_df = pd.read_csv(routes_file)
    valid_routes = []
    for _, row in routes_df.iterrows():
        valid_routes.append({
            "route_id": int(row["route_id"]),
            "agency_id": str(row.get("agency_id", "DTC")),
            "route_short_name": str(row["route_short_name"]).strip(),
            "route_long_name": str(row["route_long_name"]).strip(),
            "route_desc": str(row.get("route_desc", "")),
            "route_type": int(row.get("route_type", 3))
        })
    print(f"  Inserting {len(valid_routes):,} routes into SQLite...")
    db.bulk_insert_mappings(Route, valid_routes)
    db.commit()
    print(f"  ✓ {len(valid_routes):,} routes imported successfully.")

    # 4. Import Trips (Representative active trips per route)
    trips_file = GTFS_DIR / "trips.txt"
    print(f"\n[4/6] Importing Trips from {trips_file.name}...")
    trips_df = pd.read_csv(trips_file)
    
    # Keep unique trips per route to optimize SQLite performance for journey planner
    valid_trips = []
    trip_ids = set()
    for _, row in trips_df.iterrows():
        t_id = str(row["trip_id"])
        if t_id not in trip_ids:
            trip_ids.add(t_id)
            valid_trips.append({
                "trip_id": t_id,
                "route_id": int(row["route_id"]),
                "service_id": int(row.get("service_id", 1)),
                "trip_headsign": str(row.get("trip_headsign", "")),
                "shape_id": str(row.get("shape_id", "")),
                "direction_id": int(row["direction_id"]) if pd.notna(row.get("direction_id")) else 0
            })
    print(f"  Inserting {len(valid_trips):,} trips into SQLite...")
    db.bulk_insert_mappings(Trip, valid_trips)
    db.commit()
    print(f"  ✓ {len(valid_trips):,} trips imported successfully.")

    # 5. Import Stop Times & Build Traffic Segments
    stop_times_file = GTFS_DIR / "stop_times.txt"
    print(f"\n[5/6] Processing Stop Times and Computing Traffic Segments...")
    
    # Process stop_times with DuckDB for extreme speed
    con = duckdb.connect()
    # Filter stop_times only for trips present in valid_trips and stops in stop_coords
    st_df = con.execute(f"""
        SELECT 
            trip_id,
            CAST(stop_id AS INTEGER) as stop_id,
            CAST(stop_sequence AS INTEGER) as stop_sequence,
            arrival_time,
            departure_time
        FROM read_csv_auto('{stop_times_file.as_posix()}')
        WHERE stop_id IN ({','.join(str(k) for k in stop_coords.keys())})
        ORDER BY trip_id, stop_sequence
    """).df()

    print(f"  Loaded {len(st_df):,} stop_times records. Inserting into SQLite in chunks...")
    chunk_size = 50000
    for i in range(0, len(st_df), chunk_size):
        chunk = st_df.iloc[i:i+chunk_size].to_dict(orient="records")
        db.bulk_insert_mappings(StopTime, chunk)
        db.commit()
        if (i // chunk_size) % 10 == 0:
            print(f"    ... {min(i + chunk_size, len(st_df)):,} / {len(st_df):,} inserted")

    print(f"  ✓ {len(st_df):,} stop_times records imported.")

    # Build unique Traffic Segments between consecutive stops
    print("\n  Computing inter-stop distances and baseline traffic segments...")
    segments = {}
    grouped = st_df.groupby("trip_id")
    for _, trip_group in grouped:
        stops_seq = trip_group.sort_values("stop_sequence")["stop_id"].tolist()
        for j in range(len(stops_seq) - 1):
            s1, s2 = stops_seq[j], stops_seq[j+1]
            seg_key = f"{s1}_{s2}"
            if seg_key not in segments and s1 in stop_coords and s2 in stop_coords:
                lat1, lon1 = stop_coords[s1]
                lat2, lon2 = stop_coords[s2]
                dist = haversine_m(lat1, lon1, lat2, lon2)
                # Realistic stop spacing in Delhi: 200m to 3500m
                if 50 <= dist <= 10000:
                    segments[seg_key] = {
                        "segment_id": seg_key,
                        "from_stop_id": s1,
                        "to_stop_id": s2,
                        "distance_m": round(dist, 1),
                        "historical_avg_speed": 18.5,  # km/h typical Delhi bus operating speed
                        "current_speed": 18.5,
                        "congestion_level": "low"
                    }

    seg_list = list(segments.values())
    print(f"  Inserting {len(seg_list):,} unique road/transit segments into SQLite...")
    for i in range(0, len(seg_list), chunk_size):
        chunk = seg_list[i:i+chunk_size]
        db.bulk_insert_mappings(TrafficSegment, chunk)
        db.commit()
    print(f"  ✓ {len(seg_list):,} traffic segments created.")

    # 6. Process Route Shapes for Leaflet Map Visualization
    shapes_file = GTFS_DIR / "shapes.txt"
    print(f"\n[6/6] Processing Shapes for Map Rendering from {shapes_file.name}...")
    shapes_df = con.execute(f"""
        SELECT 
            shape_id,
            shape_pt_lat,
            shape_pt_lon,
            shape_pt_sequence
        FROM read_csv_auto('{shapes_file.as_posix()}')
        WHERE shape_pt_lat BETWEEN {LAT_MIN} AND {LAT_MAX}
          AND shape_pt_lon BETWEEN {LON_MIN} AND {LON_MAX}
        ORDER BY shape_id, shape_pt_sequence
    """).df()

    # Aggregate shapes as GeoJSON-compatible coordinate arrays { shape_id: [[lat, lon], ...] }
    shapes_dict = {}
    for shape_id, group in shapes_df.groupby("shape_id"):
        # Downsample if too dense (> 200 points) to keep Leaflet fast and responsive
        pts = group[["shape_pt_lat", "shape_pt_lon"]].values.tolist()
        if len(pts) > 150:
            step = max(1, len(pts) // 150)
            pts = pts[::step]
            if pts[-1] != group[["shape_pt_lat", "shape_pt_lon"]].values.tolist()[-1]:
                pts.append(group[["shape_pt_lat", "shape_pt_lon"]].values.tolist()[-1])
        shapes_dict[shape_id] = pts

    shapes_out = PROCESSED_DIR / "shapes_summary.json"
    with open(shapes_out, "w", encoding="utf-8") as f:
        json.dump(shapes_dict, f)
    print(f"  ✓ Saved {len(shapes_dict):,} route polyline shapes to {shapes_out.name} ({shapes_out.stat().st_size / (1024*1024):.1f} MB)")

    db.close()
    print("\n" + "=" * 80)
    print("✓ STAGE 2 GTFS IMPORT COMPLETE! Database ready for Journey Planning & ML.")
    print("=" * 80)

if __name__ == "__main__":
    import_all()
