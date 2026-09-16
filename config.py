import os
from dotenv import load_dotenv

# Load secret variables from .env file
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key-2026")
    DATABASE_PATH = os.path.join(BASE_DIR, "attendance_system.db")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads", "faces")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
    RECOGNITION_TOLERANCE = 0.58
    CAMERA_INDEX = 0

    # Secret Admin from .env (Code me koi password nahi!)
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")