"""DelhiMove AI - High-Performance Intelligent Journey Planning Engine (Stage 4)
Finds direct and connecting bus journeys across Delhi's 6,800+ stops,
integrates the Machine Learning traffic prediction model for segment travel times,
calculates total journey duration, walking, waiting, and transfer penalties,
and tags smart fastest recommendations.
"""

import sys
import math
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
ML_DIR = PROJECT_ROOT / "ml"
sys.path.insert(0, BACKEND_DIR.as_posix())
sys.path.insert(0, ML_DIR.as_posix())

from services.gtfs_service import get_gtfs_service, haversine_m
from predict import get_predictor

class JourneyService:
    def __init__(self, db_path: Path = BACKEND_DIR / "delhi_move.db"):
        self.db_path = str(db_path)
        self.gtfs = get_gtfs_service()
        self.predictor = get_predictor()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _resolve_location(self, loc_input: Any) -> Tuple[List[Dict], Dict]:
        """Resolves user input (coordinates, stop_id, or stop_name) into candidate transit stops with real walking distances."""
        if isinstance(loc_input, dict) and "lat" in loc_input and "lon" in loc_input:
            lat, lon = float(loc_input["lat"]), float(loc_input["lon"])
            name = loc_input.get("name", f"Location ({lat:.4f}, {lon:.4f})")
            stops = self.gtfs.find_nearest_stops(lat, lon, max_dist_m=1500, limit=6)
            loc_info = {"name": name, "lat": lat, "lon": lon, "is_coordinate": True}
            return stops, loc_info

        elif isinstance(loc_input, int) or (isinstance(loc_input, str) and loc_input.isdigit()):
            stop = self.gtfs.get_stop_by_id(int(loc_input))
            if stop:
                nearby = self.gtfs.find_nearest_stops(stop["stop_lat"], stop["stop_lon"], max_dist_m=800, limit=6)
                if not any(s["stop_id"] == stop["stop_id"] for s in nearby):
                    stop["distance_m"] = 0.0
                    stop["walk_time_min"] = 0.0
                    nearby.insert(0, stop)
                return nearby[:6], {"name": stop["stop_name"], "lat": stop["stop_lat"], "lon": stop["stop_lon"], "is_coordinate": False}
            return [], {"name": f"Stop {loc_input}", "lat": 28.6139, "lon": 77.2090, "is_coordinate": False}

        elif isinstance(loc_input, str):
            matched = self.gtfs.search_stops(loc_input, limit=6)
            if matched:
                ref = matched[0]
                nearby = self.gtfs.find_nearest_stops(ref["stop_lat"], ref["stop_lon"], max_dist_m=900, limit=6)
                seen_ids = {s["stop_id"] for s in nearby}
                for m in matched:
                    if m["stop_id"] not in seen_ids:
                        dist = haversine_m(ref["stop_lat"], ref["stop_lon"], m["stop_lat"], m["stop_lon"])
                        m["distance_m"] = round(dist, 1)
                        m["walk_time_min"] = round(dist / 75.0, 1)
                        nearby.append(m)
                        seen_ids.add(m["stop_id"])
                nearby.sort(key=lambda x: x["distance_m"])
                return nearby[:6], {"name": loc_input, "lat": ref["stop_lat"], "lon": ref["stop_lon"], "is_coordinate": False}
            return [], {"name": loc_input, "lat": 28.6139, "lon": 77.2090, "is_coordinate": False}

        return [], {"name": "Unknown", "lat": 28.6139, "lon": 77.2090, "is_coordinate": False}

    def plan_journey(
        self,
        source: Any,
        destination: Any,
        departure_time: str = "08:30",
        day_of_week: int = 1
    ) -> Dict[str, Any]:
        """Core intelligent journey planning engine."""
        try:
            dep_parts = departure_time.split(":")
            dep_hour, dep_min = int(dep_parts[0]), int(dep_parts[1])
        except Exception:
            dep_hour, dep_min = 9, 0
            departure_time = "09:00"

        # 1. Resolve source and destination candidate stops
        src_candidates, src_info = self._resolve_location(source)
        dst_candidates, dst_info = self._resolve_location(destination)

        if not src_candidates or not dst_candidates:
            return {
                "status": "error",
                "message": "Could not identify nearby bus stops for the selected location.",
                "source": src_info,
                "destination": dst_info,
                "journeys": []
            }

        conn = self._get_conn()
        cur = conn.cursor()

        raw_options = []
        seen_route_signatures = set()

        src_ids = [s["stop_id"] for s in src_candidates]
        dst_ids = [d["stop_id"] for d in dst_candidates]

        placeholders_src = ",".join(str(s) for s in src_ids)
        placeholders_dst = ",".join(str(d) for d in dst_ids)

        # 2. Discover Direct Bus Routes
        cur.execute(f"""
            SELECT 
                r.route_id,
                r.route_short_name,
                r.route_long_name,
                t.trip_id,
                t.shape_id,
                t.trip_headsign,
                st1.stop_id as board_stop_id,
                st1.stop_sequence as board_seq,
                st2.stop_id as alight_stop_id,
                st2.stop_sequence as alight_seq,
                (st2.stop_sequence - st1.stop_sequence) as n_stops
            FROM stop_times st1
            JOIN stop_times st2 ON st1.trip_id = st2.trip_id AND st1.stop_sequence < st2.stop_sequence
            JOIN trips t ON st1.trip_id = t.trip_id
            JOIN routes r ON t.route_id = r.route_id
            WHERE st1.stop_id IN ({placeholders_src})
              AND st2.stop_id IN ({placeholders_dst})
            ORDER BY n_stops ASC
            LIMIT 30
        """)

        direct_matches = [dict(row) for row in cur.fetchall()]

        for m in direct_matches:
            sig = f"direct_{m['route_short_name']}"
            if sig in seen_route_signatures:
                continue
            seen_route_signatures.add(sig)

            cur.execute("""
                SELECT st.stop_sequence, s.stop_id, s.stop_name, s.stop_lat, s.stop_lon
                FROM stop_times st
                JOIN stops s ON st.stop_id = s.stop_id
                WHERE st.trip_id = ? AND st.stop_sequence BETWEEN ? AND ?
                ORDER BY st.stop_sequence ASC
            """, (m["trip_id"], m["board_seq"], m["alight_seq"]))
            stops_in_leg = [dict(r) for r in cur.fetchall()]

            src_stop_info = next((s for s in src_candidates if s["stop_id"] == m["board_stop_id"]), src_candidates[0])
            dst_stop_info = next((d for d in dst_candidates if d["stop_id"] == m["alight_stop_id"]), dst_candidates[0])

            raw_options.append({
                "type": "direct",
                "transfers": 0,
                "src_stop": src_stop_info,
                "dst_stop": dst_stop_info,
                "legs": [{
                    "route_id": m["route_id"],
                    "route_short_name": m["route_short_name"],
                    "route_long_name": m["route_long_name"],
                    "trip_headsign": m["trip_headsign"],
                    "shape_id": m["shape_id"],
                    "board_stop": src_stop_info,
                    "alight_stop": dst_stop_info,
                    "stops": stops_in_leg
                }]
            })

        # 3. Discover 1-Transfer Connecting Routes (via Set Intersection of transfer hubs)
        if len(raw_options) < 5:
            # Downstream reachable stops from origin
            cur.execute(f"""
                SELECT DISTINCT st2.stop_id
                FROM stop_times st1
                JOIN stop_times st2 ON st1.trip_id = st2.trip_id AND st2.stop_sequence > st1.stop_sequence
                WHERE st1.stop_id IN ({placeholders_src})
            """)
            downstream = set(r[0] for r in cur.fetchall())

            # Upstream reachable stops to destination
            cur.execute(f"""
                SELECT DISTINCT st1.stop_id
                FROM stop_times st2
                JOIN stop_times st1 ON st1.trip_id = st2.trip_id AND st1.stop_sequence < st2.stop_sequence
                WHERE st2.stop_id IN ({placeholders_dst})
            """)
            upstream = set(r[0] for r in cur.fetchall())

            common_hubs = list(downstream.intersection(upstream))

            if common_hubs:
                hub_list = common_hubs[:25]
                hub_placeholders = ",".join(str(h) for h in hub_list)

                # Find Leg 1: Source -> Hub
                cur.execute(f"""
                    SELECT r.route_id, r.route_short_name, r.route_long_name, t.trip_id, t.shape_id, t.trip_headsign,
                           st1.stop_id as b_id, st1.stop_sequence as b_seq,
                           st2.stop_id as xfer_id, st2.stop_sequence as xfer_seq
                    FROM stop_times st1
                    JOIN stop_times st2 ON st1.trip_id = st2.trip_id AND st1.stop_sequence < st2.stop_sequence
                    JOIN trips t ON st1.trip_id = t.trip_id
                    JOIN routes r ON t.route_id = r.route_id
                    WHERE st1.stop_id IN ({placeholders_src}) AND st2.stop_id IN ({hub_placeholders})
                    ORDER BY (st2.stop_sequence - st1.stop_sequence) ASC
                    LIMIT 30
                """)
                leg1_rows = [dict(r) for r in cur.fetchall()]

                # Find Leg 2: Hub -> Destination
                cur.execute(f"""
                    SELECT r.route_id, r.route_short_name, r.route_long_name, t.trip_id, t.shape_id, t.trip_headsign,
                           st1.stop_id as xfer_id, st1.stop_sequence as xfer_seq,
                           st2.stop_id as a_id, st2.stop_sequence as a_seq
                    FROM stop_times st1
                    JOIN stop_times st2 ON st1.trip_id = st2.trip_id AND st1.stop_sequence < st2.stop_sequence
                    JOIN trips t ON st1.trip_id = t.trip_id
                    JOIN routes r ON t.route_id = r.route_id
                    WHERE st1.stop_id IN ({hub_placeholders}) AND st2.stop_id IN ({placeholders_dst})
                    ORDER BY (st2.stop_sequence - st1.stop_sequence) ASC
                    LIMIT 30
                """)
                leg2_rows = [dict(r) for r in cur.fetchall()]

                # Match connections
                for l1 in leg1_rows:
                    for l2 in leg2_rows:
                        if l1["xfer_id"] == l2["xfer_id"] and l1["route_short_name"] != l2["route_short_name"]:
                            sig = f"xfer_{l1['route_short_name']}_{l2['route_short_name']}"
                            if sig in seen_route_signatures:
                                continue
                            seen_route_signatures.add(sig)

                            # Fetch stops for leg 1
                            cur.execute("""
                                SELECT st.stop_sequence, s.stop_id, s.stop_name, s.stop_lat, s.stop_lon
                                FROM stop_times st JOIN stops s ON st.stop_id = s.stop_id
                                WHERE st.trip_id = ? AND st.stop_sequence BETWEEN ? AND ?
                                ORDER BY st.stop_sequence ASC
                            """, (l1["trip_id"], l1["b_seq"], l1["xfer_seq"]))
                            stops1 = [dict(r) for r in cur.fetchall()]

                            # Fetch stops for leg 2
                            cur.execute("""
                                SELECT st.stop_sequence, s.stop_id, s.stop_name, s.stop_lat, s.stop_lon
                                FROM stop_times st JOIN stops s ON st.stop_id = s.stop_id
                                WHERE st.trip_id = ? AND st.stop_sequence BETWEEN ? AND ?
                                ORDER BY st.stop_sequence ASC
                            """, (l2["trip_id"], l2["xfer_seq"], l2["a_seq"]))
                            stops2 = [dict(r) for r in cur.fetchall()]

                            xfer_stop = self.gtfs.get_stop_by_id(l1["xfer_id"])
                            src_stop_info = next((s for s in src_candidates if s["stop_id"] == l1["b_id"]), src_candidates[0])
                            dst_stop_info = next((d for d in dst_candidates if d["stop_id"] == l2["a_id"]), dst_candidates[0])

                            raw_options.append({
                                "type": "transfer",
                                "transfers": 1,
                                "src_stop": src_stop_info,
                                "dst_stop": dst_stop_info,
                                "transfer_stop": xfer_stop,
                                "legs": [
                                    {
                                        "route_id": l1["route_id"],
                                        "route_short_name": l1["route_short_name"],
                                        "route_long_name": l1["route_long_name"],
                                        "trip_headsign": l1["trip_headsign"],
                                        "shape_id": l1["shape_id"],
                                        "board_stop": src_stop_info,
                                        "alight_stop": xfer_stop,
                                        "stops": stops1
                                    },
                                    {
                                        "route_id": l2["route_id"],
                                        "route_short_name": l2["route_short_name"],
                                        "route_long_name": l2["route_long_name"],
                                        "trip_headsign": l2["trip_headsign"],
                                        "shape_id": l2["shape_id"],
                                        "board_stop": xfer_stop,
                                        "alight_stop": dst_stop_info,
                                        "stops": stops2
                                    }
                                ]
                            })
                            if len(raw_options) >= 8:
                                break
                    if len(raw_options) >= 8:
                        break

        conn.close()

        # 4. Score each journey using the Machine Learning Prediction Engine
        journeys = []
        for idx, opt in enumerate(raw_options):
            initial_walk_m = opt["src_stop"].get("distance_m", 0.0)
            initial_walk_min = initial_walk_m / 75.0  # 4.5 km/h

            final_walk_m = opt["dst_stop"].get("distance_m", 0.0)
            final_walk_min = final_walk_m / 75.0

            total_bus_time_min = 0.0
            total_bus_dist_m = 0.0
            total_baseline_time_min = 0.0
            leg_details = []
            overall_congestion_levels = []
            leg_conf_scores = []
            leg_ml_coverages = []

            base_wait_min = 4.0 if dep_hour in (8, 9, 10, 17, 18, 19) else 7.0
            transfer_wait_min = 8.0 if opt["transfers"] > 0 else 0.0

            dep_dt = datetime.strptime(departure_time, "%H:%M")
            cursor_min = initial_walk_min + base_wait_min

            for leg_idx, leg in enumerate(opt["legs"]):
                if leg_idx > 0:
                    cursor_min += transfer_wait_min

                stops = leg["stops"]
                segment_distances = []
                traffic_segments = []

                for k in range(len(stops) - 1):
                    s_from = stops[k]
                    s_to = stops[k+1]
                    dist = haversine_m(s_from["stop_lat"], s_from["stop_lon"], s_to["stop_lat"], s_to["stop_lon"])
                    dist = max(80.0, dist)
                    segment_distances.append(dist)

                    # ML Prediction for this segment
                    seg_pred = self.predictor.predict_segment(
                        distance_m=dist,
                        hour=dep_hour,
                        day_of_week=day_of_week
                    )
                    traffic_segments.append({
                        "from_stop": s_from["stop_name"],
                        "to_stop": s_to["stop_name"],
                        "from_coords": [s_from["stop_lat"], s_from["stop_lon"]],
                        "to_coords": [s_to["stop_lat"], s_to["stop_lon"]],
                        "distance_m": round(dist, 1),
                        "duration_sec": seg_pred["predicted_duration_sec"],
                        "baseline_sec": seg_pred["baseline_duration_sec"],
                        "effective_speed_kmh": seg_pred["effective_speed_kmh"],
                        "congestion_level": seg_pred["congestion_level"],
                        "prediction_method": seg_pred["prediction_method"]
                    })
                    overall_congestion_levels.append(seg_pred["congestion_level"])
                    total_baseline_time_min += seg_pred["baseline_duration_sec"] / 60.0

                # ML Batch Prediction for entire leg
                leg_ml = self.predictor.predict_journey(segment_distances, hour=dep_hour, day_of_week=day_of_week)
                leg_time_min = leg_ml["total_duration_min"]
                leg_dist_m = leg_ml["total_distance_m"]
                leg_conf_scores.append(leg_ml.get("confidence_score", 0.85))
                leg_ml_coverages.append(leg_ml.get("ml_coverage_pct", 100.0))

                board_dt = dep_dt + timedelta(minutes=round(cursor_min))
                alight_dt = board_dt + timedelta(minutes=math.ceil(leg_time_min))
                cursor_min += leg_time_min

                total_bus_time_min += leg_time_min
                total_bus_dist_m += leg_dist_m

                # Polyline shape for Leaflet map
                shape_coords = self.gtfs.get_shape(leg.get("shape_id", ""))
                if not shape_coords:
                    shape_coords = [[s["stop_lat"], s["stop_lon"]] for s in stops]

                leg_details.append({
                    "leg_number": leg_idx + 1,
                    "route_id": leg["route_id"],
                    "route_short_name": leg["route_short_name"],
                    "route_long_name": leg["route_long_name"],
                    "trip_headsign": leg["trip_headsign"],
                    "board_stop": leg["board_stop"]["stop_name"],
                    "board_stop_id": leg["board_stop"]["stop_id"],
                    "board_time": board_dt.strftime("%H:%M"),
                    "alight_stop": leg["alight_stop"]["stop_name"],
                    "alight_stop_id": leg["alight_stop"]["stop_id"],
                    "alight_time": alight_dt.strftime("%H:%M"),
                    "stops_count": len(stops),
                    "stops": stops,
                    "distance_km": round(leg_dist_m / 1000.0, 2),
                    "duration_min": round(leg_time_min, 1),
                    "prediction_method": leg_ml.get("prediction_method", "random_forest_regressor"),
                    "ml_coverage_pct": leg_ml.get("ml_coverage_pct", 100.0),
                    "traffic_segments": traffic_segments,
                    "shape_coords": shape_coords
                })

            total_walk_time_min = initial_walk_min + final_walk_min
            total_walk_dist_m = initial_walk_m + final_walk_m
            total_wait_time_min = base_wait_min + transfer_wait_min

            total_journey_min = round(total_walk_time_min + total_wait_time_min + total_bus_time_min, 1)

            arr_dt = dep_dt + timedelta(minutes=math.ceil(total_journey_min))
            arrival_time_str = arr_dt.strftime("%H:%M")

            if overall_congestion_levels.count("high") > len(overall_congestion_levels) * 0.3:
                journey_congestion = "high"
            elif overall_congestion_levels.count("moderate") > len(overall_congestion_levels) * 0.35:
                journey_congestion = "moderate"
            else:
                journey_congestion = "low"

            avg_conf_score = round(sum(leg_conf_scores) / len(leg_conf_scores), 2) if leg_conf_scores else 0.65
            avg_ml_cov = round(sum(leg_ml_coverages) / len(leg_ml_coverages), 1) if leg_ml_coverages else 0.0
            using_ml = avg_ml_cov > 0

            journeys.append({
                "journey_id": f"j_{idx+1}",
                "type": opt["type"],
                "transfers": opt["transfers"],
                "routes": [leg["route_short_name"] for leg in leg_details],
                "total_duration_min": total_journey_min,
                "departure_time": departure_time,
                "arrival_time": arrival_time_str,
                "initial_walk_m": round(initial_walk_m, 1),
                "initial_walk_min": round(initial_walk_min, 1),
                "final_walk_m": round(final_walk_m, 1),
                "final_walk_min": round(final_walk_min, 1),
                "walking_time_min": round(total_walk_time_min, 1),
                "walking_distance_m": round(total_walk_dist_m, 1),
                "waiting_time_min": round(total_wait_time_min, 1),
                "transfer_wait_min": round(transfer_wait_min, 1),
                "bus_travel_time_min": round(total_bus_time_min, 1),
                "baseline_duration_min": round(total_baseline_time_min + total_walk_time_min + total_wait_time_min, 1),
                "total_distance_km": round((total_bus_dist_m + total_walk_dist_m) / 1000.0, 2),
                "overall_congestion": journey_congestion,
                "prediction_method": "random_forest_regressor" if using_ml else "historical_baseline_fallback",
                "ml_coverage_pct": avg_ml_cov,
                "confidence": "high" if avg_conf_score >= 0.80 else "medium",
                "confidence_score": avg_conf_score,
                "reliability": "High Reliability" if avg_conf_score >= 0.80 else ("Moderate Reliability" if using_ml else "Baseline Fallback"),
                "confidence_reason": (
                    f"ML-predicted across {avg_ml_cov}% of segments (ensemble agreement {int(avg_conf_score * 100)}%)."
                ) if using_ml else "Historical average speed fallback (ML model unavailable).",
                "legs": leg_details,
                "recommended": False,
                "tags": []
            })

        # 5. Rank journeys by total duration & apply Add-on Smart Recommendations
        if journeys:
            journeys.sort(key=lambda j: (j["total_duration_min"], j["transfers"]))

            # Smart Fastest Recommendation
            journeys[0]["recommended"] = True
            journeys[0]["tags"].append("⚡ Fastest Journey")

            # Identify Direct / Fewest Transfers
            min_transfers = min(j["transfers"] for j in journeys)
            fewest_xfer = next((j for j in journeys if j["transfers"] == min_transfers), None)
            if fewest_xfer:
                label = "Direct Bus" if min_transfers == 0 else f"Fewest Transfers ({min_transfers})"
                if not fewest_xfer["recommended"]:
                    fewest_xfer["tags"].append(label)
                elif min_transfers == 0:
                    fewest_xfer["tags"].append("Direct Bus")

            # Shortest Walk
            min_walk = min(journeys, key=lambda j: j["walking_distance_m"])
            if min_walk != journeys[0] and min_walk["walking_distance_m"] < journeys[0]["walking_distance_m"]:
                min_walk["tags"].append("🚶 Shortest Walk")

            # Label remaining options as Alternative
            for j in journeys[1:]:
                if not j["tags"]:
                    j["tags"].append("Alternative Route")

        return {
            "status": "success",
            "departure_time": departure_time,
            "day_of_week": day_of_week,
            "source": src_info,
            "destination": dst_info,
            "journeys_count": len(journeys),
            "recommended_journey_id": journeys[0]["journey_id"] if journeys else None,
            "journeys": journeys
        }

# Global singleton
_journey_service = None
def get_journey_service() -> JourneyService:
    global _journey_service
    if _journey_service is None:
        _journey_service = JourneyService()
    return _journey_service
