"""Unit tests for Stage 3 - Machine Learning Traffic Prediction Engine."""

import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ML_DIR = PROJECT_ROOT / "ml"
sys.path.insert(0, ML_DIR.as_posix())

from predict import TravelTimePredictor, get_predictor

def test_model_artifacts_exist():
    model_path = ML_DIR / "saved_models" / "travel_time_rf.joblib"
    metrics_path = ML_DIR / "saved_models" / "model_metrics.json"

    assert model_path.exists(), "Trained model joblib artifact missing"
    assert metrics_path.exists(), "Evaluation metrics JSON missing"

def test_metrics_evaluation_quality():
    import json
    metrics_path = ML_DIR / "saved_models" / "model_metrics.json"
    with open(metrics_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "models" in data
    assert "baseline_historical_avg" in data["models"]
    assert "random_forest" in data["models"]

    rf_metrics = data["models"]["random_forest"]
    assert rf_metrics["mae_seconds"] < 25.0, "Random Forest MAE should be < 25s"
    assert rf_metrics["r2_score"] > 0.85, "Random Forest R² should be > 0.85"
    assert rf_metrics["improvement_vs_baseline_pct"] > 40.0, "RF should significantly outperform baseline"

def test_single_segment_prediction():
    predictor = get_predictor()
    res = predictor.predict_segment(distance_m=850.0, hour=9, day_of_week=1)

    assert "predicted_duration_sec" in res
    assert "predicted_duration_min" in res
    assert "effective_speed_kmh" in res
    assert res["predicted_duration_sec"] > 10.0
    assert res["congestion_level"] in ("low", "moderate", "high")
    assert res["confidence"] in ("high", "medium", "low")

def test_multi_segment_journey_prediction():
    predictor = get_predictor()
    # 5 contiguous stops with ~500m spacing
    segments = [450.0, 520.0, 610.0, 480.0, 550.0]
    res = predictor.predict_journey(segments, hour=18, day_of_week=2)

    assert res["total_distance_m"] == sum(segments)
    assert res["total_duration_sec"] > 0
    assert res["total_duration_min"] > 0
    assert len(res["segment_predictions"]) == 5
    assert res["overall_congestion"] in ("low", "moderate", "high")
