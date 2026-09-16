import cv2
import numpy as np
import time
import os
import urllib.request
from database import load_all_known_encodings, mark_attendance_in_db
from config import Config

# 1. Check if dlib-based face_recognition is available
try:
    import face_recognition
    USE_DLIB = True
    print("[FACE ENGINE] Using dlib / face_recognition backend.")
except ImportError:
    USE_DLIB = False
    print("[FACE ENGINE] face_recognition not found. Falling back to Pure OpenCV Haar Cascade & Feature Matching.")

# 2. Robust Haar Cascade Loader (Auto-downloads if missing in cv2.data)
def load_haar_cascade():
    # Try cv2 built-in data path
    built_in = getattr(cv2.data, 'haarcascades', '') + 'haarcascade_frontalface_default.xml'
    if os.path.exists(built_in):
        cascade = cv2.CascadeClassifier(built_in)
        if not cascade.empty():
            return cascade

    # Try local project directory
    local_xml = os.path.join(os.path.dirname(__file__), 'haarcascade_frontalface_default.xml')
    if not os.path.exists(local_xml):
        print("[FACE ENGINE] Haar cascade XML not found locally. Downloading from official OpenCV repository...")
        url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
        try:
            urllib.request.urlretrieve(url, local_xml)
            print("[FACE ENGINE] Downloaded haarcascade_frontalface_default.xml successfully.")
        except Exception as e:
            print(f"[FACE ENGINE] Error downloading XML: {e}")

    if os.path.exists(local_xml):
        cascade = cv2.CascadeClassifier(local_xml)
        if not cascade.empty():
            return cascade

    return cv2.CascadeClassifier()

face_cascade = load_haar_cascade()

class FaceRecognitionEngine:
    def __init__(self):
        self.known_data = None
        self.reload_known_faces()
        self.last_marked_times = {}

    def reload_known_faces(self):
        """Refreshes facial encodings cached in memory from database."""
        self.known_data = load_all_known_encodings()
        print(f"[FACE ENGINE] Loaded {len(self.known_data['encodings'])} registered faces.")

    def _extract_opencv_feature(self, img_bgr, face_rect=None):
        """Generates a 128-d normalized feature vector using pure OpenCV."""
        if face_rect is not None:
            x, y, w, h = face_rect
            face = img_bgr[y:y+h, x:x+w]
        else:
            face = img_bgr
        
        if face is None or face.size == 0:
            return np.zeros(128, dtype="float32")

        gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (16, 8))  # 16x8 = 128 dimensions
        vector = resized.flatten().astype("float32")
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector

    def extract_encoding_from_image(self, image_path):
        """Validates face in image and returns 128-d embedding."""
        if USE_DLIB:
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image, model="hog")
            if len(face_locations) == 0:
                return None, "No face detected in image. Ensure good lighting and face camera directly."
            if len(face_locations) > 1:
                return None, "Multiple faces detected. Ensure only one person is in the frame."
            encodings = face_recognition.face_encodings(image, face_locations)
            return encodings[0], None
        else:
            # OpenCV Fallback
            img = cv2.imread(image_path)
            if img is None:
                return None, "Could not load image."
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(60, 60))
            if len(faces) == 0:
                return None, "No face detected. Ensure good lighting and look straight at the camera."
            if len(faces) > 1:
                return None, "Multiple faces detected. Please frame only one face."
            
            vector = self._extract_opencv_feature(img, faces[0])
            return vector, None

    def process_live_frame(self, frame):
        """Detects faces, recognizes students, and draws UI bounding boxes."""
        detection_results = []
        if frame is None:
            return frame, detection_results

        if USE_DLIB:
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            for face_encoding, (top, right, bottom, left) in zip(face_encodings, face_locations):
                top, right, bottom, left = top * 4, right * 4, bottom * 4, left * 4
                self._match_and_draw(frame, (left, top, right - left, bottom - top), face_encoding, detection_results, is_dlib=True)
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(70, 70))
            
            for (x, y, fw, fh) in faces:
                feature_vec = self._extract_opencv_feature(frame, (x, y, fw, fh))
                self._match_and_draw(frame, (x, y, fw, fh), feature_vec, detection_results, is_dlib=False)

        return frame, detection_results

    def _match_and_draw(self, frame, bbox, current_vector, detection_results, is_dlib):
        x, y, w, h = bbox
        name = "Unknown"
        roll = ""
        status_color = (0, 0, 255)  # Red for unknown
        match_status = "Unregistered"
        confidence = 0.0

        if self.known_data and len(self.known_data["encodings"]) > 0:
            if is_dlib:
                distances = face_recognition.face_distance(self.known_data["encodings"], current_vector)
                best_idx = int(np.argmin(distances))
                best_dist = distances[best_idx]
                is_match = best_dist <= Config.RECOGNITION_TOLERANCE
                confidence = max(0.0, (1.0 - best_dist)) * 100
            else:
                known_matrix = np.array(self.known_data["encodings"])
                similarities = np.dot(known_matrix, current_vector)
                best_idx = int(np.argmax(similarities))
                best_sim = similarities[best_idx]
                is_match = best_sim >= 0.70
                confidence = min(100.0, max(0.0, best_sim * 100))

            if is_match:
                student_id = self.known_data["ids"][best_idx]
                roll = self.known_data["rolls"][best_idx]
                name = self.known_data["names"][best_idx]
                dept = self.known_data["depts"][best_idx]
                status_color = (0, 220, 50)  # Green for recognized

                # 5-second debounce check
                now = time.time()
                if student_id not in self.last_marked_times or (now - self.last_marked_times[student_id] > 5):
                    res, msg = mark_attendance_in_db(student_id, roll, name, dept, confidence)
                    self.last_marked_times[student_id] = now
                    match_status = "Checked In" if res == "SUCCESS" else "Already Marked"
                else:
                    match_status = "Verified"

        # Draw aesthetic corner box
        self._draw_corner_rect(frame, bbox, status_color, 2, 15)

        # Label badge
        label = f"{name}"
        sub_label = f"{roll} | {confidence:.1f}%" if roll else match_status
        cv2.rectangle(frame, (x, y + h - 45), (x + w, y + h), status_color, cv2.FILLED)
        cv2.putText(frame, label, (x + 6, y + h - 26), cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(frame, sub_label, (x + 6, y + h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        detection_results.append({"name": name, "roll": roll, "status": match_status, "confidence": confidence})

    def _draw_corner_rect(self, img, bbox, color, thickness=2, corner_len=15):
        x, y, w, h = bbox
        cv2.line(img, (x, y), (x + corner_len, y), color, thickness)
        cv2.line(img, (x, y), (x, y + corner_len), color, thickness)
        cv2.line(img, (x + w, y), (x + w - corner_len, y), color, thickness)
        cv2.line(img, (x + w, y), (x + w, y + corner_len), color, thickness)
        cv2.line(img, (x, y + h), (x + corner_len, y + h), color, thickness)
        cv2.line(img, (x, y + h), (x, y + h - corner_len), color, thickness)
        cv2.line(img, (x + w, y + h), (x + w - corner_len, y + h), color, thickness)
        cv2.line(img, (x + w, y + h), (x + w, y + h - corner_len), color, thickness)

face_engine = FaceRecognitionEngine()

def generate_video_stream():
    cap = cv2.VideoCapture(Config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    while True:
        success, frame = cap.read()
        if not success:
            break

        processed_frame, _ = face_engine.process_live_frame(frame)
        ret, buffer = cv2.imencode('.jpg', processed_frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    cap.release()