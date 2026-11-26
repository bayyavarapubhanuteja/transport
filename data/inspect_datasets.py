"""DelhiMove AI - Dataset Schema and Format Inspection Script (Stage 1)
Inspects all available datasets, checks formats, column types, missing values,
and verifies schema properties before writing preprocessing and ML pipelines.
"""

import os
import sys
import json
from pathlib import Path
import duckdb
import pandas as pd

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
RAW_CSV = WORKSPACE_ROOT / "Bheedbus" / "data" / "raw" / "October-Delhi.csv"
PROCESSED_DIR = WORKSPACE_ROOT / "Bheedbus" / "data" / "processed"
OUTPUT_DIR = Path(__file__).resolve().parent / "processed"

def inspect_all():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    report = {
        "datasets": {},
        "summary": {}
    }

    print("=" * 80)
    print("DelhiMove AI - STAGE 1: Dataset Inspection & Schema Identification")
    print("=" * 80)

    # 1. Inspect Raw Ticket CSV
    if RAW_CSV.exists():
        print(f"\n[1/4] Inspecting Raw Dataset: {RAW_CSV.name} ({RAW_CSV.stat().st_size / (1024*1024):.1f} MB)...")
        # Column profile
        cols_df = con.execute(f"DESCRIBE SELECT * FROM read_csv_auto('{RAW_CSV.as_posix()}')").df()
        raw_stats = con.execute(f"""
            SELECT 
                COUNT(*) as total_rows,
                COUNT(passenger_count) as non_null_pax,
                COUNT(amount) as non_null_amount,
                COUNT(vehicle_number) as non_null_vehicle,
                COUNT(DISTINCT vehicle_number) as distinct_vehicles,
                COUNT(DISTINCT route) as distinct_routes,
                COUNT(DISTINCT start_stop_name) as distinct_start_stops,
                COUNT(DISTINCT end_stop_name) as distinct_end_stops,
                MIN(created_at) as min_timestamp,
                MAX(created_at) as max_timestamp,
                SUM(CASE WHEN is_ac = true THEN 1 ELSE 0 END) as ac_records,
                SUM(CASE WHEN is_ac = false THEN 1 ELSE 0 END) as non_ac_records
            FROM read_csv_auto('{RAW_CSV.as_posix()}')
        """).df().to_dict(orient="records")[0]

        sample_rows = con.execute(f"SELECT * FROM read_csv_auto('{RAW_CSV.as_posix()}') LIMIT 3").df().to_dict(orient="records")

        report["datasets"]["raw_tickets_csv"] = {
            "file": RAW_CSV.as_posix(),
            "columns": cols_df.to_dict(orient="records"),
            "stats": raw_stats,
            "sample": sample_rows
        }
        print(f"  ✓ Total records: {raw_stats['total_rows']:,}")
        print(f"  ✓ Unique bus routes: {raw_stats['distinct_routes']:,}")
        print(f"  ✓ Distinct vehicles observed: {raw_stats['distinct_vehicles']:,}")
        print(f"  ✓ Records with active vehicle IDs: {raw_stats['non_null_vehicle']:,} ({raw_stats['non_null_vehicle']/raw_stats['total_rows']*100:.1f}%)")
        print(f"  ✓ Date Range: {raw_stats['min_timestamp']} to {raw_stats['max_timestamp']}")

    # 2. Inspect tickets.parquet
    tickets_pq = PROCESSED_DIR / "tickets.parquet"
    if tickets_pq.exists():
        print(f"\n[2/4] Inspecting Processed Parquet: {tickets_pq.name}...")
        cols_df = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{tickets_pq.as_posix()}')").df()
        pq_stats = con.execute(f"""
            SELECT 
                COUNT(*) as total_rows,
                COUNT(DISTINCT route_raw) as distinct_routes,
                COUNT(DISTINCT route_base) as distinct_route_bases,
                COUNT(DISTINCT vehicle) as distinct_vehicles,
                COUNT(DISTINCT start_key) as distinct_stops,
                MIN(ts) as min_ts,
                MAX(ts) as max_ts
            FROM read_parquet('{tickets_pq.as_posix()}')
        """).df().to_dict(orient="records")[0]

        report["datasets"]["tickets_parquet"] = {
            "columns": cols_df.to_dict(orient="records"),
            "stats": pq_stats
        }
        print(f"  ✓ Cleaned tickets: {pq_stats['total_rows']:,}")
        print(f"  ✓ Distinct route variations: {pq_stats['distinct_routes']:,}")
        print(f"  ✓ Normalized base routes (e.g. 534, 717): {pq_stats['distinct_route_bases']:,}")

    # 3. Inspect stop_order_inferred.parquet
    stops_pq = PROCESSED_DIR / "stop_order_inferred.parquet"
    if stops_pq.exists():
        print(f"\n[3/4] Inspecting Inferred Stop Sequences: {stops_pq.name}...")
        cols_df = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{stops_pq.as_posix()}')").df()
        stops_stats = con.execute(f"""
            SELECT 
                COUNT(*) as total_stop_sequences,
                COUNT(DISTINCT route_raw) as routes_covered,
                COUNT(DISTINCT stop_key) as unique_stops,
                AVG(order_consistency) as mean_consistency
            FROM read_parquet('{stops_pq.as_posix()}')
        """).df().to_dict(orient="records")[0]

        report["datasets"]["stop_order_inferred"] = {
            "columns": cols_df.to_dict(orient="records"),
            "stats": stops_stats
        }
        print(f"  ✓ Total stop sequence links: {stops_stats['total_stop_sequences']:,}")
        print(f"  ✓ Covered routes: {stops_stats['routes_covered']:,}")
        print(f"  ✓ Unique bus stop names: {stops_stats['unique_stops']:,}")
        print(f"  ✓ Sequence order consistency: {stops_stats['mean_consistency']*100:.2f}%")

    # 4. Inspect crowding_profile.parquet
    crowd_pq = PROCESSED_DIR / "crowding_profile.parquet"
    if crowd_pq.exists():
        print(f"\n[4/4] Inspecting Crowding & Segment Load Profile: {crowd_pq.name}...")
        cols_df = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{crowd_pq.as_posix()}')").df()
        crowd_stats = con.execute(f"""
            SELECT 
                COUNT(*) as total_profile_rows,
                COUNT(DISTINCT route_raw) as routes,
                COUNT(DISTINCT hour) as hours_modeled,
                COUNT(DISTINCT day_group) as day_groups
            FROM read_parquet('{crowd_pq.as_posix()}')
        """).df().to_dict(orient="records")[0]

        report["datasets"]["crowding_profile"] = {
            "columns": cols_df.to_dict(orient="records"),
            "stats": crowd_stats
        }
        print(f"  ✓ Route segment-hour profiles: {crowd_stats['total_profile_rows']:,}")
        print(f"  ✓ Hours modeled: {crowd_stats['hours_modeled']} (5 AM to 11 PM)")

    # Save output report
    report_path = OUTPUT_DIR / "dataset_schema_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n✓ Stage 1 Inspection Complete. Saved report to: {report_path.relative_to(WORKSPACE_ROOT)}")

if __name__ == "__main__":
    inspect_all()
