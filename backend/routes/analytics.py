"""DelhiMove AI - Analytics Blueprint (Stage 5)
Endpoint for network scale and ML model evaluation metrics.
"""

from flask import Blueprint, jsonify
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, BACKEND_DIR.as_posix())

from services.analytics_service import get_analytics_service

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")

@analytics_bp.route("/overview", methods=["GET"])
def analytics_overview():
    """Returns network metrics, coverage stats, and genuine ML evaluation results."""
    analytics_svc = get_analytics_service()
    overview = analytics_svc.get_overview()
    return jsonify(overview)
