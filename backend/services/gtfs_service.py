"""DelhiMove AI - GTFS Query and Spatial Transit Service (Stage 4)
Provides fast spatial stop search, route lookups, stop sequences, and map geometry.
"""

import math
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import sqlite3

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "backend" / "delhi_move.db"
SHAPES_PATH = PROJECT_ROOT / "data" / "processed" / "shapes_summary.json"

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000  # meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class GtfsService:
    def __init__(self, db_path: Path = DB_PATH, shapes_path: Path = SHAPES_PATH):
        self.db_path = str(db_path)
        self.shapes_path = Path(shapes_path)
        self._shapes_cache = None

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @property
    def shapes(self) -> Dict[str, List[List[float]]]:
        if self._shapes_cache is None:
            if self.shapes_path.exists():
                try:
                    with open(self.shapes_path, "r", encoding="utf-8") as f:
                        self._shapes_cache = json.load(f)
                except Exception:
                    self._shapes_cache = {}
            else:
                self._shapes_cache = {}
        return self._shapes_cache

    def get_all_stops(self, limit: int = 100) -> List[Dict]:
        """Returns all stops up to the requested limit."""
        return self.search_stops("", limit=limit)

    def search_stops(self, query: str = "", limit: int = 20) -> List[Dict]:
        """Searches stops by name or code."""
        conn = self._get_conn()
        cur = conn.cursor()
        q = f"%{query.strip().lower()}%" if query else "%"
        cur.execute("""
            SELECT stop_id, stop_code, stop_name, stop_lat, stop_lon
            FROM stops
            WHERE LOWER(stop_name) LIKE ? OR LOWER(stop_code) LIKE ?
            ORDER BY length(stop_name) ASC
            LIMIT ?
        """, (q, q, limit))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def get_stop_by_id(self, stop_id: int) -> Optional[Dict]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT stop_id, stop_code, stop_name, stop_lat, stop_lon FROM stops WHERE stop_id = ?", (stop_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def find_nearest_stops(self, lat: float, lon: float, max_dist_m: float = 2000, limit: int = 5) -> List[Dict]:
        """Finds nearest bus stops to given GPS coordinates."""
        conn = self._get_conn()
        cur = conn.cursor()
        # Bounding box filter for query efficiency
        deg = max_dist_m / 111000.0
        cur.execute("""
            SELECT stop_id, stop_code, stop_name, stop_lat, stop_lon
            FROM stops
            WHERE stop_lat BETWEEN ? AND ? AND stop_lon BETWEEN ? AND ?
        """, (lat - deg, lat + deg, lon - deg, lon + deg))
        candidates = cur.fetchall()
        conn.close()

        results = []
        for c in candidates:
            dist = haversine_m(lat, lon, c["stop_lat"], c["stop_lon"])
            if dist <= max_dist_m:
                d = dict(c)
                d["distance_m"] = round(dist, 1)
                d["walk_time_min"] = round(dist / 75.0, 1)  # standard ~4.5 km/h walking speed
                results.append(d)

        results.sort(key=lambda x: x["distance_m"])
        return results[:limit]

    def get_routes(self, query: str = "", limit: int = 50) -> List[Dict]:
        """Retrieves list of bus routes."""
        conn = self._get_conn()
        cur = conn.cursor()
        q = f"%{query.strip().lower()}%" if query else "%"
        cur.execute("""
            SELECT route_id, agency_id, route_short_name, route_long_name, route_desc, route_type
            FROM routes
            WHERE LOWER(route_short_name) LIKE ? OR LOWER(route_long_name) LIKE ?
            ORDER BY route_id ASC
            LIMIT ?
        """, (q, q, limit))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def get_route_details(self, route_id: int) -> Optional[Dict]:
        """Returns comprehensive route information with stop sequence and polyline shape."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT route_id, agency_id, route_short_name, route_long_name, route_desc
            FROM routes WHERE route_id = ?
        """, (route_id,))
        r = cur.fetchone()
        if not r:
            conn.close()
            return None

        route_info = dict(r)

        # Get representative trip for this route
        cur.execute("""
            SELECT trip_id, trip_headsign, shape_id, direction_id
            FROM trips WHERE route_id = ? LIMIT 1
        """, (route_id,))
        trip = cur.fetchone()

        stops_list = []
        shape_coords = []
        if trip:
            route_info["trip_headsign"] = trip["trip_headsign"]
            route_info["shape_id"] = trip["shape_id"]
            if trip["shape_id"] in self.shapes:
                shape_coords = self.shapes[trip["shape_id"]]

            # Fetch stop sequence
            cur.execute("""
                SELECT st.stop_sequence, s.stop_id, s.stop_name, s.stop_lat, s.stop_lon
                FROM stop_times st
                JOIN stops s ON st.stop_id = s.stop_id
                WHERE st.trip_id = ?
                ORDER BY st.stop_sequence ASC
            """, (trip["trip_id"],))
            stops_list = [dict(row) for row in cur.fetchall()]

        conn.close()
        route_info["stops_count"] = len(stops_list)
        route_info["stops"] = stops_list
        route_info["shape_coords"] = shape_coords
        return route_info

    def get_shape(self, shape_id: str) -> List[List[float]]:
        return self.shapes.get(shape_id, [])

_gtfs_service = None
def get_gtfs_service() -> GtfsService:
    global _gtfs_service
    if _gtfs_service is None:
        _gtfs_service = GtfsService()
    return _gtfs_service
