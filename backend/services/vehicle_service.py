"""DelhiMove AI - Vehicle Tracking & Telemetry Service (Stage 5 & Stage 7)
Connects to the authorized Delhi Transport GTFS-RT VehiclePositions.pb live feed
configured via backend environment variables (DELHI_TRANSPORT_API_KEY and
DELHI_TRANSPORT_API_URL). Parses real-time protobuf entities, maps GTFS route_ids
to Delhi route names, filters invalid coordinates/GPS spikes, and flags stale records.
Falls back cleanly to real historical observations only when the live feed is unavailable.
"""

import os
import sys
import time
import json
import sqlite3
import logging
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from google.transit import gtfs_realtime_pb2

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
ML_DIR = PROJECT_ROOT / "ml"
sys.path.insert(0, ML_DIR.as_posix())

load_dotenv(BACKEND_DIR / ".env")

from predict import get_predictor

SNAPSHOT_FILE = PROJECT_ROOT / "data" / "processed" / "historical_fleet_snapshot.json"
STALE_THRESHOLD_SEC = 300  # 5 minutes
LIVE_CACHE_TTL_SEC = 10    # Reuse upstream protobuf response within 10s
IST = timezone(timedelta(hours=5, minutes=30))

DELHI_BBOX = {
    "lat_min": 28.25,
    "lat_max": 29.05,
    "lon_min": 76.75,
    "lon_max": 77.65,
}


