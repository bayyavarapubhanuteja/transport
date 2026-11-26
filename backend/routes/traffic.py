"""DelhiMove AI - Traffic Blueprint (Stage 5 & Stage 8)
Endpoints for network congestion overview and segment travel time prediction.
"""

from flask import Blueprint, request, jsonify
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, BACKEND_DIR.as_posix())

from services.traffic_service import get_traffic_service

traffic_bp = Blueprint("traffic", __name__, url_prefix="/api/traffic")

@traffic_bp.route("/overview", methods=["GET"])
def traffic_overview():
    """Returns network-wide traffic conditions and arterial corridor delays."""
    traffic_svc = get_traffic_service()
    overview = traffic_svc.get_network_overview()
    return jsonify(overview)

@traffic_bp.route("/predict", methods=["GET", "POST"])
def traffic_predict():
    """Predicts segment travel time using the Random Forest ML model."""
    traffic_svc = get_traffic_service()

    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        distance_m = body.get("distance_m")
        from_stop_id = body.get("from_stop_id")
        to_stop_id = body.get("to_stop_id")
        hour = body.get("hour", 9)
        day_of_week = body.get("day_of_week", 1)
    else:
        distance_m = request.args.get("distance_m", type=float)
        from_stop_id = request.args.get("from_stop_id", type=int)
        to_stop_id = request.args.get("to_stop_id", type=int)
        hour = request.args.get("hour", default=9, type=int)
        day_of_week = request.args.get("day_of_week", default=1, type=int)

    pred = traffic_svc.predict_segment(
        distance_m=distance_m,
        from_stop_id=from_stop_id,
        to_stop_id=to_stop_id,
        hour=hour,
        day_of_week=day_of_week
    )
    return jsonify(pred)
