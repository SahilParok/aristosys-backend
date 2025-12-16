"""
Jobs Router
API endpoints for job description management
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List, Optional
import fitz

from ..config import get_settings, Settings
from ..services import SupabaseService, ClaudeService
from ..models.schemas import JobDescriptionResponse, JobDescriptionAnalysis


router = APIRouter(prefix="/jobs", tags=["Job Descriptions"])


def get_services(settings: Settings = Depends(get_settings)):
    """Dependency to get services."""
    return {
        "supabase": SupabaseService(settings.supabase_url, settings.supabase_key),
        "claude": ClaudeService(settings.anthropic_api_key)
    }


def extract_pdf_text(content: bytes) -> str:
    """Extract text from PDF bytes."""
    try:
        doc = fitz.open(stream=content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract PDF text: {e}")


@router.get("", response_model=List[JobDescriptionResponse])
async def list_jobs(
    services: dict = Depends(get_services)
):
    """Get all saved job descriptions."""
    jobs = services["supabase"].get_job_descriptions()
    return jobs


@router.get("/{jd_id}", response_model=JobDescriptionResponse)
async def get_job(
    jd_id: str,
    services: dict = Depends(get_services)
):
    """Get a specific job description."""
    job = services["supabase"].get_jd_by_id(jd_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job description not found")
    return job


@router.post("", response_model=JobDescriptionResponse)
async def create_job(
    title: str = Form(...),
    jd_file: Optional[UploadFile] = File(None),
    jd_text: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None),
    analyze: bool = Form(True),
    services: dict = Depends(get_services)
):
    """
    Create a new job description.
    
    Upload a PDF or provide text directly.
    Optionally analyze the JD with Claude.
    """
    # Get JD content
    if jd_file:
        content = await jd_file.read()
        if jd_file.filename.lower().endswith('.pdf'):
            text = extract_pdf_text(content)
        else:
            text = content.decode('utf-8')
    elif jd_text:
        text = jd_text
    else:
        raise HTTPException(status_code=400, detail="Provide jd_file or jd_text")
    
    # Analyze if requested
    analysis = None
    if analyze:
        # Get client preferences for analysis
        client_comments = None
        if client_id:
            client = services["supabase"].get_client_by_id(client_id)
            if client and client.get("evaluation_preferences"):
                client_comments = f"CLIENT: {client['name']}\nPREFERENCES: {client['evaluation_preferences']}"
        
        analysis = services["claude"].analyze_jd(text, client_comments)
        
        # Use analyzed title if not provided
        if not title or title == "Untitled":
            title = analysis.get("job_title", "Untitled Position")
    
    # Save to database
    jd_id = services["supabase"].save_job_description(
        title=title,
        content=text,
        analysis=analysis,
        client_id=client_id
    )
    
    if not jd_id:
        raise HTTPException(status_code=500, detail="Failed to save job description")
    
    return services["supabase"].get_jd_by_id(jd_id)


@router.post("/{jd_id}/analyze")
async def analyze_job(
    jd_id: str,
    client_id: Optional[str] = None,
    services: dict = Depends(get_services)
):
    """Re-analyze an existing job description."""
    job = services["supabase"].get_jd_by_id(jd_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job description not found")
    
    # Get client preferences
    client_comments = None
    if client_id:
        client = services["supabase"].get_client_by_id(client_id)
        if client and client.get("evaluation_preferences"):
            client_comments = f"CLIENT: {client['name']}\nPREFERENCES: {client['evaluation_preferences']}"
    
    # Analyze
    analysis = services["claude"].analyze_jd(job.get("jd_text", ""), client_comments)
    
    return {
        "jd_id": jd_id,
        "analysis": analysis
    }


@router.delete("/{jd_id}")
async def delete_job(
    jd_id: str,
    services: dict = Depends(get_services)
):
    """Delete a job description."""
    existing = services["supabase"].get_jd_by_id(jd_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Job description not found")
    
    success = services["supabase"].delete_job_description(jd_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete job description")
    
    return {"message": "Job description deleted", "id": jd_id}
