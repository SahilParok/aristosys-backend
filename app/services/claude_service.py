"""
Claude AI Service
Handles JD analysis, resume analysis, and recommendations
"""
import anthropic
import json
import re
from typing import Dict, Any, Optional, List


class ClaudeService:
    """Service for Claude AI operations."""
    
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"
    
    def _clean_json_response(self, text: str) -> str:
        """Clean JSON from Claude response."""
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r'^```json?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
        return text
    
    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON from Claude response."""
        text = self._clean_json_response(text)
        json_start = text.find('{')
        json_end = text.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            return json.loads(text[json_start:json_end])
        raise ValueError("No valid JSON found in response")
    
    def analyze_jd(self, jd_text: str, client_comments: Optional[str] = None) -> Dict[str, Any]:
        """Analyze job description and extract requirements."""
        prompt = f"""You are an expert technical recruiter analyzing a Job Description.

JOB DESCRIPTION:
{jd_text[:8000]}

{f'ADDITIONAL CLIENT REQUIREMENTS: {client_comments}' if client_comments else ''}

Return ONLY valid JSON:

{{
  "job_title": "exact job title from JD",
  "job_classification": "strict_engineering OR moderate_engineering OR support_ok",
  "classification_reasoning": "1-2 sentence explanation",
  "must_have_skills": [
    {{"skill": "Python", "type": "single"}},
    {{"skill": "Database", "type": "or_group", "options": ["MySQL", "MongoDB", "PostgreSQL"]}},
    {{"skill": "CI/CD Tools", "type": "or_group", "options": ["Jenkins", "GitHub Actions", "GitLab CI"]}},
    {{"skill": "Cloud Platform", "type": "or_group", "options": ["AWS", "Azure", "GCP"]}}
  ],
  "nice_to_have_skills": [
    {{"skill": "Docker", "type": "single"}},
    {{"skill": "Container Orchestration", "type": "or_group", "options": ["Kubernetes", "ECS"]}}
  ],
  "total_experience_required": 5,
  "relevant_experience_required": {{"SkillName": 3}}
}}

CRITICAL SKILL GROUPING RULES:
1. When JD says "(A, B, C)" → These are OR options, group them together
2. When JD says "e.g., A, B" or "such as A, B" or "like A, B" → OR options
3. When JD says "A or B" explicitly → OR options
4. When JD says "A/B/C" with slashes → OR options
5. When JD says "A and B" explicitly or lists core technologies → AND (separate skills)
6. For OR groups, use a descriptive category name like "Database", "Cloud Platform", "CI/CD Tools"

CLASSIFICATION RULES:
- strict_engineering: Software Dev, Full Stack, Backend, Frontend, Cloud Engineer, DevOps, SRE, AWS Data Engineer, ETL
- moderate_engineering: QA Automation, Test Engineer, RPA Developer
- support_ok: CDGC, Data Governance, ITSM, SAP functional, CRM functional, L2/L3 support

