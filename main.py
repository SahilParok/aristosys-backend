"""
ARISTOSYS FASTAPI BACKEND - DIRECT HTTP VERSION
Uses direct HTTP calls to Supabase to avoid DNS issues
"""

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional
import os
import httpx
import tempfile
import fitz

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
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# HTTP client
http_client = httpx.AsyncClient(timeout=30.0)

# Models
class UserSignup(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Endpoints
@app.get("/")
async def root():
    return {"status": "Aristosys API Running", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "supabase_url": SUPABASE_URL,
        "key_configured": SUPABASE_ANON_KEY is not None
    }

@app.post("/api/auth/signup")
async def signup(data: UserSignup):
    try:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise HTTPException(500, "Supabase not configured")
        
        # Direct HTTP call to Supabase Auth API
        auth_url = f"{SUPABASE_URL}/auth/v1/signup"
        
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json"
        }
        
        payload = {
            "email": data.email,
            "password": data.password,
            "data": {
                "full_name": data.full_name or data.email.split("@")[0]
            }
        }
        
        print(f"Calling: {auth_url}")
        
        response = await http_client.post(auth_url, headers=headers, json=payload)
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            if result.get("user"):
                return {
                    "success": True,
                    "message": "Account created successfully!",
                    "user": {
                        "id": result["user"]["id"],
                        "email": result["user"]["email"]
                    }
                }
        
        # Handle error response
        error_data = response.json() if response.status_code != 500 else {}
        error_msg = error_data.get("msg") or error_data.get("message") or "Signup failed"
        raise HTTPException(400, error_msg)
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Signup error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Signup error: {str(e)}")

@app.post("/api/auth/login")
async def login(data: UserLogin):
    try:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise HTTPException(500, "Supabase not configured")
        
        # Direct HTTP call to Supabase Auth API
        auth_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
        
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json"
        }
        
        payload = {
            "email": data.email,
            "password": data.password
        }
        
        response = await http_client.post(auth_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "access_token": result["access_token"],
                "user": {
                    "id": result["user"]["id"],
                    "email": result["user"]["email"]
                }
            }
        
        error_data = response.json() if response.status_code != 500 else {}
        error_msg = error_data.get("error_description") or error_data.get("msg") or "Invalid credentials"
        raise HTTPException(401, error_msg)
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Login error: {str(e)}")

@app.on_event("shutdown")
async def shutdown():
    await http_client.aclose()

# Helper
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
