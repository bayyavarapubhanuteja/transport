"""DelhiMove AI - Feature Engineering & Time-Based Splitting."""

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "distance_m",
    "hour",
    "day_of_week",
    "is_weekend",
    "is_peak_hour",
    "historical_avg_speed_kmh",
]

TARGET_COLUMN = "target_travel_time_sec"

def extract_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Extracts X (features) and y (target) from raw preprocessed DataFrame."""
    X = df[FEATURE_COLUMNS].copy()
    y = df[TARGET_COLUMN].copy() if TARGET_COLUMN in df.columns else None
    return X, y

def time_based_train_test_split(df: pd.DataFrame, test_start_day: int = 22) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Splits dataset temporally based on calendar dates (Oct 1-21 Train vs Oct 22-31 Test)
    to strictly eliminate data leakage while learning full 24-hour traffic dynamics.
    """
    if "day" in df.columns:
        train_df = df[df["day"] < test_start_day].copy()
        test_df = df[df["day"] >= test_start_day].copy()
    else:
        split_idx = int(len(df) * 0.70)
        train_df = df.iloc[:split_idx].copy()
        test_df = df.iloc[split_idx:].copy()

    return train_df, test_df
