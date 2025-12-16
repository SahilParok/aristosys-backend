"""
Screening Router
API endpoints for candidate screening
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List, Optional
import fitz  # PyMuPDF
from pathlib import Path
import re

from ..config import get_settings, Settings
from ..services import ClaudeService, ScoringService, DeepgramService, SupabaseService
from ..models.schemas import ScreeningResponse, CandidateResult


router = APIRouter(prefix="/screening", tags=["Screening"])


def get_services(settings: Settings = Depends(get_settings)):
    """Dependency to get all services."""
    return {
        "claude": ClaudeService(settings.anthropic_api_key),
        "scoring": ScoringService(),
        "deepgram": DeepgramService(settings.deepgram_api_key),
        "supabase": SupabaseService(settings.supabase_url, settings.supabase_key)
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


def normalize_name(filename: str) -> str:
    """Extract and normalize name from filename for matching."""
    name = Path(filename).stem
    # Remove common suffixes
    for suffix in ['_resume', '_cv', '_interview', '_audio', '_recording', 'resume', 'cv']:
        name = re.sub(rf'[_\-\s]*{re.escape(suffix)}[_\-\s]*', '', name, flags=re.IGNORECASE)
    # Normalize
    name = re.sub(r'[_\-]+', ' ', name).lower().strip()
    return name


def partial_word_match(word1: str, word2: str) -> bool:
    """Check if one word is substring of another."""
    if len(word1) < 3 or len(word2) < 3:
        return False
    return word1 in word2 or word2 in word1


@router.post("/analyze-jd")
async def analyze_job_description(
    jd_file: Optional[UploadFile] = File(None),
    jd_text: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None),
    save_jd: bool = Form(True),
    services: dict = Depends(get_services)
):
    """
    Analyze a job description.
    
    Upload a PDF or provide text directly.
    Returns extracted requirements and optionally saves to database.
    """
    # Get JD text
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
    
    # Get client preferences if client_id provided
    client_comments = None
    if client_id:
        client = services["supabase"].get_client_by_id(client_id)
        if client and client.get("evaluation_preferences"):
            client_comments = f"CLIENT: {client['name']}\nPREFERENCES: {client['evaluation_preferences']}"
    
    # Analyze with Claude
    analysis = services["claude"].analyze_jd(text, client_comments)
    
    # Save to database if requested
    jd_id = None
    if save_jd:
        title = analysis.get("job_title", "Untitled Position")
        jd_id = services["supabase"].save_job_description(
            title=title,
            content=text,
            analysis=analysis,
            client_id=client_id
        )
    
    return {
        "jd_id": jd_id,
        "analysis": analysis,
        "saved": save_jd
    }


@router.post("/screen", response_model=ScreeningResponse)
async def screen_candidates(
    jd_id: Optional[str] = Form(None),
    jd_file: Optional[UploadFile] = File(None),
    client_id: Optional[str] = Form(None),
    resumes: List[UploadFile] = File([]),
    audio_files: List[UploadFile] = File([]),
    services: dict = Depends(get_services)
):
    """
    Screen candidates against a job description.
    
    - Provide either jd_id (saved JD) or jd_file (new upload)
    - Upload resume PDFs and/or audio files
    - Returns scored results for all candidates
    """
    # Get JD analysis
    if jd_id:
        jd_data = services["supabase"].get_jd_by_id(jd_id)
        if not jd_data:
            raise HTTPException(status_code=404, detail="Job description not found")
        jd_text = jd_data.get("jd_text", "")
        jd_analysis = jd_data.get("analysis_json")
        if not jd_analysis:
            jd_analysis = services["claude"].analyze_jd(jd_text)
    elif jd_file:
        content = await jd_file.read()
        jd_text = extract_pdf_text(content) if jd_file.filename.lower().endswith('.pdf') else content.decode('utf-8')
        jd_analysis = services["claude"].analyze_jd(jd_text)
    else:
        raise HTTPException(status_code=400, detail="Provide jd_id or jd_file")
    
    # Get client preferences
    client_comments = None
    if client_id:
        client = services["supabase"].get_client_by_id(client_id)
        if client and client.get("evaluation_preferences"):
            client_comments = f"CLIENT: {client['name']}\nPREFERENCES: {client['evaluation_preferences']}"
    
    # Match resume and audio files by name
    candidates = {}
    
    # Process resumes
    for resume in resumes:
        filename = resume.filename
        name = normalize_name(filename)
        if name not in candidates:
            candidates[name] = {
                "resume_file": None,
                "resume_content": None,
                "audio_file": None,
                "audio_content": None
            }
        content = await resume.read()
        candidates[name]["resume_file"] = filename
        candidates[name]["resume_content"] = content
    
    # Process audio files and match to resumes
    for audio in audio_files:
        filename = audio.filename
        audio_name = normalize_name(filename)
        content = await audio.read()
        
        matched = False
        
        # Try exact match
        if audio_name in candidates:
            candidates[audio_name]["audio_file"] = filename
            candidates[audio_name]["audio_content"] = content
            matched = True
        else:
            # Try partial matching
            audio_words = set(audio_name.split())
            for cand_name in candidates:
                cand_words = set(cand_name.split())
                # Check word overlap or partial match
                if audio_words & cand_words:
                    candidates[cand_name]["audio_file"] = filename
                    candidates[cand_name]["audio_content"] = content
                    matched = True
                    break
                # Check substring
                for aw in audio_words:
                    for cw in cand_words:
                        if partial_word_match(aw, cw):
                            candidates[cand_name]["audio_file"] = filename
                            candidates[cand_name]["audio_content"] = content
                            matched = True
                            break
                    if matched:
                        break
                if matched:
                    break
        
        # Add as standalone if no match
        if not matched:
            candidates[audio_name] = {
                "resume_file": None,
                "resume_content": None,
                "audio_file": filename,
                "audio_content": content
            }
    
    # Process each candidate
    results = []
    
    for cand_name, cand_data in candidates.items():
        result = CandidateResult(
            name=cand_name,
            resume_file=cand_data["resume_file"],
            audio_file=cand_data["audio_file"]
        )
        
        # Process resume
        if cand_data["resume_content"]:
            resume_text = extract_pdf_text(cand_data["resume_content"])
            resume_analysis = services["claude"].analyze_resume(
                resume_text, jd_analysis, client_comments
            )
            
            # Update candidate name from resume
            if resume_analysis.get("candidate_name") and resume_analysis["candidate_name"] != "Unknown":
                result.name = resume_analysis["candidate_name"]
            
            # Score the resume
            scoring_result = services["scoring"].score_candidate(resume_analysis, jd_analysis)
            
            result.resume_score = scoring_result["final_score"]
            result.resume_analysis = resume_analysis
            result.score_breakdown = scoring_result["breakdown"]
        
        # Process audio
        if cand_data["audio_content"]:
            transcript_result = services["deepgram"].transcribe_file(cand_data["audio_content"])
            
            if transcript_result["success"] and transcript_result["text"]:
                audio_analysis = services["claude"].analyze_audio(
                    transcript_result["text"], jd_analysis
                )
                result.audio_analysis = audio_analysis
        
        # Generate recommendation
        if result.resume_score is not None or result.audio_analysis is not None:
            result.recommendation = services["claude"].generate_recommendation(
                result.name,
                result.resume_score,
                result.audio_analysis,
                jd_analysis
            )
        
        results.append(result)
    
    # Sort by score (highest first)
    results.sort(
        key=lambda x: (x.resume_score or 0, x.audio_analysis.technical_score if x.audio_analysis else 0),
        reverse=True
    )
    
    return ScreeningResponse(
        job_title=jd_analysis.get("job_title", "Unknown Position"),
        job_analysis=jd_analysis,
        candidates=results
    )


@router.get("/reports")
async def get_reports(
    limit: int = 50,
    jd_id: Optional[str] = None,
    services: dict = Depends(get_services)
):
    """Get screening reports."""
    reports = services["supabase"].get_screening_reports(jd_id=jd_id, limit=limit)
    return {"reports": reports}


@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    services: dict = Depends(get_services)
):
    """Get a specific screening report."""
    report = services["supabase"].get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
