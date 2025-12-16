# Aristosys Backend API

FastAPI backend for Aristosys recruitment platform.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in your API keys

3. Run locally:
```bash
uvicorn main:app --reload
```

## Deploy to Railway

1. Push code to GitHub
2. Connect Railway to your repo
3. Add environment variables in Railway dashboard
4. Railway will auto-deploy

API will be live at: https://your-app.railway.app
