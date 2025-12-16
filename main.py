"""
ARISTOSYS FASTAPI BACKEND - FIXED
Production API for Aristosys recruitment platform
"""

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
import os
import json
import tempfile
import anthropic
from supabase import create_client, Client
from deepgram import DeepgramClient, PrerecordedOptions
import fitz
import re

app = FastAPI(title="Aristosys API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")  # For auth operations
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # For database operations
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

supabase_auth = None  # For auth operations
supabase_db = None    # For database operations
claude_client = None
deepgram_client = None

@app.on_event("startup")
async def startup():
    global supabase_auth, supabase_db, claude_client, deepgram_client
    
    # Auth client with anon key
    if SUPABASE_URL and SUPABASE_ANON_KEY:
        supabase_auth = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    
    # Database client with service key
    if SUPABASE_URL and SUPABASE_SERVICE_KEY:
        supabase_db = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    if ANTHROPIC_API_KEY:
        claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    if DEEPGRAM_API_KEY:
        deepgram_client = DeepgramClient(DEEPGRAM_API_KEY)

# Models
class UserSignup(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Auth
async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing authorization")
    token = authorization.replace("Bearer ", "")
    try:
        user_response = supabase_auth.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(401, "Invalid token")
        user_data = supabase_db.table("users").select("*, companies(*)").eq("id", user_response.user.id).single().execute()
        return user_data.data
    except Exception as e:
        raise HTTPException(401, f"Auth failed: {str(e)}")

# Endpoints
@app.get("/")
async def root():
    return {"status": "Aristosys API Running", "version": "1.0.0"}

@app.post("/api/auth/signup")
async def signup(data: UserSignup):
    try:
        if not supabase_auth:
            raise HTTPException(500, "Supabase not configured")
        
        response = supabase_auth.auth.sign_up({
            "email": data.email,
            "password": data.password,
            "options": {
                "data": {
                    "full_name": data.full_name or data.email.split("@")[0]
                }
            }
        })
        
        if response.user:
            return {
                "success": True,
                "message": "Account created! Check your email to verify.",
                "user": {
                    "id": response.user.id,
                    "email": response.user.email
                }
            }
        else:
            raise HTTPException(400, "Signup failed")
    
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/api/auth/login")
async def login(data: UserLogin):
    try:
        if not supabase_auth or not supabase_db:
            raise HTTPException(500, "Supabase not configured")
        
        response = supabase_auth.auth.sign_in_with_password({
            "email": data.email,
            "password": data.password
        })
        
        if response.user and response.session:
            user_data = supabase_db.table("users").select("*, companies(*)").eq("id", response.user.id).single().execute()
            
            return {
                "success": True,
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "user": user_data.data
            }
        else:
            raise HTTPException(401, "Invalid credentials")
    
    except Exception as e:
        raise HTTPException(401, str(e))

@app.get("/api/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {"user": user}

@app.get("/api/clients")
async def get_clients(user: dict = Depends(get_current_user)):
    company_id = user.get("company_id")
    response = supabase_db.table("clients").select("*").eq("company_id", company_id).order("name").execute()
    return {"clients": response.data}

@app.get("/api/jds")
async def get_jds(client_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    company_id = user.get("company_id")
    query = supabase_db.table("saved_jds").select("*, clients(name)").eq("company_id", company_id)
    if client_id:
        query = query.eq("client_id", client_id)
    response = query.order("created_at", desc=True).execute()
    return {"jds": response.data}

@app.get("/api/candidates")
async def get_candidates(jd_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    company_id = user.get("company_id")
    query = supabase_db.table("candidates").select("*").eq("company_id", company_id)
    if jd_id:
        query = query.eq("jd_id", jd_id)
    response = query.order("created_at", desc=True).execute()
    return {"candidates": response.data}

@app.post("/api/screen")
async def screen_candidate(
    jd_id: str = Form(...),
    candidate_name: str = Form(...),
    candidate_email: Optional[str] = Form(None),
    resume: UploadFile = File(...),
    audio: Optional[UploadFile] = File(None),
    user: dict = Depends(get_current_user)
):
    company_id = user.get("company_id")
    
    # Get JD
    jd = supabase_db.table("saved_jds").select("*").eq("id", jd_id).eq("company_id", company_id).single().execute()
    if not jd.data:
        raise HTTPException(404, "JD not found")
    
    jd_data = jd.data
    jd_analysis = jd_data.get("analysis_json") or {}
    
    # Extract resume
    resume_bytes = await resume.read()
    resume_text = extract_text_pdf(resume_bytes)
    
    if not resume_text:
        raise HTTPException(400, "Could not extract resume text")
    
    # Analyze resume
    resume_score = 85  # Placeholder
    
    # Analyze audio if provided
    audio_analysis = None
    if audio:
        audio_bytes = await audio.read()
        # Transcribe and analyze here
        audio_analysis = {"technical_score": 70, "communication_score": 65}
    
    # Save candidate
    candidate_data = {
        "name": candidate_name,
        "email": candidate_email,
        "jd_id": jd_id,
        "company_id": company_id,
        "resume_score": resume_score,
        "tech_score": audio_analysis.get("technical_score") if audio_analysis else None,
        "comm_score": audio_analysis.get("communication_score") if audio_analysis else None,
        "stage": "not_submitted",
        "status": "ongoing"
    }
    
    result = supabase_db.table("candidates").insert(candidate_data).execute()
    
    return {"success": True, "candidate": result.data[0] if result.data else None, "resume_score": resume_score}

def extract_text_pdf(content: bytes) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        doc = fitz.open(tmp_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    finally:
        os.unlink(tmp_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
