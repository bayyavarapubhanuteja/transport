"""DelhiMove AI - Stops Blueprint (Stage 5)
Endpoints for bus stop searching, spatial proximity lookups, and details.
"""

from flask import Blueprint, request, jsonify
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, BACKEND_DIR.as_posix())

from services.gtfs_service import get_gtfs_service

stops_bp = Blueprint("stops", __name__, url_prefix="/api/stops")

@stops_bp.route("", methods=["GET"])
def get_stops():
    """Returns bus stops matching a query string, near coordinates, or a default slice."""
    gtfs = get_gtfs_service()
    
    q = request.args.get("q", "").strip()
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    radius = request.args.get("radius", default=1500.0, type=float)
    limit = request.args.get("limit", default=50, type=int)

    if lat is not None and lon is not None:
        results = gtfs.find_nearest_stops(lat, lon, max_dist_m=radius, limit=min(limit, 100))
        return jsonify({
            "status": "success",
            "type": "nearby",
            "count": len(results),
            "stops": results
        })

    if q:
        results = gtfs.search_stops(q, limit=min(limit, 100))
        return jsonify({
            "status": "success",
            "type": "search",
            "query": q,
            "count": len(results),
            "stops": results
        })

    # Default: return representative top stops across Delhi
    all_stops = gtfs.get_all_stops(limit=min(limit, 200))
    return jsonify({
        "status": "success",
        "type": "all",
        "count": len(all_stops),
        "stops": all_stops
    })

@stops_bp.route("/<int:stop_id>", methods=["GET"])
def get_stop_detail(stop_id: int):
    """Returns detailed information for a single bus stop."""
    gtfs = get_gtfs_service()
    stop = gtfs.get_stop_by_id(stop_id)
    if not stop:
        return jsonify({"status": "error", "message": f"Stop {stop_id} not found"}), 404
    return jsonify({"status": "success", "stop": stop})
