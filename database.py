import sqlite3
import os
import json
import numpy as np
import random
import string
from datetime import datetime
from werkzeug.security import generate_password_hash
from config import Config

def get_db_connection():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # Safe directory creation (Prevents WinError 183)
    if os.path.exists(Config.UPLOAD_FOLDER) and not os.path.isdir(Config.UPLOAD_FOLDER):
        os.remove(Config.UPLOAD_FOLDER)
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Admins & CRs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'superadmin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    try:
        cursor.execute("ALTER TABLE admins ADD COLUMN role TEXT DEFAULT 'superadmin'")
    except sqlite3.OperationalError:
        pass

    # 2. Students Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_number TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            semester TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            photo_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. Face Encodings Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS face_encodings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            encoding_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        )
    """)

    # 4. Attendance Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            roll_number TEXT NOT NULL,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT DEFAULT 'Present',
            confidence REAL,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            UNIQUE(student_id, date)
        )
    """)

    # 5. Dynamic Daily Sessions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_code TEXT NOT NULL,
            date TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --- SECURE MAIN ADMIN INITIALIZATION FROM .ENV ---
    admin_user = getattr(Config, "ADMIN_USERNAME", None) or "admin"
    admin_pass = getattr(Config, "ADMIN_PASSWORD", None) or "admin123"

    cursor.execute("SELECT id FROM admins WHERE role = 'superadmin'")
    existing_superadmin = cursor.fetchone()

    if not existing_superadmin:
        # Create Super Admin from .env
        hashed_pw = generate_password_hash(admin_pass)
        cursor.execute("""
            INSERT INTO admins (username, password_hash, role)
            VALUES (?, ?, 'superadmin')
        """, (admin_user, hashed_pw))
        print(f"[DB] Initialized Master Admin from environment config: {admin_user}")
    else:
        # Auto-update credentials if changed in .env
        hashed_pw = generate_password_hash(admin_pass)
        cursor.execute("""
            UPDATE admins 
            SET username = ?, password_hash = ? 
            WHERE id = ?
        """, (admin_user, hashed_pw, existing_superadmin["id"]))

    conn.commit()
    conn.close()

def save_student(roll_number, name, department, semester, email, phone, photo_filename, encoding_array):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO students (roll_number, name, department, semester, email, phone, photo_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (roll_number.strip().upper(), name.strip(), department.strip(), semester.strip(), email.strip(), phone.strip(), photo_filename))
        
        student_id = cursor.lastrowid
        encoding_json = json.dumps(encoding_array.tolist())
        cursor.execute("INSERT INTO face_encodings (student_id, encoding_json) VALUES (?, ?)", (student_id, encoding_json))
        conn.commit()
        return True, "Student registered successfully!"
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, f"Roll Number '{roll_number}' is already registered."
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

def load_all_known_encodings():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, s.roll_number, s.name, s.department, fe.encoding_json
        FROM students s
        JOIN face_encodings fe ON s.id = fe.student_id
    """)
    rows = cursor.fetchall()
    conn.close()

    known_ids, known_rolls, known_names, known_depts, known_encodings = [], [], [], [], []
    for row in rows:
        known_ids.append(row["id"])
        known_rolls.append(row["roll_number"])
        known_names.append(row["name"])
        known_depts.append(row["department"])
        known_encodings.append(np.array(json.loads(row["encoding_json"])))

    return {
        "ids": known_ids, "rolls": known_rolls, "names": known_names,
        "depts": known_depts, "encodings": known_encodings
    }

def mark_attendance_in_db(student_id, roll_number, name, department, confidence=1.0):
    today_date = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO attendance (student_id, roll_number, name, department, date, time, status, confidence)
            VALUES (?, ?, ?, ?, ?, ?, 'Present', ?)
        """, (student_id, roll_number, name, department, today_date, current_time, round(confidence, 2)))
        conn.commit()

        # Hardware Beep Sound on Success
        try:
            import winsound
            winsound.Beep(1200, 250)
        except Exception:
            pass

        return "SUCCESS", f"Attendance marked for {name} ({roll_number}) at {current_time}"
    except sqlite3.IntegrityError:
        # Hardware Alert Sound on Duplicate
        try:
            import winsound
            winsound.Beep(600, 180)
        except Exception:
            pass
        return "DUPLICATE", f"{name} ({roll_number}) already checked in today."
    except Exception as e:
        return "ERROR", str(e)
    finally:
        conn.close()

# --- CR (Class Representative) Helper Functions ---
def get_all_crs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, created_at FROM admins WHERE role = 'cr' ORDER BY id DESC")
    crs = cursor.fetchall()
    conn.close()
    return crs

def add_new_cr(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        hashed = generate_password_hash(password)
        cursor.execute("INSERT INTO admins (username, password_hash, role) VALUES (?, ?, 'cr')", (username.strip(), hashed))
        conn.commit()
        return True, f"CR Account '{username}' created successfully!"
    except sqlite3.IntegrityError:
        return False, f"Username '{username}' already exists!"
    finally:
        conn.close()

def delete_cr_by_id(cr_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM admins WHERE id = ? AND role = 'cr'", (cr_id,))
    conn.commit()
    conn.close()

# --- Dynamic Daily Link & Session Controller ---
def generate_new_daily_session():
    new_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    today = datetime.now().strftime("%Y-%m-%d")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE daily_sessions SET is_active = 0")
    cursor.execute("INSERT INTO daily_sessions (session_code, date, is_active) VALUES (?, ?, 1)", (new_code, today))
    conn.commit()
    conn.close()
    return new_code

def get_current_active_session():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT session_code, created_at FROM daily_sessions WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def close_active_session():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE daily_sessions SET is_active = 0")
    conn.commit()
    conn.close()

# Ensure tables & admin are initialized
init_db()