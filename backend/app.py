"""DelhiMove AI - Main Flask Application (Stage 5)
High-performance REST API Server for Real-Time Bus Traffic Prediction & Journey Planning.
"""

import os
import sys
from pathlib import Path
from flask import Flask, jsonify
from flask_cors import CORS

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, PROJECT_ROOT.as_posix())

from config import Config
from routes.stops import stops_bp
from routes.buses import buses_bp
from routes.traffic import traffic_bp
from routes.journey import journey_bp
from routes.analytics import analytics_bp

def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Enable CORS for frontend clients
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register Blueprints
    app.register_blueprint(stops_bp)
    app.register_blueprint(buses_bp)
    app.register_blueprint(traffic_bp)
    app.register_blueprint(journey_bp)
    app.register_blueprint(analytics_bp)

    @app.route("/", methods=["GET"])
    def root():
        return jsonify({
            "name": "DelhiMove AI API",
            "version": Config.VERSION,
            "status": "operational",
            "city": "Delhi NCR, India",
            "docs": {
                "stops": "/api/stops?q=Kashmere",
                "routes": "/api/routes",
                "vehicles_live": "/api/vehicles/live",
                "traffic_overview": "/api/traffic/overview",
                "traffic_predict": "/api/traffic/predict?distance_m=1500&hour=9",
                "journey_plan": "POST /api/journey/plan",
                "analytics": "/api/analytics/overview"
            }
        })

    @app.route("/api/health", methods=["GET"])
    def healthcheck():
        return jsonify({
            "status": "healthy",
            "db_exists": Config.DATABASE_PATH.exists(),
            "model_ready": (Config.ML_MODELS_DIR / "travel_time_rf.joblib").exists(),
            "shapes_ready": (Config.PROCESSED_DIR / "shapes_summary.json").exists()
        })

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"status": "error", "message": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"status": "error", "message": "Internal server error", "detail": str(e)}), 500

    return app

app = create_app()

if __name__ == "__main__":
    port = Config.PORT
    host = Config.HOST
    print(f"🚀 DelhiMove AI REST API starting on http://{host}:{port}")
    app.run(host=host, port=port, debug=Config.DEBUG)
