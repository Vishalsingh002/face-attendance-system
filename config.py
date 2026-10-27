import os
from datetime import timedelta
from dotenv import load_dotenv

# Load secret variables from .env file
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    BASE_DIR = BASE_DIR
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY") or os.getenv("SECRET_KEY", "fallback-secret-key-2026")
    DATABASE_PATH = os.path.join(BASE_DIR, "attendance_system.db")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads", "faces")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
    RECOGNITION_TOLERANCE = 0.58
    CAMERA_INDEX = 0
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.getenv("SESSION_TIMEOUT_MINUTES", "30")))

    # Secret Admin credentials with safe fallbacks
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME") or "admin"
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD") or "admin123"

    # Cloud Storage (Google Firebase)
    FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase_credentials.json")
    FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET", "smart-face-attendance0.firebasestorage.app")
    FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "")
    FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "smart-face-attendance0")

    # Cloud Database (Turso LibSQL)
    TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "")
    TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "")

# Module level exports (taaki direct import bhi fail na ho)
ADMIN_USERNAME = Config.ADMIN_USERNAME
ADMIN_PASSWORD = Config.ADMIN_PASSWORD
FLASK_SECRET_KEY = Config.SECRET_KEY