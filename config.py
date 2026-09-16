import os
from dotenv import load_dotenv

# Load secret variables from .env file
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY") or os.getenv("SECRET_KEY", "fallback-secret-key-2026")
    DATABASE_PATH = os.path.join(BASE_DIR, "attendance_system.db")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads", "faces")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
    RECOGNITION_TOLERANCE = 0.58
    CAMERA_INDEX = 0

    # Secret Admin credentials with safe fallbacks
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME") or "admin"
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD") or "admin123"

# Module level exports (taaki direct import bhi fail na ho)
ADMIN_USERNAME = Config.ADMIN_USERNAME
ADMIN_PASSWORD = Config.ADMIN_PASSWORD
FLASK_SECRET_KEY = Config.SECRET_KEY