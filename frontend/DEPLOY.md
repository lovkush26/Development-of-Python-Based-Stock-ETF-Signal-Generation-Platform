# AlphaSignal React UI — Deployment Guide

## Local Development

### Prerequisites
- Node.js 18+  (https://nodejs.org)
- Python backend running on port 8000

### Setup
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:3000

The Vite dev server proxies /api → http://localhost:8000 automatically.

---

## Option 1 — Deploy to Render.com (Recommended, Free tier)

### Deploy Backend (FastAPI)

1. Go to https://render.com → New → Web Service
2. Connect your GitHub repo
3. Settings:
   - Name: `alphasignal-api`
   - Root Directory: `.` (repo root)
   - Runtime: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn dashboard.api:app --host 0.0.0.0 --port $PORT`
4. Add Environment Variables (copy from .env):
   - DATABASE_URL (use Render PostgreSQL)
   - TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, etc.
5. Click Deploy

### Deploy Frontend (React)

1. Go to Render → New → Static Site
2. Connect same GitHub repo
3. Settings:
   - Name: `alphasignal-ui`
   - Root Directory: `frontend`
   - Build Command: `npm install && npm run build`
   - Publish Directory: `dist`
4. Add Environment Variable:
   - `VITE_API_URL` = `https://alphasignal-api.onrender.com/api`
5. Click Deploy

---

## Option 2 — Deploy to Railway.app

### One-command deploy
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Deploy backend
railway up --service backend

# Deploy frontend
cd frontend
railway up --service frontend
```

### railway.toml (already included)
Backend and frontend are separate services in Railway.

---

## Option 3 — Deploy to VPS (DigitalOcean / AWS / any Linux server)

### Requirements
- Ubuntu 22.04 server
- Docker + Docker Compose installed
- Domain name pointing to server IP

### Steps
```bash
# 1. SSH into server
ssh root@your-server-ip

# 2. Clone repo
git clone https://github.com/yourname/alphasignal.git
cd alphasignal

# 3. Configure environment
cp .env.example .env
nano .env  # fill in all keys

# 4. Build and start all services
cd docker
docker-compose up -d --build

# 5. Check everything is running
docker-compose ps

# Services running:
#   alphasignal_nginx     → :80  (public)
#   alphasignal_backend   → :8000 (internal)
#   alphasignal_frontend  → :80  (internal)
#   alphasignal_db        → :5432 (internal)
#   alphasignal_redis     → :6379 (internal)
#   alphasignal_worker    (Celery)
#   alphasignal_beat      (Scheduler)
```

### SSL with Let's Encrypt
```bash
apt install certbot python3-certbot-nginx
certbot --nginx -d yourdomain.com
```

---

## Option 4 — Vercel (Frontend only) + Render (Backend)

### Frontend on Vercel
```bash
cd frontend
npm install -g vercel
vercel

# Set env variable in Vercel dashboard:
# VITE_API_URL = https://your-render-api.onrender.com/api
```

### Backend on Render
Same as Option 1 backend steps above.

---

## Environment Variables Required for Production

| Variable | Description |
|----------|-------------|
| DATABASE_URL | PostgreSQL connection string |
| TWILIO_ACCOUNT_SID | SMS alerts |
| TWILIO_AUTH_TOKEN | SMS alerts |
| TWILIO_FROM_NUMBER | Your Twilio number |
| SENDGRID_API_KEY | Email alerts |
| SLACK_BOT_TOKEN | Slack alerts (optional) |
| APP_ENV | Set to `production` |
| APP_SECRET_KEY | Random secret string |
