# 🎓 VisionAttend - AI Face Attendance System

A modern, full-stack facial recognition attendance management system built with **Python Flask**, **dlib / face_recognition**, and **OpenCV**.

---

## 🚀 Quick Start (For New Users)

### Option 1: 1-Click Launch (Windows)
Simply double-click `run.bat` in the project root folder, or in your terminal:
```cmd
.\run.bat
```

### Option 2: Run via Terminal
Make sure to run with the project's virtual environment (`venv`) where all dependencies (`dlib`, `face_recognition`, `OpenCV`) are installed:

#### **PowerShell:**
```powershell
cd d:\DONE_Project\face-attendance-system
.\venv\Scripts\python.exe app.py
```

#### **Command Prompt (CMD):**
```cmd
cd /d d:\DONE_Project\face-attendance-system
venv\Scripts\python.exe app.py
```

---

## 🔑 Login Credentials

- **URL:** [http://127.0.0.1:5000](http://127.0.0.1:5000)
- **Super Admin Username:** `admin`
- **Super Admin Password:** `admin123`

---

## 👥 How to Use

### 1. Student Attendance Self-Service Portal (`/my-attendance`)
Students can check their own real-time attendance report anytime:
- Enter Roll Number.
- Shows total classes held, classes attended, classes absent.
- Real-time **Examination Eligibility Status** (🟢 Safe Zone >= 75% or 🔴 Shortage Warning < 75%).
- Timestamped logs of every class check-in with biometric match confidence.

### 2. Register a New Student Face (`/register`)
1. Go to **Students** ➔ **Enroll New Student** (or directly `/register`).
2. Enter Roll Number, Full Name, Department, and Semester.
3. Open the camera to capture a live selfie or upload a front-facing photo.
4. Click **Complete Face Enrollment**.
5. The 128-dimensional facial embedding is extracted and saved to SQLite database.

### 2. Mark Attendance (Live Scanner Kiosk)
1. Go to **Live Scanner** (`/mark-attendance`).
2. Point your camera at students.
3. When recognized:
   - Visual bounding box with name, roll number, and confidence percentage.
   - Immediate audio chime and voice announcement (*"Attendance marked for [Name]"*).
   - Duplicate prevention stops multiple check-ins on the same day.

### 3. Mark Attendance (Mobile Self-Checkin)
1. On the **Dashboard**, click **Generate New Daily Link**.
2. Share the generated code (or URL: `http://<YOUR_IP>:5000/checkin?code=XXXXXX`) with students.
3. Students open the link on their smartphone, enter their Roll Number, and take a selfie.
4. AI verifies the selfie against their registered face to prevent proxy attendance.

### 4. Manage Class Representatives (CRs)
- Super Admins can create sub-admin accounts for Class Representatives (`/manage-crs`).
- CRs can run the scanner and view attendance, but cannot delete records or manage other admin accounts.

### 5. Export Reports
- Navigate to **Reports** (`/attendance`).
- Filter by date or department.
- Export as **CSV** or formatted **Excel (.xlsx)** spreadsheet.

---

## 🛠️ Fresh Installation (If Setting Up on a New PC)

```bash
# 1. Clone repository & create venv
python -m venv venv

# 2. Activate venv
.\venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start app
python app.py
```

---

## ☁️ Optional Cloud Integrations (Firebase & Turso)

Project supports automatic hybrid mode: runs 100% offline with local storage, and seamlessly connects to cloud when credentials are added in `.env`:

### 1. Google Firebase Storage (For Student Photos):
1. Create a free project on [Firebase Console](https://console.firebase.google.com).
2. Enable **Storage**.
3. In **Project Settings ➔ Service Accounts**, click **Generate new private key** and save it as `firebase_credentials.json` in the project root.
4. Set `FIREBASE_STORAGE_BUCKET=your-bucket.appspot.com` in `.env`.

### 2. Turso Cloud Database (For Attendance Records & Biometrics):
1. Create free cloud SQLite database at [turso.tech](https://turso.tech).
2. Copy your database URL and token into `.env`:
   ```env
   TURSO_DATABASE_URL=libsql://your-db.turso.io
   TURSO_AUTH_TOKEN=your-token-here
   ```

