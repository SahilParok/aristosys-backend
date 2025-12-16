"""
ARISTOSYS FASTAPI BACKEND - SIMPLE & WORKING
Production API for Aristosys recruitment platform
"""

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional
import os
import tempfile
import fitz

app = FastAPI(title="Aristosys API", version="1.0.0")

# CORS - Allow all origins for now
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

# Import supabase only if keys exist
supabase = None

@app.on_event("startup")
async def startup():
    global supabase
    if SUPABASE_URL and SUPABASE_ANON_KEY:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        print("✅ Supabase connected successfully")

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
        "supabase": "connected" if supabase else "not configured"
    }

@app.post("/api/auth/signup")
async def signup(data: UserSignup):
    try:
        if not supabase:
            raise HTTPException(500, "Database not configured")
        
        response = supabase.auth.sign_up({
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
                "message": "Account created successfully!",
                "user": {
                    "id": response.user.id,
                    "email": response.user.email
                }
            }
        else:
            raise HTTPException(400, "Signup failed")
    
    except Exception as e:
        error_msg = str(e)
        print(f"Signup error: {error_msg}")
        raise HTTPException(400, error_msg)

@app.post("/api/auth/login")
async def login(data: UserLogin):
    try:
        if not supabase:
            raise HTTPException(500, "Database not configured")
        
        response = supabase.auth.sign_in_with_password({
            "email": data.email,
            "password": data.password
        })
        
        if response.user and response.session:
            # Get user company info
            user_data = supabase.table("users").select("*, companies(*)").eq("id", response.user.id).single().execute()
            
            return {
                "success": True,
                "access_token": response.session.access_token,
                "user": user_data.data if user_data.data else {"id": response.user.id, "email": response.user.email}
            }
        else:
            raise HTTPException(401, "Invalid credentials")
    
    except Exception as e:
        error_msg = str(e)
        print(f"Login error: {error_msg}")
        raise HTTPException(401, error_msg)

# Helper function
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
