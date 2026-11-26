"""Configuration settings for DelhiMove AI Backend."""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Load environment variables from .env if present
load_dotenv(BASE_DIR / ".env")

class Config:
    PROJECT_NAME = "DelhiMove AI"
    VERSION = "1.0.0"
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1")
    PORT = int(os.getenv("PORT", 5001))
    HOST = os.getenv("HOST", "127.0.0.1")

    # Database
    DATABASE_PATH = BASE_DIR / "delhi_move.db"
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{DATABASE_PATH.as_posix()}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Transport Stack Official API Credentials (secure environment variables)
    DELHI_TRANSPORT_API_KEY = os.getenv("DELHI_TRANSPORT_API_KEY", "")
    DELHI_TRANSPORT_API_URL = os.getenv(
        "DELHI_TRANSPORT_API_URL", "https://api.transportstack.delhi.gov.in/v1"
    )

    # Directories
    DATA_DIR = PROJECT_ROOT / "data"
    PROCESSED_DIR = DATA_DIR / "processed"
    GTFS_DIR = DATA_DIR / "raw" / "gtfs"
    ML_MODELS_DIR = PROJECT_ROOT / "ml" / "saved_models"

    # Delhi NCR Spatial Bounds
    DELHI_BBOX = {
        "lat_min": 28.25,
        "lat_max": 29.05,
        "lon_min": 76.75,
        "lon_max": 77.65,
    }
