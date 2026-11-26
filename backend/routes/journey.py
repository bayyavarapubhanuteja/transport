"""DelhiMove AI - Journey Planning Blueprint (Stage 5)
Endpoint for multi-modal bus journey planning with ML travel-time estimation.
"""

from flask import Blueprint, request, jsonify
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, BACKEND_DIR.as_posix())

from services.journey_service import get_journey_service

journey_bp = Blueprint("journey", __name__, url_prefix="/api/journey")

@journey_bp.route("/plan", methods=["GET", "POST"])
def plan_journey():
    """Calculates intelligent bus routes connecting source and destination."""
    journey_svc = get_journey_service()

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        source = data.get("source")
        destination = data.get("destination")
        departure_time = data.get("departure_time", "08:30")
        day_of_week = int(data.get("day_of_week", 1))
    else:
        # GET query params support
        source = request.args.get("source")
        destination = request.args.get("destination")
        departure_time = request.args.get("departure_time", default="08:30")
        day_of_week = request.args.get("day_of_week", default=1, type=int)

        # Coordinate support in GET (e.g. src_lat, src_lon)
        src_lat = request.args.get("src_lat", type=float)
        src_lon = request.args.get("src_lon", type=float)
        if src_lat is not None and src_lon is not None:
            source = {"lat": src_lat, "lon": src_lon, "name": source or "Source Location"}

        dst_lat = request.args.get("dst_lat", type=float)
        dst_lon = request.args.get("dst_lon", type=float)
        if dst_lat is not None and dst_lon is not None:
            destination = {"lat": dst_lat, "lon": dst_lon, "name": destination or "Destination Location"}

    if not source or not destination:
        return jsonify({
            "status": "error",
            "message": "Both 'source' and 'destination' are required fields."
        }), 400

    plan_result = journey_svc.plan_journey(
        source=source,
        destination=destination,
        departure_time=departure_time,
        day_of_week=day_of_week
    )

    return jsonify(plan_result)