JSON:"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = self._parse_json_response(response.content[0].text)
            
            # Ensure required fields
            if "nice_to_have_skills" not in result:
                result["nice_to_have_skills"] = []
            if "relevant_experience_required" not in result:
                result["relevant_experience_required"] = {}
            
            # Normalize skill format
            result["must_have_skills"] = self._normalize_skills(result.get("must_have_skills", []))
            result["nice_to_have_skills"] = self._normalize_skills(result.get("nice_to_have_skills", []))
            
            return result
            
        except Exception as e:
            print(f"JD analysis error: {e}")
            return {
                "job_title": "Technical Position",
                "job_classification": "strict_engineering",
                "must_have_skills": [{"skill": "Python", "type": "single"}],
                "nice_to_have_skills": [],
                "total_experience_required": 5,
                "relevant_experience_required": {}
            }
    
    def _normalize_skills(self, skills: List[Any]) -> List[Dict[str, Any]]:
        """Convert skills to consistent format."""
        normalized = []
        for skill in skills:
            if isinstance(skill, str):
                normalized.append({"skill": skill, "type": "single"})
            elif isinstance(skill, dict):
                normalized.append(skill)
        return normalized
    
    def _get_all_skills_to_evaluate(self, must_have: List[Dict], nice_to_have: List[Dict]) -> List[str]:
        """Get flat list of all skills to evaluate."""
        skills = []
        for skill in must_have + nice_to_have:
            if isinstance(skill, dict):
                if skill.get("type") == "or_group":
                    skills.extend(skill.get("options", []))
                else:
                    skills.append(skill.get("skill", ""))
            else:
                skills.append(str(skill))
        return skills
    
    def analyze_resume(
        self, 
        resume_text: str, 
        jd_analysis: Dict[str, Any],
        client_comments: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze resume against job requirements."""
        
        must_have = jd_analysis.get("must_have_skills", [])
        nice_to_have = jd_analysis.get("nice_to_have_skills", [])
        all_skills = self._get_all_skills_to_evaluate(must_have, nice_to_have)
        skill_list = ", ".join(all_skills) if all_skills else "Python, SQL, Git"
        
        relevant_exp_str = json.dumps(jd_analysis.get("relevant_experience_required", {}))
        
        prompt = f"""You are an expert technical recruiter evaluating a candidate's resume.

JOB REQUIREMENTS:
- Title: {jd_analysis.get('job_title', 'Technical Role')}
- Classification: {jd_analysis.get('job_classification', 'strict_engineering')}
- Total Experience Required: {jd_analysis.get('total_experience_required', 5)} years
- Relevant Experience Required: {relevant_exp_str}

{f'CLIENT REQUIREMENTS: {client_comments}' if client_comments else ''}

RESUME:
{resume_text[:6000]}

Return ONLY valid JSON:

{{
  "candidate_name": "Full Name from resume",
  "candidate_email": "email@example.com or null if not found",
  "candidate_linkedin": "linkedin.com/in/profile or null if not found",
  "candidate_phone": "phone number or null if not found",
  "estimated_total_experience": 6.5,
  "skill_strength": {{"SkillName": "strong/moderate/weak/missing"}},
  "estimated_relevant_experience": {{"SkillName": 3}},
  "support_hybrid_pattern": "engineering_heavy OR hybrid OR support_heavy",
  "pattern_reasoning": "1 sentence",
  "engineering_depth_score": 12,
  "engineering_depth_reasoning": "1-2 sentences",
  "formatting_score": 2,
  "formatting_notes": "brief notes",
  "career_gap_months": 0,
  "gap_reason": "none OR education OR maternity OR illness OR unexplained",
  "gap_is_recent": false,
  "job_hopping_data": {{
    "full_time_roles_last_5_years": 2,
    "short_tenure_ft_roles_count": 0,
    "has_valid_explanation": true
  }},
  "summary": "2-3 sentence summary",
  "strengths": ["s1", "s2", "s3"],
  "concerns": ["c1", "c2"]
}}

IMPORTANT - CONTACT INFO EXTRACTION:
- candidate_email: Extract the email address exactly as written in the resume
- candidate_linkedin: Extract the LinkedIn URL
- candidate_phone: Extract phone number including country code if present
- If any contact info is not found, set to null

EVALUATE EACH SKILL INDIVIDUALLY: {skill_list}

SKILL STRENGTH: strong (prominently featured), moderate (mentioned), weak (brief mention), missing (not found)
ENGINEERING DEPTH (0-15): 0-5 (lists tools), 6-10 (basic work), 11-15 (architecture, ownership)
FORMATTING (0-3): 0 (poor), 1 (issues), 2 (good), 3 (excellent)

JSON:"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = self._parse_json_response(response.content[0].text)
            
            # Apply defaults
            defaults = {
                "estimated_total_experience": 5,
                "skill_strength": {},
                "estimated_relevant_experience": {},
                "support_hybrid_pattern": "engineering_heavy",
                "engineering_depth_score": 8,
                "formatting_score": 2,
                "career_gap_months": 0,
                "gap_reason": "none",
                "gap_is_recent": False,
                "job_hopping_data": {
                    "full_time_roles_last_5_years": 0,
                    "short_tenure_ft_roles_count": 0,
                    "has_valid_explanation": True
                },
                "candidate_email": None,
                "candidate_linkedin": None,
                "candidate_phone": None
            }
            
            for key, val in defaults.items():
                if key not in result:
                    result[key] = val
            
            # Clamp scores
            result["engineering_depth_score"] = max(0, min(15, result["engineering_depth_score"]))
            result["formatting_score"] = max(0, min(3, result["formatting_score"]))
            
            return result
            
        except Exception as e:
            print(f"Resume analysis error: {e}")
            return {
                "candidate_name": "Unknown",
                "candidate_email": None,
                "candidate_linkedin": None,
                "candidate_phone": None,
                "estimated_total_experience": 5,
                "skill_strength": {},
                "summary": "Analysis failed",
                "strengths": [],
                "concerns": ["Analysis failed"]
            }
    
    def analyze_audio(
        self, 
        transcript: str, 
        jd_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze interview transcript."""
        
        must_have = jd_analysis.get("must_have_skills", [])
        all_skills = self._get_all_skills_to_evaluate(must_have, [])
        
        prompt = f"""You are an expert technical recruiter evaluating an interview transcript.

JOB: {jd_analysis.get('job_title', 'Technical Role')}
KEY SKILLS TO EVALUATE: {', '.join(all_skills)}

INTERVIEW TRANSCRIPT:
{transcript[:8000]}

Return ONLY valid JSON:

{{
  "technical_score": 75,
  "communication_score": 80,
  "skills_demonstrated": ["skill1", "skill2"],
  "skills_missing": ["skill3"],
  "technical_notes": "2-3 sentences on technical ability",
  "communication_notes": "2-3 sentences on communication",
  "transcript_summary": "Brief summary of interview"
}}

SCORING GUIDELINES:
- technical_score (0-100): How well did they demonstrate technical knowledge?
- communication_score (0-100): Clarity, articulation, professionalism
- Be lenient with Indian English accents and phrasing - focus on content

JSON:"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = self._parse_json_response(response.content[0].text)
            
            # Clamp scores
            result["technical_score"] = max(0, min(100, result.get("technical_score", 50)))
            result["communication_score"] = max(0, min(100, result.get("communication_score", 50)))
            
            return result
            
        except Exception as e:
            print(f"Audio analysis error: {e}")
            return {
                "technical_score": 50,
                "communication_score": 50,
                "skills_demonstrated": [],
                "skills_missing": [],
                "technical_notes": "Analysis failed",
                "communication_notes": "Analysis failed",
                "transcript_summary": ""
            }
    
    def generate_recommendation(
        self,
        candidate_name: str,
        resume_score: Optional[float],
        audio_analysis: Optional[Dict[str, Any]],
        jd_analysis: Dict[str, Any]
    ) -> str:
        """Generate hiring recommendation."""
        
        prompt = f"""Based on screening results, provide a brief hiring recommendation.

JOB: {jd_analysis.get('job_title', 'Technical Role')}
CANDIDATE: {candidate_name}
RESUME SCORE: {resume_score if resume_score else 'N/A'}/100

{f"TECHNICAL SCORE: {audio_analysis.get('technical_score', 'N/A')}/100" if audio_analysis else ""}
{f"COMMUNICATION SCORE: {audio_analysis.get('communication_score', 'N/A')}/100" if audio_analysis else ""}

Provide a 2-3 sentence recommendation. Be direct about whether to proceed or not."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            return f"Unable to generate recommendation: {e}"
