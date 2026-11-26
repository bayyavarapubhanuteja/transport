"""DelhiMove AI - Machine Learning Model Training (Stage 3)
Trains:
1. Historical Average Baseline (distance / historical avg speed)
2. Random Forest Regressor on time-split transit records (Train: Oct 1-21, Test: Oct 22-31)
Computes MAE, RMSE, MAPE, R², and saves model artifacts.
"""

import os
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from feature_engineering import extract_features, time_based_train_test_split, FEATURE_COLUMNS

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "ml_training_data.parquet"
MODEL_DIR = PROJECT_ROOT / "ml" / "saved_models"

def calculate_mape(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    non_zero = y_true > 1.0
    if not np.any(non_zero):
        return 0.0
    return float(np.mean(np.abs((y_true[non_zero] - y_pred[non_zero]) / y_true[non_zero])) * 100)

def train_and_evaluate():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80, flush=True)
    print("DelhiMove AI - STAGE 3: Travel-Time Prediction Model Training", flush=True)
    print("=" * 80, flush=True)

    # 1. Load Preprocessed Data
    print(f"\n[1/4] Loading training dataset from {DATA_PATH.name}...", flush=True)
    df = pd.read_parquet(DATA_PATH)
    print(f"  Total records: {len(df):,}", flush=True)

    # 2. Time-Based Train/Test Split (Oct 1-21 Train vs Oct 22-31 Test)
    print("\n[2/4] Applying time-based calendar split to prevent data leakage...", flush=True)
    train_df, test_df = time_based_train_test_split(df)
    print(f"  Training samples (Oct 1 to Oct 21): {len(train_df):,} ({len(train_df)/len(df)*100:.1f}%)", flush=True)
    print(f"  Testing samples  (Oct 22 to Oct 31): {len(test_df):,} ({len(test_df)/len(df)*100:.1f}%)", flush=True)

    X_train, y_train = extract_features(train_df)
    X_test, y_test = extract_features(test_df)

    # 3. Model 1: Historical Average Baseline
    print("\n[3/4] Evaluating Historical Average Baseline...", flush=True)
    baseline_pred = X_test["distance_m"] / (X_test["historical_avg_speed_kmh"] * (1000 / 3600))
    base_mae = float(mean_absolute_error(y_test, baseline_pred))
    base_rmse = float(np.sqrt(mean_squared_error(y_test, baseline_pred)))
    base_mape = float(calculate_mape(y_test, baseline_pred))
    base_r2 = float(r2_score(y_test, baseline_pred))

    print(f"  Baseline Results on Held-out Days (Oct 22-31):", flush=True)
    print(f"    - MAE:  {base_mae:.2f} seconds", flush=True)
    print(f"    - RMSE: {base_rmse:.2f} seconds", flush=True)
    print(f"    - MAPE: {base_mape:.2f}%", flush=True)
    print(f"    - R²:   {base_r2:.4f}", flush=True)

    # 4. Model 2: Random Forest Regressor
    print("\n[4/4] Training Random Forest Regressor (n_estimators=75, max_depth=14)...", flush=True)
    rf = RandomForestRegressor(
        n_estimators=75,
        max_depth=14,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=1
    )
    rf.fit(X_train, y_train)

    rf_pred = rf.predict(X_test)
    rf_mae = float(mean_absolute_error(y_test, rf_pred))
    rf_rmse = float(np.sqrt(mean_squared_error(y_test, rf_pred)))
    rf_mape = float(calculate_mape(y_test, rf_pred))
    rf_r2 = float(r2_score(y_test, rf_pred))

    improvement_pct = ((base_mae - rf_mae) / base_mae) * 100
    print(f"  Random Forest Results on Held-out Days (Oct 22-31):", flush=True)
    print(f"    - MAE:  {rf_mae:.2f} seconds ({improvement_pct:.1f}% reduction in error vs baseline)", flush=True)
    print(f"    - RMSE: {rf_rmse:.2f} seconds", flush=True)
    print(f"    - MAPE: {rf_mape:.2f}%", flush=True)
    print(f"    - R²:   {rf_r2:.4f}", flush=True)

    # Feature Importance
    importances = dict(zip(FEATURE_COLUMNS, [float(x) for x in rf.feature_importances_]))
    print("\n  Top Feature Importances:", flush=True)
    for feat, imp in sorted(importances.items(), key=lambda x: x[1], reverse=True):
        print(f"    • {feat:25s}: {imp*100:.1f}%", flush=True)

    # Save Model Artifacts
    model_path = MODEL_DIR / "travel_time_rf.joblib"
    joblib.dump(rf, model_path, compress=3)
    print(f"\n✓ Saved trained Random Forest model to: {model_path.relative_to(PROJECT_ROOT)}", flush=True)

    # Save Metrics & Comparison Report
    metrics = {
        "model_type": "RandomForestRegressor",
        "features": FEATURE_COLUMNS,
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "split_strategy": "time_based_split (Train: Oct 1-21, Held-out Test: Oct 22-31)",
        "models": {
            "baseline_historical_avg": {
                "mae_seconds": round(base_mae, 2),
                "rmse_seconds": round(base_rmse, 2),
                "mape_percent": round(base_mape, 2),
                "r2_score": round(base_r2, 4)
            },
            "random_forest": {
                "mae_seconds": round(rf_mae, 2),
                "rmse_seconds": round(rf_rmse, 2),
                "mape_percent": round(rf_mape, 2),
                "r2_score": round(rf_r2, 4),
                "improvement_vs_baseline_pct": round(improvement_pct, 1)
            }
        },
        "feature_importances": importances
    }

    metrics_path = MODEL_DIR / "model_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"✓ Saved evaluation metrics to: {metrics_path.relative_to(PROJECT_ROOT)}", flush=True)

    return metrics

if __name__ == "__main__":
    train_and_evaluate()
