# 🎓 VisionAttend - AI Face Attendance System

A modern, enterprise-grade facial recognition attendance management system built with **Python Flask**, **dlib / face_recognition**, and **OpenCV**.

---

## ✨ Key Features

- **Autonomous Facial Biometric Recognition:** Sub-200ms recognition latency powered by ResNet 128-dimensional landmark embeddings.
- **Smart Classroom Kiosk:** Real-time multi-face tracking with live bounding boxes, match confidence scores, and automatic audio voice announcements.
- **Anti-Proxy & Duplicate Prevention:** Restricts students to one check-in per calendar date; verifies live selfies against enrolled facial landmarks for mobile check-ins.
- **Student Attendance Self-Service Portal (`/my-attendance`):** Roll number self-lookup showing attendance percentages, safe-zone examination eligibility indicators (75%+), and timestamped audit logs.
- **Role-Based Access Control (RBAC):** Granular access levels for Super Administrators, Faculty, and Class Representatives (CRs).
- **Hybrid Cloud & Local Architecture:** Runs 100% offline out-of-the-box with local SQLite and disk storage; supports **Google Firebase** and **Turso Cloud LibSQL** database synchronization.
- **Instant Excel & CSV Export:** Download comprehensive formatted spreadsheets filtered by date and department.

---

## 🚀 Quick Start Guide

### 1.Set Up Environment

```bash

# Create and activate virtual environment
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\activate

# Linux / macOS:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create your local `.env` file from the example template:

```bash
cp .env.example .env
```

### 4. Run the Application

```bash
python app.py
```

Or double-click `run.bat` on Windows.

Open your browser at: **[http://localhost:5000](http://localhost:5000)**

---

## 👥 How to Use

### 1. Student Attendance Portal (`/my-attendance`)
- Enter student Roll Number.
- View total classes held, classes attended, and current turnout percentage.
- Real-time **Examination Eligibility Status** (🟢 Safe Zone >= 75% or 🔴 Shortage Warning < 75%).
- Detailed timestamped log of every verified class check-in.

### 2. Student Enrollment (`/register`)
- Enter student Roll Number, Name, Department, and Semester.
- Capture a live selfie via camera or upload a clear front-facing photograph.
- The 128-dimensional biometric vector is extracted and securely stored.

### 3. Live Recognition Kiosk (`/mark-attendance`)
- Position the camera towards entering students.
- System detects and matches faces in real time.
- Voice feedback automatically announces the student's name on successful check-in.

### 4. Mobile Check-In Sessions (`/checkin`)
- Faculty generates a temporary dynamic session token from the Dashboard.
- Students open the check-in URL on their smartphones, enter their Roll Number, and take a live selfie.
- AI validates facial similarity to ensure physical attendance without proxy.

### 5. Reports & Analytics (`/attendance`)
- View attendance trends and branch-wise distributions.
- Export filtered audit reports as **CSV** or formatted **Excel (.xlsx)** spreadsheets.

---

## ☁️ Cloud Architecture & Hybrid Sync (Optional)

The application operates 100% offline with zero cloud dependencies. For distributed deployments, configure the following in `.env`:

### 1. Turso Cloud Database (LibSQL)
- Distributed cloud database synchronized with local SQLite.
- Configure `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` in `.env`.

### 2. Google Firebase Storage
- Cloud object storage for enrolled student photographs.
- Configure `FIREBASE_STORAGE_BUCKET`, `FIREBASE_API_KEY`, and `FIREBASE_PROJECT_ID` in `.env`.

---

## 🔒 Biometric Privacy & Security

- **Landmark Vectors:** Facial representations are stored as serialized 128-dimensional floating-point vectors, which cannot be reverse-engineered into original photographs.
- **Local Autonomy:** When running in local mode, no biometric data leaves the institutional server.
- **Cryptographic Hashing:** All system passwords are protected using PBKDF2 with SHA-256 password hashing.
- **Session Protection:** Configurable inactivity timeouts and CSRF protections.

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).
