# 🧠 Smart Interview System

An AI-powered interview preparation platform built with Flask, MySQL, and Google Gemini AI.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Database Setup](#database-setup)
- [Running the App](#running-the-app)
- [User Roles](#user-roles)
- [API Integration](#api-integration)
- [Screenshots](#screenshots)

---

## 🌟 Overview

Smart Interview System is a full-stack web application that helps candidates prepare for job interviews using AI. The system allows candidates to upload their resumes, get AI-powered resume scores, and take mock interviews with real-time AI feedback and scoring.

---

## ✨ Features

### 👤 Candidate
- Register and login securely
- Upload resume (PDF/DOCX) — max 5MB
- Get AI-powered resume analysis:
  - Overall Score
  - Technical Score
  - Experience Score
  - Education Score
  - Skills extraction
- Take mock interviews (5 questions)
- Get real-time AI feedback on each answer
- View detailed result with score ring

### 🧑‍💼 Interviewer
- Login with interviewer credentials
- View all candidate interview sessions
- View detailed answers and AI feedback per session
- Track completed vs in-progress interviews

### 🛡️ Admin
- Full system overview dashboard
- View all users, resumes, interviews
- Delete users (cascade delete)
- Real-time stats: total users, resumes, interviews, completed sessions

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, Flask 3.x |
| Database | MySQL 9.x |
| AI | Google Gemini API (gemini-2.0-flash-lite) |
| PDF Parsing | pdfplumber |
| Auth | Werkzeug password hashing |
| Frontend | HTML5, CSS3, Bootstrap Icons |
| Fonts | Instrument Serif, DM Sans (Google Fonts) |
| Design | Glassmorphism, Dark Theme |

---

## 📁 Project Structure

```
smart_interview_system/
├── run.py                          # App entry point
├── config.py                       # Configuration (loads .env)
├── database.py                     # MySQL connection pool
├── requirements.txt                # Python dependencies
├── .env                            # Environment variables (not in git)
├── .env.example                    # Example env file
├── .gitignore
│
└── app/
    ├── __init__.py                 # App factory, blueprint registration
    │
    ├── static/
    │   ├── css/style.css           # Global dark theme styles
    │   └── uploads/                # Uploaded resume files
    │
    ├── templates/
    │   ├── base.html               # Base template
    │   ├── auth/
    │   │   ├── login.html          # Login page (3 role buttons)
    │   │   ├── register.html       # Register page
    │   │   └── dashboard.html      # Candidate dashboard
    │   ├── resume/
    │   │   ├── upload.html         # Resume upload page
    │   │   └── list.html           # Resume list with AI scores
    │   ├── interview/
    │   │   ├── start.html          # Interview start page
    │   │   ├── question.html       # Question page with progress bar
    │   │   └── result.html         # Result page with score ring
    │   ├── interviewer/
    │   │   ├── dashboard.html      # Interviewer dashboard
    │   │   └── session.html        # Session detail view
    │   └── admin/
    │       └── dashboard.html      # Admin dashboard
    │
    ├── auth/
    │   └── routes.py               # Login, Register, Dashboard, Logout
    │
    ├── resume/
    │   └── routes.py               # Upload, List, Delete resume
    │
    ├── interview/
    │   └── routes.py               # Start, Question, Result flow
    │
    ├── interviewer/
    │   └── routes.py               # Interviewer dashboard, Session view
    │
    ├── admin/
    │   └── routes.py               # Admin dashboard, Delete user
    │
    ├── models/
    │   ├── user.py                 # User DB functions
    │   ├── resume.py               # Resume DB functions
    │   └── admin.py                # Admin DB functions
    │
    └── ai_services/
        ├── gemini.py               # Gemini AI client (legacy)
        ├── resume_analyzer.py      # Resume parse + score
        ├── answer_evaluator.py     # Interview answer scoring
        └── prompt_templates.py     # All AI prompts
```

---

## ⚙️ Installation

### Prerequisites
- Python 3.10+
- MySQL 8.x or 9.x
- Git

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/smart-interview-system.git
cd smart-interview-system

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

---

## 🔧 Configuration

Create a `.env` file in the root directory:

```env
FLASK_ENV=development
FLASK_DEBUG=true
SECRET_KEY=your-secret-key-here

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-mysql-password
MYSQL_DATABASE=smart_interview_db

GEMINI_API_KEY=your-gemini-api-key
```

Get your Gemini API key from: https://aistudio.google.com

---

## 🗄️ Database Setup

```bash
# Create database
mysql -u root -p -e "CREATE DATABASE smart_interview_db;"

# Run migrations
mysql -u root -p smart_interview_db < migrations/create_tables.sql
mysql -u root -p smart_interview_db < migrations/interview_tables.sql

# Add AI score columns
mysql -u root -p -e "ALTER TABLE smart_interview_db.resumes
  ADD COLUMN overall_score INT DEFAULT 0,
  ADD COLUMN technical_score INT DEFAULT 0,
  ADD COLUMN experience_score INT DEFAULT 0,
  ADD COLUMN education_score INT DEFAULT 0,
  ADD COLUMN skills TEXT,
  ADD COLUMN strengths TEXT,
  ADD COLUMN improvements TEXT;"

# Set admin role
mysql -u root -p -e "UPDATE smart_interview_db.users SET role='admin' WHERE email='your@email.com';"

# Update role enum
mysql -u root -p -e "ALTER TABLE smart_interview_db.users MODIFY COLUMN role ENUM('admin','interviewer','candidate') DEFAULT 'candidate';"
```

---

## 🚀 Running the App

```bash
python run.py
```

Open browser: http://127.0.0.1:5000

---

## 👥 User Roles

| Role | Access | Default Redirect |
|---|---|---|
| `admin` | Full system control | `/admin/dashboard` |
| `interviewer` | View all interviews + sessions | `/interviewer/dashboard` |
| `candidate` | Resume upload + take interview | `/auth/dashboard` |

### Default Test Accounts

| Role | Email | Password |
|---|---|---|
| Admin | ssaikumar99513@gmail.com | your-password |
| Interviewer | interviewer@test.com | Interview@123 |
| Candidate | Register at /auth/register | — |

---

## 🤖 API Integration

### Google Gemini AI

Used for:
1. **Resume Analysis** — Extract skills, experience, education from PDF
2. **Resume Scoring** — Score technical, experience, education out of 100
3. **Answer Evaluation** — Score interview answers with detailed feedback

Model used: `gemini-2.0-flash-lite`

---

## 🎨 Design System

| Element | Value |
|---|---|
| Background | `#080b14` |
| Primary | `#0affed` (teal) |
| Secondary | `#6366f1` (indigo) |
| Success | `#10b981` (green) |
| Warning | `#f59e0b` (amber) |
| Danger | `#ef4444` (red) |
| Fonts | Instrument Serif + DM Sans |
| Style | Glassmorphism + Dark theme |

---

## 📦 Dependencies

```
flask
flask-mysqldb
python-dotenv
werkzeug
pdfplumber
google-genai
gunicorn
```

---

## 🔮 Roadmap

- [ ] Camera + Voice based interview
- [ ] Resume-based question generation
- [ ] Dashboard live analytics
- [ ] Google OAuth login
- [ ] Email notifications
- [ ] Deploy to Railway/Render

---

## 👨‍💻 Developer

**Saikumar**
- Email: ssaikumar99513@gmail.com
- Project: BCA Final Year Project

---

## 📄 License

MIT License — Free to use for educational purposes.