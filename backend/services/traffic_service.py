"""DelhiMove AI - Traffic Monitoring & Prediction Service (Stage 5 & Stage 8)
Computes network-wide traffic conditions from real GTFS traffic segments,
live/snapshot vehicle observations, and ML travel-time predictions relative
to historical speeds.
"""

import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import sqlite3

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
ML_DIR = PROJECT_ROOT / "ml"
sys.path.insert(0, BACKEND_DIR.as_posix())
sys.path.insert(0, ML_DIR.as_posix())

from predict import get_predictor
from services.gtfs_service import get_gtfs_service, haversine_m
from services.vehicle_service import get_vehicle_service

class TrafficService:
    def __init__(self, db_path: Path = BACKEND_DIR / "delhi_move.db"):
        self.db_path = str(db_path)
        self.predictor = get_predictor()
        self.gtfs = get_gtfs_service()
        self.vehicle_service = get_vehicle_service()

    def get_network_overview(self) -> Dict[str, Any]:
        """Provides a high-level overview of Delhi bus network traffic conditions from live GPS, DB segments, and ML predictions."""
        vehicles_data = self.vehicle_service.get_live_vehicles(limit=10000)
        vehicles = vehicles_data.get("vehicles", [])

        moving_speeds = [v["speed_kmh"] for v in vehicles if v.get("speed_kmh") is not None and 2.0 <= v["speed_kmh"] <= 80.0]
        avg_speed = round(sum(moving_speeds) / len(moving_speeds), 1) if moving_speeds else 18.5

        congestion_counts = {"low": 0, "moderate": 0, "high": 0}
        for v in vehicles:
            c = v.get("congestion_level", "moderate")
            congestion_counts[c] = congestion_counts.get(c, 0) + 1

        total_v = max(1, len(vehicles))
        congestion_pct = {
            "low": round((congestion_counts["low"] / total_v) * 100, 1),
            "moderate": round((congestion_counts["moderate"] / total_v) * 100, 1),
            "high": round((congestion_counts["high"] / total_v) * 100, 1)
        }

        # Current IST time for ML segment evaluation
        ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        curr_hour = ist_now.hour
        curr_dow = ist_now.weekday()

        # Query real arterial inter-stop segments from SQLite
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT ts.segment_id, ts.distance_m, ts.historical_avg_speed,
                   s1.stop_name as from_stop, s2.stop_name as to_stop
            FROM traffic_segments ts
            JOIN stops s1 ON ts.from_stop_id = s1.stop_id
            JOIN stops s2 ON ts.to_stop_id = s2.stop_id
            WHERE ts.distance_m BETWEEN 900 AND 2800
            ORDER BY ts.segment_id ASC
            LIMIT 8
        """)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()

        key_corridors = []
        for r in rows:
            hist_speed = float(r["historical_avg_speed"] or 18.5)
            pred = self.predictor.predict_segment(
                distance_m=float(r["distance_m"]),
                hour=curr_hour,
                day_of_week=curr_dow,
                historical_speed_kmh=hist_speed
            )
            delay_min = round(max(0.0, (pred["predicted_duration_sec"] - pred["baseline_duration_sec"]) / 60.0), 1)
            key_corridors.append({
                "corridor_name": f"{r['from_stop']} ➔ {r['to_stop']}",
                "distance_km": round(r["distance_m"] / 1000.0, 2),
                "historical_kmh": round(hist_speed, 1),
                "current_kmh": pred["effective_speed_kmh"],
                "congestion": pred["congestion_level"],
                "delay_min": delay_min,
                "prediction_method": pred["prediction_method"]
            })

        return {
            "status": "success",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "evaluated_hour_ist": curr_hour,
            "is_live_gps": vehicles_data.get("is_live", False),
            "data_source": vehicles_data.get("source", "historical_dataset_snapshot"),
            "active_monitored_buses": len(vehicles),
            "average_network_speed_kmh": avg_speed,
            "congestion_distribution": congestion_pct,
            "congested_corridors": key_corridors,
            "traffic_state": "Heavy Peak" if congestion_pct["high"] > 30 else ("Moderate Flow" if congestion_pct["moderate"] > 35 else "Smooth Flow")
        }

    def predict_segment(
        self,
        distance_m: Optional[float] = None,
        from_stop_id: Optional[int] = None,
        to_stop_id: Optional[int] = None,
        hour: int = 9,
        day_of_week: int = 1
    ) -> Dict[str, Any]:
        """Predicts travel time for a specific distance or between two known GTFS stops."""
        from_stop_name = None
        to_stop_name = None

        if from_stop_id and to_stop_id:
            s_from = self.gtfs.get_stop_by_id(int(from_stop_id))
            s_to = self.gtfs.get_stop_by_id(int(to_stop_id))
            if s_from and s_to:
                from_stop_name = s_from["stop_name"]
                to_stop_name = s_to["stop_name"]
                distance_m = haversine_m(s_from["stop_lat"], s_from["stop_lon"], s_to["stop_lat"], s_to["stop_lon"])

        if distance_m is None or distance_m <= 0:
            distance_m = 1200.0

        pred = self.predictor.predict_segment(
            distance_m=distance_m,
            hour=hour,
            day_of_week=day_of_week
        )

        return {
            "status": "success",
            "from_stop_id": from_stop_id,
            "from_stop_name": from_stop_name,
            "to_stop_id": to_stop_id,
            "to_stop_name": to_stop_name,
            "distance_m": round(distance_m, 1),
            "hour": hour,
            "day_of_week": day_of_week,
            "prediction": pred
        }

# Global singleton
_traffic_service = None
def get_traffic_service() -> TrafficService:
    global _traffic_service
    if _traffic_service is None:
        _traffic_service = TrafficService()
    return _traffic_service
