"""
Aristosys API Models
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==============================================================================
# ENUMS
# ==============================================================================

class JobClassification(str, Enum):
    STRICT_ENGINEERING = "strict_engineering"
    MODERATE_ENGINEERING = "moderate_engineering"
    SUPPORT_OK = "support_ok"


class SkillStrength(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    MISSING = "missing"


class SkillType(str, Enum):
    SINGLE = "single"
    OR_GROUP = "or_group"


# ==============================================================================
# SKILL MODELS
# ==============================================================================

class Skill(BaseModel):
    """Represents a skill requirement (single or OR group)."""
    skill: str
    type: SkillType = SkillType.SINGLE
    options: Optional[List[str]] = None  # For OR groups


class SkillScore(BaseModel):
    """Skill scoring result."""
    skill: str
    strength: Optional[SkillStrength] = None
    has_skill: Optional[bool] = None
    points: float
    max_points: float
    is_or_group: bool = False
    matched_option: Optional[str] = None


# ==============================================================================
# JOB DESCRIPTION MODELS
# ==============================================================================

class JobDescriptionCreate(BaseModel):
    """Request to create/save a job description."""
    title: str
    content: str
    client_id: Optional[str] = None


class JobDescriptionAnalysis(BaseModel):
    """Analyzed job description."""
    job_title: str
    job_classification: JobClassification
    classification_reasoning: Optional[str] = None
    must_have_skills: List[Skill]
    nice_to_have_skills: List[Skill]
    total_experience_required: float
    relevant_experience_required: Dict[str, float] = {}


class JobDescriptionResponse(BaseModel):
    """Saved job description response."""
    id: str
    title: str
    content: str
    analysis: Optional[JobDescriptionAnalysis] = None
    client_id: Optional[str] = None
    created_at: datetime
    created_by: Optional[str] = None


# ==============================================================================
# CLIENT MODELS
# ==============================================================================

class ClientCreate(BaseModel):
    """Request to create a client."""
    name: str
    evaluation_preferences: Optional[str] = None
    notes: Optional[str] = None


class ClientUpdate(BaseModel):
    """Request to update a client."""
    name: Optional[str] = None
    evaluation_preferences: Optional[str] = None
    notes: Optional[str] = None


class ClientResponse(BaseModel):
    """Client response."""
    id: str
    name: str
    evaluation_preferences: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime


# ==============================================================================
# CANDIDATE MODELS
# ==============================================================================

class CandidateContact(BaseModel):
    """Candidate contact information."""
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None


class ResumeAnalysis(BaseModel):
    """Resume analysis result."""
    candidate_name: str
    contact: CandidateContact
    estimated_total_experience: float
    skill_strength: Dict[str, SkillStrength]
    estimated_relevant_experience: Dict[str, float] = {}
    support_hybrid_pattern: str
    engineering_depth_score: int = Field(ge=0, le=15)
    formatting_score: int = Field(ge=0, le=3)
    career_gap_months: int = 0
    gap_reason: str = "none"
    summary: str
    strengths: List[str] = []
    concerns: List[str] = []


class AudioAnalysis(BaseModel):
    """Audio/interview analysis result."""
    technical_score: int = Field(ge=0, le=100)
    communication_score: int = Field(ge=0, le=100)
    skills_demonstrated: List[str] = []
    skills_missing: List[str] = []
    technical_notes: str = ""
    communication_notes: str = ""
    transcript_summary: str = ""


class ScoreBreakdown(BaseModel):
    """Detailed score breakdown."""
    base_score: int = 40
    must_have_score: float
    nice_to_have_score: float
    suitability_score: float
    formatting_score: int
    total: float
    skills_breakdown: List[SkillScore] = []
    notes: List[str] = []


class CandidateResult(BaseModel):
    """Complete candidate screening result."""
    name: str
    resume_file: Optional[str] = None
    audio_file: Optional[str] = None
    resume_score: Optional[float] = None
    resume_analysis: Optional[ResumeAnalysis] = None
    audio_analysis: Optional[AudioAnalysis] = None
    score_breakdown: Optional[ScoreBreakdown] = None
    recommendation: Optional[str] = None
    screened_at: datetime = Field(default_factory=datetime.now)


# ==============================================================================
# SCREENING REQUEST/RESPONSE
# ==============================================================================

class ScreeningRequest(BaseModel):
    """Request to screen candidates."""
    job_description_id: Optional[str] = None
    job_description_text: Optional[str] = None  # Alternative to ID
    client_id: Optional[str] = None


class ScreeningResponse(BaseModel):
    """Screening results response."""
    job_title: str
    job_analysis: JobDescriptionAnalysis
    candidates: List[CandidateResult]
    report_html: Optional[str] = None
    screened_at: datetime = Field(default_factory=datetime.now)


# ==============================================================================
# HEALTH CHECK
# ==============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str
    environment: str
