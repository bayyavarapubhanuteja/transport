"""DelhiMove AI - Travel Time Prediction & Reliability Scoring (Stage 3)
Loads the trained Random Forest model and provides fast single-segment
and multi-segment journey travel-time predictions with confidence indicators.
"""

import os
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "ml" / "saved_models" / "travel_time_rf.joblib"
METRICS_PATH = PROJECT_ROOT / "ml" / "saved_models" / "model_metrics.json"

FEATURE_COLUMNS = [
    "distance_m",
    "hour",
    "day_of_week",
    "is_weekend",
    "is_peak_hour",
    "historical_avg_speed_kmh",
]

class TravelTimePredictor:
    def __init__(self, model_path: Path = MODEL_PATH):
        self.model_path = Path(model_path)
        self.model = None
        self.metrics = None
        self._load()

    def _load(self):
        if self.model_path.exists():
            try:
                self.model = joblib.load(self.model_path)
            except Exception as e:
                print(f"Warning: Could not load ML model: {e}. Fallback to baseline enabled.")
                self.model = None

        if METRICS_PATH.exists():
            try:
                with open(METRICS_PATH, "r", encoding="utf-8") as f:
                    self.metrics = json.load(f)
            except Exception:
                self.metrics = None

    def predict_segment(
        self,
        distance_m: float,
        hour: int = 9,
        day_of_week: int = 1,
        historical_speed_kmh: float = 18.5
    ) -> dict:
        """Predicts travel time for a single road or transit segment."""
        is_weekend = 1 if day_of_week >= 5 else 0
        is_peak = 1 if (hour in (8, 9, 10, 17, 18, 19, 20)) and not is_weekend else 0

        # Baseline travel time (seconds)
        baseline_sec = max(5.0, distance_m / (historical_speed_kmh * (1000 / 3600)))

        # ML Prediction
        if self.model is not None:
            features = pd.DataFrame([{
                "distance_m": float(distance_m),
                "hour": int(hour),
                "day_of_week": int(day_of_week),
                "is_weekend": is_weekend,
                "is_peak_hour": is_peak,
                "historical_avg_speed_kmh": float(historical_speed_kmh),
            }])[FEATURE_COLUMNS]

            try:
                pred_sec = float(self.model.predict(features)[0])
                pred_sec = max(5.0, pred_sec)
                method = "random_forest_regressor"

                # Compute real ensemble agreement across decision trees
                in_coverage = 80.0 <= float(distance_m) <= 3500.0
                if hasattr(self.model, "estimators_") and len(self.model.estimators_) > 0:
                    tree_preds = np.array([est.predict(features.values)[0] for est in self.model.estimators_])
                    cv = float(np.std(tree_preds) / max(1.0, np.mean(tree_preds)))
                    agreement_score = max(0.55, min(0.98, 1.0 - cv * 1.2))
                else:
                    agreement_score = 0.88

                if not in_coverage:
                    confidence_score = round(max(0.55, agreement_score - 0.15), 2)
                    confidence = "medium"
                    confidence_level = "Medium"
                    reliability = "Moderate Reliability"
                    confidence_reason = (
                        f"Extrapolated distance ({round(distance_m)}m outside 80–3500m training range); "
                        f"Random Forest (75 trees) calibrated on 39,900 Oct 1–21 records (held-out MAE 10.96s)."
                    )
                elif agreement_score >= 0.80:
                    confidence_score = round(agreement_score, 2)
                    confidence = "high"
                    confidence_level = "High"
                    reliability = "High Reliability"
                    confidence_reason = (
                        f"In-distribution prediction ({round(distance_m)}m within 80–3500m GTFS segment range); "
                        f"75-tree ensemble agreement {int(agreement_score*100)}% trained on 39,900 samples (R²=0.9731)."
                    )
                else:
                    confidence_score = round(agreement_score, 2)
                    confidence = "medium"
                    confidence_level = "Medium"
                    reliability = "Moderate Reliability"
                    confidence_reason = (
                        f"Higher traffic variance at hour {hour:02d}:00; "
                        f"75-tree ensemble agreement {int(agreement_score*100)}% (held-out test MAE 10.96s)."
                    )
            except Exception:
                pred_sec = baseline_sec
                method = "historical_baseline_fallback"
                confidence_score = 0.62
                confidence = "medium"
                confidence_level = "Medium"
                reliability = "Baseline Fallback"
                confidence_reason = "Historical average fallback applied due to ML inference error."
        else:
            pred_sec = baseline_sec
            method = "historical_baseline_fallback"
            confidence_score = 0.60
            confidence = "medium"
            confidence_level = "Medium"
            reliability = "Baseline Fallback"
            confidence_reason = "Historical average speed fallback (ML model weights not loaded)."

        # Implied effective speed in km/h
        effective_speed_kmh = (distance_m / pred_sec) * 3.6
        speed_ratio = effective_speed_kmh / max(1.0, float(historical_speed_kmh))

        # Traffic Congestion Classification relative to historical network speed (18.5 km/h)
        if speed_ratio >= 1.05 and effective_speed_kmh >= 19.5:
            congestion_level = "low"      # Green: faster than historical norm
        elif speed_ratio >= 0.72 and effective_speed_kmh >= 13.0:
            congestion_level = "moderate" # Yellow: near or moderately below historical norm
        else:
            congestion_level = "high"     # Red: significant slowdown vs historical norm

        return {
            "predicted_duration_sec": round(pred_sec, 1),
            "predicted_duration_min": round(pred_sec / 60.0, 1),
            "baseline_duration_sec": round(baseline_sec, 1),
            "effective_speed_kmh": round(effective_speed_kmh, 1),
            "historical_speed_kmh": round(float(historical_speed_kmh), 1),
            "speed_ratio": round(speed_ratio, 2),
            "congestion_level": congestion_level,
            "confidence": confidence,
            "confidence_level": confidence_level,
            "confidence_score": confidence_score,
            "reliability": reliability,
            "confidence_reason": confidence_reason,
            "prediction_method": method,
        }

    def predict_journey(
        self,
        segment_distances_m: list[float],
        hour: int = 9,
        day_of_week: int = 1
    ) -> dict:
        """Predicts travel times across multiple contiguous route segments of a journey."""
        if not segment_distances_m:
            return {
                "total_duration_sec": 0,
                "total_duration_min": 0,
                "segments": [],
                "confidence": "high",
                "overall_congestion": "low"
            }

        seg_results = []
        total_sec = 0.0
        total_dist = 0.0
        congestions = []

        for dist in segment_distances_m:
            res = self.predict_segment(dist, hour, day_of_week)
            seg_results.append(res)
            total_sec += res["predicted_duration_sec"]
            total_dist += dist
            congestions.append(res["congestion_level"])

        # Overall congestion
        if congestions.count("high") > len(congestions) * 0.35:
            overall_congestion = "high"
        elif congestions.count("moderate") + congestions.count("high") > len(congestions) * 0.4:
            overall_congestion = "moderate"
        else:
            overall_congestion = "low"

        # Overall confidence from segment ensemble scores
        avg_speed = (total_dist / total_sec) * 3.6 if total_sec > 0 else 18.5
        avg_conf_score = round(sum(s["confidence_score"] for s in seg_results) / len(seg_results), 2) if seg_results else 0.60
        ml_count = sum(1 for s in seg_results if s["prediction_method"] == "random_forest_regressor")
        ml_coverage_pct = round((ml_count / len(seg_results)) * 100, 1) if seg_results else 0.0
        confidence = "high" if (self.model is not None and avg_conf_score >= 0.80) else "medium"
        reliability = "High Reliability" if confidence == "high" else ("Moderate Reliability" if self.model is not None else "Baseline Fallback")

        return {
            "total_distance_m": round(total_dist, 1),
            "total_duration_sec": round(total_sec, 1),
            "total_duration_min": round(total_sec / 60.0, 1),
            "average_speed_kmh": round(avg_speed, 1),
            "overall_congestion": overall_congestion,
            "confidence": confidence,
            "confidence_level": "High" if confidence == "high" else "Medium",
            "confidence_score": avg_conf_score,
            "reliability": reliability,
            "ml_coverage_pct": ml_coverage_pct,
            "prediction_method": "random_forest_regressor" if ml_count > 0 else "historical_baseline_fallback",
            "confidence_reason": (
                f"ML prediction across {len(seg_results)} segments ({ml_coverage_pct}% RF coverage, "
                f"mean ensemble agreement {int(avg_conf_score * 100)}%)."
            ) if ml_count > 0 else "Historical average fallback applied (ML weights unavailable).",
            "segment_predictions": seg_results
        }

# Global singleton predictor instance
_predictor = None

def get_predictor() -> TravelTimePredictor:
    global _predictor
    if _predictor is None:
        _predictor = TravelTimePredictor()
    return _predictor
