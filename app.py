import os
import io
import csv
import json
import base64
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, Response, jsonify, send_file
)
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
import numpy as np
import pandas as pd

from config import Config
from database import (
    init_db, get_db_connection, save_student,
    get_all_crs, add_new_cr, delete_cr_by_id,
    generate_new_daily_session, get_current_active_session, close_active_session
)

app = Flask(__name__)
app.config.from_object(Config)

# 1. Initialize Database Schema
init_db()

# 2. Computer Vision Face Engine
from face_engine import face_engine, generate_video_stream, USE_DLIB

# --- Role-Based Access Helpers ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "admin_logged_in" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def superadmin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("admin_role") != "superadmin":
            flash("Access Denied: Only Main Admin has permission.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

@app.route("/")
def index():
    if "admin_logged_in" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admins WHERE username = ?", (username,))
        admin = cursor.fetchone()
        conn.close()

        if admin and check_password_hash(admin["password_hash"], password):
            session["admin_logged_in"] = True
            session["admin_username"] = admin["username"]
            session["admin_role"] = admin["role"] if "role" in admin.keys() else "superadmin"
            flash(f"Welcome back, {admin['username']} ({session['admin_role'].upper()})!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM students")
    total_students = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM attendance WHERE date = ?", (today,))
    today_present = cursor.fetchone()["total"]

    today_absent = max(0, total_students - today_present)
    attendance_percentage = round((today_present / total_students * 100), 1) if total_students > 0 else 0

    cursor.execute("SELECT * FROM attendance WHERE date = ? ORDER BY time DESC LIMIT 5", (today,))
    recent_records = cursor.fetchall()

    cursor.execute("SELECT department, COUNT(*) as count FROM students GROUP BY department")
    dept_distribution = cursor.fetchall()

    cursor.execute("SELECT date, COUNT(*) as count FROM attendance GROUP BY date ORDER BY date DESC LIMIT 7")
    trend_data = cursor.fetchall()
    conn.close()

    active_session = get_current_active_session()

    return render_template(
        "dashboard.html",
        total_students=total_students,
        today_present=today_present,
        today_absent=today_absent,
        attendance_percentage=attendance_percentage,
        recent_records=recent_records,
        dept_labels=[row["department"] for row in dept_distribution],
        dept_counts=[row["count"] for row in dept_distribution],
        trend_dates=[row["date"] for row in reversed(trend_data)],
        trend_counts=[row["count"] for row in reversed(trend_data)],
        active_session=active_session
    )

# --- Dynamic Daily Link Controller ---
@app.route("/session/generate", methods=["POST"])
@login_required
def route_generate_session():
    code = generate_new_daily_session()
    flash(f"🚀 New Attendance Session Started! Code: {code}", "success")
    return redirect(url_for("dashboard"))

@app.route("/session/close", methods=["POST"])
@login_required
def route_close_session():
    close_active_session()
    flash("🔒 Attendance Session closed. Link is now expired!", "warning")
    return redirect(url_for("dashboard"))

# --- Public Student Registration (One-Time) ---
@app.route("/register", methods=["GET", "POST"])
def register_student():
    if request.method == "POST":
        roll_number = request.form.get("roll_number", "").strip().upper()
        name = request.form.get("name", "").strip()
        department = request.form.get("department", "").strip()
        semester = request.form.get("semester", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        webcam_image_data = request.form.get("webcam_image", "")

        if not roll_number or not name or not department:
            flash("Roll number, name, and department are mandatory.", "danger")
            return redirect(url_for("register_student"))

        filename = f"{secure_filename(roll_number)}.jpg"
        save_path = os.path.join(Config.UPLOAD_FOLDER, filename)

        if webcam_image_data and "base64," in webcam_image_data:
            header, encoded = webcam_image_data.split("base64,", 1)
            image_bytes = base64.b64decode(encoded)
            with open(save_path, "wb") as f:
                f.write(image_bytes)
        elif "photo" in request.files and request.files["photo"].filename != "":
            file = request.files["photo"]
            file.save(save_path)
        else:
            flash("Please capture a photo via camera or upload a picture.", "warning")
            return redirect(url_for("register_student"))

        encoding, error = face_engine.extract_encoding_from_image(save_path)
        if error:
            if os.path.exists(save_path):
                os.remove(save_path)
            flash(error, "danger")
            return redirect(url_for("register_student"))

        success, msg = save_student(roll_number, name, department, semester, email, phone, filename, encoding)

        if success:
            face_engine.reload_known_faces()
            flash(f"🎉 Success! {name} ({roll_number}), your face enrollment is complete. You can close this tab.", "success")
            if "admin_logged_in" in session:
                return redirect(url_for("students_list"))
            return redirect(url_for("register_student"))
        else:
            if os.path.exists(save_path):
                os.remove(save_path)
            flash(msg, "danger")

    return render_template("register.html")

# --- Daily Mobile Self-Attendance Page ---
@app.route("/checkin")
def mobile_checkin_page():
    code = request.args.get("code", "").strip().upper()
    active_session = get_current_active_session()

    if not active_session:
        return render_template("session_expired.html", msg="Attendance session is currently CLOSED by the instructor.")
    
    if active_session["session_code"] != code:
        return render_template("session_expired.html", msg="Invalid or Expired Attendance Link! Please ask your teacher for today's new link.")

    return render_template("mobile_checkin.html", session_code=code)

# --- Mobile Face Verification API ---
@app.route("/api/verify-mobile-attendance", methods=["POST"])
def verify_mobile_attendance():
    active_session = get_current_active_session()
    if not active_session:
        return jsonify({"success": False, "message": "Attendance session is currently CLOSED!"})

    data = request.get_json()
    roll_number = data.get("roll_number", "").strip().upper()
    code = data.get("session_code", "").strip().upper()
    image_b64 = data.get("image", "")

    if active_session["session_code"] != code:
        return jsonify({"success": False, "message": "Session expired or invalid code!"})

    if not roll_number or not image_b64:
        return jsonify({"success": False, "message": "Roll Number and Face image required!"})

    today = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, department FROM students WHERE roll_number = ?", (roll_number,))
    student = cursor.fetchone()
    if not student:
        conn.close()
        return jsonify({"success": False, "message": f"Roll Number {roll_number} not registered in system!"})

    cursor.execute("SELECT id FROM attendance WHERE student_id = ? AND date = ?", (student["id"], today))
    if cursor.fetchone():
        conn.close()
        return jsonify({"success": False, "message": f"⚠️ {student['name']}, you are ALREADY marked Present today!"})

    cursor.execute("SELECT encoding_json FROM face_encodings WHERE student_id = ?", (student["id"],))
    encoding_row = cursor.fetchone()
    if not encoding_row:
        conn.close()
        return jsonify({"success": False, "message": "No face biometric registered for this student!"})

    registered_vector = np.array(json.loads(encoding_row["encoding_json"]))
    temp_path = os.path.join(Config.UPLOAD_FOLDER, f"temp_{roll_number}.jpg")

    try:
        header, encoded = image_b64.split("base64,", 1)
        with open(temp_path, "wb") as f:
            f.write(base64.b64decode(encoded))

        live_vector, err = face_engine.extract_encoding_from_image(temp_path)
        if err:
            return jsonify({"success": False, "message": err})

        is_match = False
        confidence = 0.0

        if USE_DLIB:
            import face_recognition
            dist = face_recognition.face_distance([registered_vector], live_vector)[0]
            is_match = (dist <= Config.RECOGNITION_TOLERANCE)
            confidence = max(0.0, (1.0 - dist)) * 100
        else:
            sim = np.dot(registered_vector, live_vector)
            is_match = (sim >= 0.70)
            confidence = min(100.0, max(0.0, sim * 100))

        if not is_match:
            return jsonify({"success": False, "message": "❌ Face does NOT match! Proxy attempt rejected."})

        cursor.execute("""
            INSERT INTO attendance (student_id, roll_number, name, department, date, time, status, confidence)
            VALUES (?, ?, ?, ?, ?, ?, 'Present', ?)
        """, (student["id"], roll_number, student["name"], student["department"], today, current_time, round(confidence, 2)))
        conn.commit()

        try:
            import winsound
            winsound.Beep(1200, 200)
        except Exception:
            pass

        return jsonify({
            "success": True,
            "message": f"🎉 Attendance Marked! Welcome, {student['name']}.",
            "time": current_time
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        conn.close()

# --- Manage CRs (Main Admin Only) ---
@app.route("/manage-crs", methods=["GET", "POST"])
@login_required
@superadmin_required
def manage_crs():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if username and password:
            success, msg = add_new_cr(username, password)
            flash(msg, "success" if success else "danger")
        return redirect(url_for("manage_crs"))

    crs = get_all_crs()
    return render_template("manage_crs.html", crs=crs)

@app.route("/delete-cr/<int:cr_id>", methods=["POST"])
@login_required
@superadmin_required
def delete_cr(cr_id):
    delete_cr_by_id(cr_id)
    flash("CR access revoked successfully.", "info")
    return redirect(url_for("manage_crs"))

# --- Student Directory & Actions ---
@app.route("/students")
@login_required
def students_list():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students ORDER BY roll_number ASC")
    students = cursor.fetchall()
    conn.close()
    return render_template("students.html", students=students)

@app.route("/students/delete/<int:student_id>", methods=["POST"])
@login_required
def delete_student(student_id):
    if session.get("admin_role") == "cr":
        flash("Permission Denied: Only Main Admin can delete students.", "danger")
        return redirect(url_for("students_list"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT photo_path FROM students WHERE id = ?", (student_id,))
    student = cursor.fetchone()
    
    if student:
        if student["photo_path"]:
            full_path = os.path.join(Config.UPLOAD_FOLDER, student["photo_path"])
            if os.path.exists(full_path):
                os.remove(full_path)
        cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()
        face_engine.reload_known_faces()
        flash("Student removed successfully.", "success")
    conn.close()
    return redirect(url_for("students_list"))

# --- Live Recognition Kiosk ---
@app.route("/mark-attendance")
@login_required
def mark_attendance_page():
    return render_template("mark_attendance.html")

@app.route("/video_feed")
@login_required
def video_feed():
    return Response(generate_video_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

# --- Attendance Records & Filter ---
@app.route("/attendance")
@login_required
def attendance_logs():
    filter_date = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    search_query = request.args.get("search", "").strip()
    filter_dept = request.args.get("dept", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM attendance WHERE 1=1"
    params = []

    if filter_date:
        query += " AND date = ?"
        params.append(filter_date)
    if search_query:
        query += " AND (name LIKE ? OR roll_number LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])
    if filter_dept:
        query += " AND department = ?"
        params.append(filter_dept)

    query += " ORDER BY time DESC"
    cursor.execute(query, params)
    records = cursor.fetchall()

    cursor.execute("SELECT DISTINCT department FROM students")
    departments = [r["department"] for r in cursor.fetchall()]
    conn.close()

    return render_template(
        "attendance.html",
        records=records,
        filter_date=filter_date,
        search_query=search_query,
        filter_dept=filter_dept,
        departments=departments
    )

# --- Excel & CSV Export ---
@app.route("/attendance/export")
@login_required
def export_attendance():
    fmt = request.args.get("format", "csv").lower()
    filter_date = request.args.get("date", "")
    filter_dept = request.args.get("dept", "")

    conn = get_db_connection()
    query = "SELECT roll_number, name, department, date, time, status, confidence FROM attendance WHERE 1=1"
    params = []
    if filter_date:
        query += " AND date = ?"
        params.append(filter_date)
    if filter_dept:
        query += " AND department = ?"
        params.append(filter_dept)

    query += " ORDER BY date DESC, time DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    filename = f"attendance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    if fmt == "excel":
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Attendance")
        output.seek(0)
        return send_file(output, download_name=f"{filename}.xlsx", as_attachment=True,
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        output = io.StringIO()
        df.to_csv(output, index=False)
        return Response(output.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment;filename={filename}.csv"})

# --- Recent Log Polling API ---
@app.route("/api/recent-attendance")
@login_required
def api_recent_attendance():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, roll_number, time, status FROM attendance WHERE date = ? ORDER BY time DESC LIMIT 5", (today,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(rows)

if __name__ == "__main__":
    print("[SERVER] Starting Smart Face Recognition Attendance System on http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)