"""DelhiMove AI - Buses & Vehicles Blueprint (Stage 5 & Stage 7)
Endpoints for bus routes, route geometry, stop sequences, and live vehicle tracking.
"""

from flask import Blueprint, request, jsonify
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, BACKEND_DIR.as_posix())

from services.gtfs_service import get_gtfs_service
from services.vehicle_service import get_vehicle_service

buses_bp = Blueprint("buses", __name__, url_prefix="/api")

@buses_bp.route("/routes", methods=["GET"])
def get_routes():
    """Returns available bus routes in Delhi."""
    gtfs = get_gtfs_service()
    q = request.args.get("q", "").strip()
    limit = request.args.get("limit", default=100, type=int)

    routes = gtfs.get_routes(query=q, limit=min(limit, 500))
    return jsonify({
        "status": "success",
        "count": len(routes),
        "routes": routes
    })

@buses_bp.route("/routes/<route_id>", methods=["GET"])
def get_route_details(route_id: str):
    """Returns route metadata, stop sequence, and polyline shape coordinates."""
    gtfs = get_gtfs_service()
    details = gtfs.get_route_details(route_id)
    if not details:
        return jsonify({"status": "error", "message": f"Route '{route_id}' not found"}), 404
    return jsonify({"status": "success", "route": details})

@buses_bp.route("/vehicles/live", methods=["GET"])
def get_live_vehicles():
    """Returns real-time vehicle positions, speed, and heading."""
    vehicle_svc = get_vehicle_service()
    route_id = request.args.get("route_id", "").strip() or None
    limit = request.args.get("limit", default=150, type=int)

    data = vehicle_svc.get_live_vehicles(route_id=route_id, limit=limit)
    return jsonify(data)

@buses_bp.route("/vehicles/<vehicle_id>", methods=["GET"])
def get_vehicle_detail(vehicle_id: str):
    """Returns real-time telemetry for a single vehicle."""
    vehicle_svc = get_vehicle_service()
    veh = vehicle_svc.get_vehicle_by_id(vehicle_id)
    if not veh:
        return jsonify({"status": "error", "message": f"Vehicle '{vehicle_id}' not currently active or found"}), 404
    return jsonify({"status": "success", "vehicle": veh})
