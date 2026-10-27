import os
import io
import shutil
import logging
from werkzeug.utils import secure_filename
from config import Config

logger = logging.getLogger(__name__)

# Track Firebase status
_firebase_app = None
_firebase_bucket = None
_firebase_initialized = False

def init_firebase():
    """
    Initializes Firebase Admin SDK if credentials and storage bucket are present in .env.
    Gracefully falls back to local storage if not configured.
    """
    global _firebase_app, _firebase_bucket, _firebase_initialized
    if _firebase_initialized:
        return _firebase_bucket is not None

    creds_path = getattr(Config, "FIREBASE_CREDENTIALS_PATH", "firebase_credentials.json")
    bucket_name = getattr(Config, "FIREBASE_STORAGE_BUCKET", "").strip()

    # Resolve relative path to absolute
    if not os.path.isabs(creds_path):
        base_dir = getattr(Config, "BASE_DIR", os.path.dirname(os.path.abspath(__file__)))
        creds_path = os.path.join(base_dir, creds_path)

    if not os.path.exists(creds_path) or not bucket_name:
        _firebase_initialized = True
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials, storage

        if not firebase_admin._apps:
            cred = credentials.Certificate(creds_path)
            clean_bucket = bucket_name.replace("gs://", "").strip()
            _firebase_app = firebase_admin.initialize_app(cred, {
                'storageBucket': clean_bucket
            })
        _firebase_bucket = storage.bucket()
        _firebase_initialized = True
        print(f"[FIREBASE] Connected to Google Firebase Storage bucket: {bucket_name}")
        return True
    except Exception as e:
        print(f"[FIREBASE] Initialization warning: {e}. Falling back to Local Storage.")
        _firebase_initialized = True
        return False

def upload_student_photo(file_bytes_or_stream, filename, content_type="image/jpeg"):
    """
    Uploads a student facial photo:
    - If Firebase is active: uploads to Firebase Storage & generates public/signed CDN URL.
      Also maintains a local cache copy for OpenCV / face recognition speed.
    - If Firebase is not configured: saves directly to static/uploads/faces/<filename>.
    
    Returns: (photo_url_or_rel_path, is_cloud)
    """
    init_firebase()
    safe_name = secure_filename(filename)
    local_dir = Config.UPLOAD_FOLDER
    os.makedirs(local_dir, exist_ok=True)
    local_path = os.path.join(local_dir, safe_name)

    # 1. Read bytes safely
    if hasattr(file_bytes_or_stream, "read"):
        data = file_bytes_or_stream.read()
        if hasattr(file_bytes_or_stream, "seek"):
            file_bytes_or_stream.seek(0)
    elif isinstance(file_bytes_or_stream, bytes):
        data = file_bytes_or_stream
    else:
        raise ValueError("Unsupported file input format")

    # Always save a local copy so OpenCV & dlib can process without network latency
    with open(local_path, "wb") as f:
        f.write(data)

    # 2. Upload to Firebase Storage if connected (Admin SDK)
    global _firebase_bucket
    if _firebase_bucket is not None:
        try:
            blob = _firebase_bucket.blob(f"students/{safe_name}")
            blob.upload_from_string(data, content_type=content_type)
            try:
                blob.make_public()
                cloud_url = blob.public_url
            except Exception:
                from datetime import timedelta
                cloud_url = blob.generate_signed_url(timedelta(days=3650))
            
            print(f"[FIREBASE] Successfully uploaded student photo via Admin SDK: {safe_name}")
            return cloud_url, True
        except Exception as e:
            print(f"[FIREBASE Admin] Cloud upload failed: {e}. Trying REST API fallback.")

    # 3. Direct Firebase Storage REST API with Web API Key & Bucket
    bucket = getattr(Config, "FIREBASE_STORAGE_BUCKET", "").strip()
    api_key = getattr(Config, "FIREBASE_API_KEY", "").strip()
    if bucket:
        try:
            import requests
            url = f"https://firebasestorage.googleapis.com/v0/b/{bucket}/o?uploadType=media&name=students/{safe_name}"
            if api_key:
                url += f"&key={api_key}"
            headers = {"Content-Type": content_type}
            resp = requests.post(url, data=data, headers=headers, timeout=10)
            if resp.ok:
                res_json = resp.json()
                token = res_json.get("downloadTokens", "")
                if token:
                    cloud_url = f"https://firebasestorage.googleapis.com/v0/b/{bucket}/o/students%2F{safe_name}?alt=media&token={token}"
                else:
                    cloud_url = f"https://firebasestorage.googleapis.com/v0/b/{bucket}/o/students%2F{safe_name}?alt=media"
                print(f"[FIREBASE REST] Successfully uploaded student photo to Firebase: {safe_name}")
                return cloud_url, True
            else:
                print(f"[FIREBASE REST] HTTP {resp.status_code}: {resp.text[:120]}")
        except Exception as err:
            print(f"[FIREBASE REST] Upload failed: {err}")

    # 4. Local fallback path relative to web root
    rel_path = f"/static/uploads/faces/{safe_name}"
    return rel_path, False

def delete_student_photo(photo_path_or_url):
    """
    Deletes student photo from both Firebase and Local storage.
    """
    init_firebase()
    if not photo_path_or_url:
        return

    # 1. Local delete
    filename = os.path.basename(photo_path_or_url.split("?")[0])
    local_path = os.path.join(Config.UPLOAD_FOLDER, filename)
    if os.path.exists(local_path):
        try:
            os.remove(local_path)
        except OSError:
            pass

    # 2. Firebase delete
    global _firebase_bucket
    if _firebase_bucket is not None and ("firebase" in photo_path_or_url or "googleapis" in photo_path_or_url):
        try:
            blob = _firebase_bucket.blob(f"students/{filename}")
            if blob.exists():
                blob.delete()
                print(f"[FIREBASE] Deleted cloud photo: {filename}")
        except Exception as e:
            print(f"[FIREBASE] Cloud delete error: {e}")

def get_storage_info():
    """Returns current active storage backend details."""
    init_firebase()
    bucket = getattr(Config, "FIREBASE_STORAGE_BUCKET", "").strip()
    api_key = getattr(Config, "FIREBASE_API_KEY", "").strip()
    if _firebase_bucket is not None or (bucket and api_key):
        return {
            "provider": "Google Firebase Storage",
            "bucket": bucket,
            "status": "Online",
            "icon": "fa-brands fa-google text-danger"
        }
    return {
        "provider": "Local Disk Storage",
        "folder": Config.UPLOAD_FOLDER,
        "status": "Active (Offline Ready)",
        "icon": "fa-solid fa-hard-drive text-primary"
    }
