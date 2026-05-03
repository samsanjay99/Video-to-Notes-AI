<div align="center">

# 🎙️ MeetMind — AI Meeting Notes

**Transform any meeting recording into structured, actionable notes in minutes.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://neon.tech)
[![Gemini AI](https://img.shields.io/badge/Gemini-2.5_Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://aistudio.google.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)

[✨ Features](#-features) · [🚀 Quick Start](#-quick-start) · [🌐 Deploy](#-deployment) · [📡 API Docs](#-api-reference)

![MeetMind Dashboard](https://placehold.co/900x480/0d0d14/6366f1?text=MeetMind+%E2%80%94+AI+Meeting+Notes&font=raleway)

</div>

---

## ✨ Features

| Feature | Description |
|---|---|
| 🎤 **AI Transcription** | Upload audio/video → get a full speaker-diarized transcript via Gemini 2.5 Flash |
| 📋 **Smart Summaries** | Auto-generated overview, key discussion points, and topics |
| ✅ **Action Items** | Extracted tasks with assignees, priorities, and due dates |
| 👥 **Participant Detection** | Identifies speakers and their roles automatically |
| ▶️ **YouTube Support** | Paste any YouTube URL — audio is extracted and processed |
| 📄 **Export** | Download notes as polished **PDF** or **DOCX** |
| 🔗 **Public Sharing** | Share a read-only link to any meeting — no login required |
| 🎭 **Demo Mode** | Fully functional without an API key using sample data |
| 📱 **Responsive UI** | Clean dark-theme interface that works on desktop and mobile |

---

## 🛠️ Tech Stack

```
Backend   →  Flask 3.1 · SQLAlchemy · PostgreSQL (Neon)
AI        →  Google Gemini 2.5 Flash (transcription + analysis)
Auth      →  JWT (PyJWT) · bcrypt
Media     →  yt-dlp · ffmpeg (YouTube + video-to-audio)
Export    →  ReportLab (PDF) · python-docx (DOCX)
Frontend  →  Jinja2 · Vanilla JS · Custom dark CSS
Deploy    →  Render / Gunicorn
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL database (or free [Neon](https://neon.tech) cloud DB)
- [ffmpeg](https://ffmpeg.org/download.html) installed and on PATH *(for video/YouTube support)*
- Google Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey) *(optional — app runs in demo mode without it)*

### 1. Clone the repo

```bash
git clone https://github.com/samsanjay99/Video-to-Notes-AI.git
cd Video-to-Notes-AI
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
# PostgreSQL connection string (Neon, Supabase, or local)
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require

# Strong random secret for JWT signing
JWT_SECRET=your_super_secret_key_here

# Google Gemini API key (leave blank to use demo mode)
GEMINI_API_KEY=your_gemini_api_key_here

FLASK_ENV=development
PORT=5000
FRONTEND_URL=http://localhost:5000
```

### 5. Run the app

```bash
python app.py
```

Open **http://localhost:5000** — the database tables are created automatically on first run.

> **Demo account:** `demo@meetmind.ai` / `demo123`

---

## 📁 Project Structure

```
Video-to-Notes-AI/
├── app.py                  # Flask app factory & page routes
├── extensions.py           # SQLAlchemy instance
├── requirements.txt
├── .env.example
│
├── models/
│   ├── user.py             # User model (bcrypt auth)
│   └── meeting.py          # Meeting model (JSON fields)
│
├── routes/
│   ├── auth.py             # /api/auth  — register, login, profile
│   ├── meetings.py         # /api/meetings — CRUD, stats, sharing
│   ├── upload.py           # /api/upload  — file & YouTube ingestion
│   └── export.py           # /api/export  — PDF & DOCX generation
│
├── services/
│   └── ai_service.py       # Gemini transcription + analysis + demo mode
│
├── middleware/
│   └── auth.py             # JWT @auth_required decorator
│
├── templates/              # Jinja2 HTML pages
│   ├── base.html           # Sidebar layout shell
│   ├── dashboard.html
│   ├── upload.html
│   ├── history.html
│   ├── meeting_detail.html
│   ├── shared.html         # Public share view (no auth)
│   ├── login.html
│   └── register.html
│
└── static/
    ├── css/style.css       # Dark theme with CSS variables
    └── js/
        ├── api.js          # Fetch wrapper + JWT auth + upload progress
        └── helpers.js      # Formatting, toasts, utilities
```

---

## 🔄 How It Works

```
User uploads file / YouTube URL
        │
        ▼
  Meeting record created  ──►  Immediate response to browser
        │
        ▼  (background thread)
  ┌─────────────────────────────────────┐
  │  1. transcribing  →  Gemini API     │
  │     • Full transcript               │
  │     • Speaker diarization           │
  │                                     │
  │  2. analyzing  →  Gemini API        │
  │     • Summary + key points          │
  │     • Action items + assignees      │
  │     • Participants + tags           │
  └─────────────────────────────────────┘
        │
        ▼
  status: completed  ◄──  Frontend polls /status every 3s
```

---

## 📡 API Reference

### Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Create account |
| `POST` | `/api/auth/login` | Login → JWT token |
| `GET` | `/api/auth/me` | Current user info |
| `PUT` | `/api/auth/profile` | Update name / preferences |

### Meetings

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/meetings/` | List meetings (paginated, searchable) |
| `GET` | `/api/meetings/stats/overview` | Dashboard stats |
| `GET` | `/api/meetings/:id` | Meeting detail |
| `GET` | `/api/meetings/:id/status` | Processing status (for polling) |
| `PUT` | `/api/meetings/:id` | Update title / tags |
| `PATCH` | `/api/meetings/:id/action-items/:itemId` | Toggle / update action item |
| `POST` | `/api/meetings/:id/share` | Generate public share link |
| `DELETE` | `/api/meetings/:id` | Delete meeting |
| `GET` | `/api/meetings/shared/:token` | Public shared view |

### Upload & Export

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload/` | Upload audio/video file or YouTube URL |
| `GET` | `/api/export/:id/pdf` | Download meeting as PDF |
| `GET` | `/api/export/:id/docx` | Download meeting as DOCX |

All endpoints except `/api/auth/register`, `/api/auth/login`, and `/api/meetings/shared/:token` require:
```
Authorization: Bearer <jwt_token>
```

---

## 🌐 Deployment

### Deploy on Render *(recommended — free tier available)*

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → **New Web Service**
3. Connect your GitHub repo
4. Set the following:

| Setting | Value |
|---------|-------|
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:create_app()` |

5. Add environment variables in the Render dashboard:

```
DATABASE_URL      = your_neon_or_postgres_url
JWT_SECRET        = a_long_random_secret
GEMINI_API_KEY    = your_gemini_key
FLASK_ENV         = production
FRONTEND_URL      = https://your-app.onrender.com
```

6. Click **Deploy** — done! 🎉

> **Note:** Vercel is not suitable for this app because it runs serverless functions with no persistent filesystem and no long-running threads (needed for background audio processing). Render's always-on web service is the right fit.

### Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `JWT_SECRET` | ✅ | Secret key for signing JWT tokens |
| `GEMINI_API_KEY` | ⚪ | Google Gemini key (demo mode if omitted) |
| `FLASK_ENV` | ⚪ | `development` or `production` |
| `PORT` | ⚪ | Port to listen on (default: `5000`) |
| `FRONTEND_URL` | ⚪ | Base URL used in share links |

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'Add my feature'`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

---

## 📄 License

MIT © [samsanjay99](https://github.com/samsanjay99)

---

<div align="center">
  Built with ❤️ using Flask + Gemini AI
</div>