class VehicleService:
    def __init__(self, db_path: Path = BACKEND_DIR / "delhi_move.db"):
        self.db_path = str(db_path)
        self.api_key = os.getenv("DELHI_TRANSPORT_API_KEY", "").strip()
        self.api_url = os.getenv("DELHI_TRANSPORT_API_URL", "").strip()
        self.predictor = get_predictor()

        # Route lookup map from SQLite GTFS routes
        self.route_map: Dict[str, Dict[str, str]] = {}
        self._load_route_map()

        # Short-lived in-memory cache for live GTFS-RT parsed feed
        self._live_cache_ts: float = 0.0
        self._live_cache_vehicles: List[Dict[str, Any]] = []
        self._live_cache_header_ts: int = 0
        self._live_cache_stale_count: int = 0
        self._last_feed_error: Optional[str] = None

        # Historical fallback snapshot (only used if live GTFS-RT feed is unreachable)
        self.historical_snapshot: List[Dict[str, Any]] = []
        if SNAPSHOT_FILE.exists():
            try:
                with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
                    self.historical_snapshot = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load historical fleet snapshot: {e}")

    def _load_route_map(self):
        """Loads GTFS route_id -> route_short_name/long_name mapping."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("SELECT route_id, route_short_name, route_long_name FROM routes")
            for r_id, s_name, l_name in cur.fetchall():
                self.route_map[str(r_id)] = {
                    "route_short_name": s_name or str(r_id),
                    "route_long_name": l_name or s_name or "Delhi Bus Route",
                }
            conn.close()
        except Exception as e:
            logger.warning(f"Could not load GTFS route map: {e}")

    def _fetch_live_gtfs_rt(self) -> Optional[List[Dict[str, Any]]]:
        """Fetches and parses live VehiclePositions.pb from the authorized Transport Stack API."""
        has_key = bool(self.api_key and self.api_key != "your_authorized_production_api_key_here")
        if not has_key or not self.api_url:
            self._last_feed_error = "No authorized DELHI_TRANSPORT_API_KEY configured in backend .env."
            return None

        now = time.time()
        if self._live_cache_vehicles and (now - self._live_cache_ts) < LIVE_CACHE_TTL_SEC:
            return self._live_cache_vehicles

        try:
            resp = requests.get(
                self.api_url,
                headers={
                    "x-api-key": self.api_key,
                },
                timeout=15.0,
            )
            if resp.status_code != 200:
                self._last_feed_error = f"GTFS-RT endpoint returned HTTP {resp.status_code}."
                return None

            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(resp.content)

            header_ts = int(feed.header.timestamp) if feed.header.timestamp else int(now)
            parsed: List[Dict[str, Any]] = []
            stale_count = 0

            for entity in feed.entity:
                if not entity.HasField("vehicle"):
                    continue
                v = entity.vehicle
                if not v.HasField("position"):
                    continue

                lat = float(v.position.latitude)
                lon = float(v.position.longitude)

                # Filter invalid coordinates outside Delhi NCR
                if not (
                    DELHI_BBOX["lat_min"] <= lat <= DELHI_BBOX["lat_max"]
                    and DELHI_BBOX["lon_min"] <= lon <= DELHI_BBOX["lon_max"]
                ):
                    continue

                veh_id = (v.vehicle.id or v.vehicle.label or entity.id or "").strip()
                if not veh_id:
                    continue

                raw_route_id = str(v.trip.route_id or "").strip()
                r_meta = self.route_map.get(raw_route_id, {})
                route_short = r_meta.get("route_short_name", raw_route_id or "DTC")
                route_long = r_meta.get("route_long_name", "Delhi Bus Corridor")

                # GTFS-RT speed is in m/s; filter unrealistic GPS speed spikes (> 80 km/h)
                raw_speed_ms = float(v.position.speed) if v.position.speed else 0.0
                speed_kmh = round(raw_speed_ms * 3.6, 1)
                gps_jump_filtered = False
                if speed_kmh > 80.0:
                    speed_kmh = 0.0
                    gps_jump_filtered = True

                # Classify congestion based on observed speed relative to Delhi 18.5 km/h historical norm
                if speed_kmh >= 19.5:
                    congestion = "low"
                elif speed_kmh >= 12.0:
                    congestion = "moderate"
                else:
                    congestion = "high"

                v_ts = int(v.timestamp) if v.timestamp else header_ts
                # Compare against feed header timestamp and current time to flag stale GPS records
                age_from_now = max(0, int(now) - v_ts)
                age_from_header = max(0, header_ts - v_ts)
                is_stale = (age_from_now > STALE_THRESHOLD_SEC) and (age_from_header > STALE_THRESHOLD_SEC)
                if is_stale:
                    stale_count += 1

                ts_iso = datetime.fromtimestamp(v_ts, tz=IST).isoformat(timespec="seconds")
                is_ev = "EV" in veh_id.upper()

                parsed.append({
                    "vehicle_id": veh_id,
                    "route_id": raw_route_id,
                    "route_short_name": route_short,
                    "route_long_name": route_long,
                    "trip_id": str(v.trip.trip_id or ""),
                    "start_time": str(v.trip.start_time or ""),
                    "latitude": round(lat, 6),
                    "longitude": round(lon, 6),
                    "speed_kmh": speed_kmh,
                    "bearing": round(float(v.position.bearing or 0.0), 1),
                    "congestion_level": congestion,
                    "is_electric": is_ev,
                    "agency": "DTC Electric" if is_ev else "DTC / DIMTS",
                    "last_updated": ts_iso,
                    "timestamp_unix": v_ts,
                    "is_stale": is_stale,
                    "gps_jump_filtered": gps_jump_filtered,
                    "is_live": True,
                    "data_source": "authorized_gtfs_rt_feed",
                })

            self._live_cache_ts = now
            self._live_cache_vehicles = parsed
            self._live_cache_header_ts = header_ts
            self._live_cache_stale_count = stale_count
            self._last_feed_error = None
            return parsed

        except Exception as e:
            self._last_feed_error = str(e)
            logger.warning(f"Authorized GTFS-RT feed request failed: {e}")
            return None

    def get_fleet_summary(self) -> Dict[str, Any]:
        """Provides consistent fleet counts across Live Tracking and Analytics pages."""
        has_key = bool(self.api_key and self.api_key != "your_authorized_production_api_key_here")
        live_vehicles = self._fetch_live_gtfs_rt()
        if live_vehicles is not None:
            return {
                "registered_vehicle_fleet": 6810,
                "active_live_buses": len(live_vehicles),
                "stale_count": self._live_cache_stale_count,
                "live_feed_configured": True,
                "is_live": True,
                "feed_source": "authorized_gtfs_rt_feed",
            }
        return {
            "registered_vehicle_fleet": 6810,
            "active_live_buses": len(self.historical_snapshot),
            "stale_count": len(self.historical_snapshot),
            "live_feed_configured": has_key,
            "is_live": False,
            "feed_source": "historical_dataset_snapshot",
        }

    def get_live_vehicles(self, route_id: Optional[str] = None, limit: int = 150) -> Dict[str, Any]:
        """Fetches vehicles from authorized GTFS-RT VehiclePositions.pb; falls back cleanly if unavailable."""
        live_vehicles = self._fetch_live_gtfs_rt()

        if live_vehicles is not None:
            filtered = []
            for v in live_vehicles:
                if route_id:
                    q = str(route_id).strip().lower()
                    if v["route_short_name"].lower() != q and str(v["route_id"]).lower() != q:
                        continue
                filtered.append(v)

            sliced = filtered[:limit]
            stale_in_slice = sum(1 for v in sliced if v["is_stale"])
            header_iso = datetime.fromtimestamp(self._live_cache_header_ts, tz=IST).isoformat(timespec="seconds")

            return {
                "status": "success",
                "feed_status": "live",
                "is_live": True,
                "source": "authorized_gtfs_rt_feed",
                "feed_message": f"Connected to live Delhi Buses GTFS-RT feed ({len(live_vehicles):,} active vehicles streaming).",
                "feed_timestamp": header_iso,
                "total_active_live": len(live_vehicles),
                "total_matching": len(filtered),
                "count": len(sliced),
                "stale_count": stale_in_slice,
                "total_registered_fleet": 6810,
                "vehicles": sliced,
            }

        # Fallback when authorized live GTFS-RT feed is unreachable
        reason = self._last_feed_error or "Authorized live GPS feed unreachable."
        vehicles = []
        for item in self.historical_snapshot:
            if route_id and item["route_short_name"] != route_id and str(item["route_id"]) != str(route_id):
                continue

            ts_str = item.get("last_updated", "")
            rec_hour = 10
            rec_dow = 2
            try:
                dt = datetime.fromisoformat(ts_str)
                rec_hour = dt.hour
                rec_dow = dt.weekday()
            except Exception:
                pass

            seg_est = self.predictor.predict_segment(distance_m=1000.0, hour=rec_hour, day_of_week=rec_dow)
            vehicles.append({
                "vehicle_id": item["vehicle_id"],
                "route_id": item["route_id"],
                "route_short_name": item["route_short_name"],
                "route_long_name": item["route_long_name"],
                "latitude": item["latitude"],
                "longitude": item["longitude"],
                "last_stop_name": item.get("last_stop_name", ""),
                "speed_kmh": seg_est["effective_speed_kmh"],
                "congestion_level": seg_est["congestion_level"],
                "is_electric": item["is_electric"],
                "agency": item["agency"],
                "last_updated": ts_str,
                "is_stale": True,
                "is_live": False,
                "data_source": "historical_dataset_snapshot",
            })
            if len(vehicles) >= limit:
                break

        return {
            "status": "success",
            "feed_status": "unavailable",
            "is_live": False,
            "source": "historical_dataset_snapshot",
            "feed_message": f"{reason} Displaying {len(vehicles)} real historical bus observations from October-Delhi.csv (marked stale).",
            "total_active_live": len(vehicles),
            "total_matching": len(vehicles),
            "count": len(vehicles),
            "stale_count": len(vehicles),
            "total_registered_fleet": 6810,
            "vehicles": vehicles,
        }

    def get_vehicle_by_id(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        """Look up a single live vehicle by registration ID across the entire live fleet."""
        live = self.get_live_vehicles(limit=10000)
        for v in live["vehicles"]:
            if v["vehicle_id"].lower() == vehicle_id.lower():
                return v
        return None


# Global singleton
_vehicle_service = None


def get_vehicle_service() -> VehicleService:
    global _vehicle_service
    if _vehicle_service is None:
        _vehicle_service = VehicleService()
    return _vehicle_service
