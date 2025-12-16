"""
Scoring Service
Handles skill scoring, experience evaluation, and final score calculation
"""
from typing import Dict, Any, List, Tuple, Optional
import math


# Skill strength multipliers
SKILL_STRENGTH_MULTIPLIER = {
    "strong": 1.0,
    "moderate": 0.7,
    "weak": 0.3,
    "missing": 0.0
}


class ScoringService:
    """Service for candidate scoring calculations."""
    
    def __init__(self):
        # Score allocation (total = 100)
        self.base_score = 40
        self.must_have_max = 30
        self.nice_to_have_max = 5
        self.suitability_max = 25  # JD suitability
        self.formatting_max = 3    # Part of base
    
    def round_experience(self, years: float) -> int:
        """Round experience: >=0.5 rounds UP, <0.5 rounds DOWN."""
        return math.floor(years + 0.5)
    
    def get_best_skill_from_group(
        self, 
        options: List[str], 
        skill_strength: Dict[str, str]
    ) -> Tuple[Optional[str], str, float]:
        """For an OR group, find the best matching skill and its strength."""
        best_skill = None
        best_strength = "missing"
        best_multiplier = 0.0
        
        for option in options:
            # Try exact match first
            strength = skill_strength.get(option, "").lower()
            if not strength:
                # Try case-insensitive match
                for key, val in skill_strength.items():
                    if key.lower() == option.lower():
                        strength = val.lower()
                        break
            
            if not strength:
                strength = "missing"
            
            multiplier = SKILL_STRENGTH_MULTIPLIER.get(strength, 0.0)
            if multiplier > best_multiplier:
                best_multiplier = multiplier
                best_strength = strength
                best_skill = option
        
        return best_skill, best_strength, best_multiplier
    
    def score_skills(
        self,
        must_have_skills: List[Dict[str, Any]],
        nice_to_have_skills: List[Dict[str, Any]],
        skill_strength: Dict[str, str]
    ) -> Tuple[float, float, List[Dict[str, Any]]]:
        """
        Score skills: Must-have (30pts with multipliers), Nice-to-have (5pts bonus, binary).
        
        Handles both single skills and OR groups.
        """
        must_have_score = 0.0
        nice_to_have_bonus = 0.0
        breakdown = []
        
        # Score must-have skills
        if must_have_skills:
            points_per_skill = self.must_have_max / len(must_have_skills)
            must_have_breakdown = []
            
            for skill_item in must_have_skills:
                if isinstance(skill_item, str):
                    # Old format - single skill
                    strength = skill_strength.get(skill_item, "missing").lower()
                    multiplier = SKILL_STRENGTH_MULTIPLIER.get(strength, 0.0)
                    skill_points = points_per_skill * multiplier
                    must_have_score += skill_points
                    must_have_breakdown.append({
                        "skill": skill_item,
                        "strength": strength,
                        "points": round(skill_points, 1),
                        "max_points": round(points_per_skill, 1)
                    })
                    
                elif isinstance(skill_item, dict):
                    skill_type = skill_item.get("type", "single")
                    skill_name = skill_item.get("skill", "Skill")
                    
                    if skill_type == "or_group":
                        # OR group - find best matching option
                        options = skill_item.get("options", [])
                        best_skill, best_strength, best_multiplier = self.get_best_skill_from_group(
                            options, skill_strength
                        )
                        skill_points = points_per_skill * best_multiplier
                        must_have_score += skill_points
                        
                        display_name = f"{skill_name} ({'/'.join(options)})"
                        must_have_breakdown.append({
                            "skill": display_name,
                            "strength": best_strength,
                            "matched_option": best_skill,
                            "points": round(skill_points, 1),
                            "max_points": round(points_per_skill, 1),
                            "is_or_group": True
                        })
                    else:
                        # Single skill in new format
                        strength = skill_strength.get(skill_name, "missing").lower()
                        multiplier = SKILL_STRENGTH_MULTIPLIER.get(strength, 0.0)
                        skill_points = points_per_skill * multiplier
                        must_have_score += skill_points
                        must_have_breakdown.append({
                            "skill": skill_name,
                            "strength": strength,
                            "points": round(skill_points, 1),
                            "max_points": round(points_per_skill, 1)
                        })
            
            breakdown.append({
                "category": "Must-Have Skills (Technical)",
                "total_points": round(must_have_score, 1),
                "max_points": self.must_have_max,
                "skills": must_have_breakdown
            })
        
        # Score nice-to-have skills
        if nice_to_have_skills:
            points_per_skill = self.nice_to_have_max / len(nice_to_have_skills)
            nice_to_have_breakdown = []
            
            for skill_item in nice_to_have_skills:
                if isinstance(skill_item, str):
                    strength = skill_strength.get(skill_item, "missing").lower()
                    has_skill = strength != "missing"
                    skill_points = points_per_skill if has_skill else 0
                    nice_to_have_bonus += skill_points
                    nice_to_have_breakdown.append({
                        "skill": skill_item,
                        "has_skill": has_skill,
                        "points": round(skill_points, 1),
                        "max_points": round(points_per_skill, 1)
                    })
                    
                elif isinstance(skill_item, dict):
                    skill_type = skill_item.get("type", "single")
                    skill_name = skill_item.get("skill", "Skill")
                    
                    if skill_type == "or_group":
                        options = skill_item.get("options", [])
                        best_skill, best_strength, _ = self.get_best_skill_from_group(
                            options, skill_strength
                        )
                        has_skill = best_strength != "missing"
                        skill_points = points_per_skill if has_skill else 0
                        nice_to_have_bonus += skill_points
                        
                        display_name = f"{skill_name} ({'/'.join(options)})"
                        nice_to_have_breakdown.append({
                            "skill": display_name,
                            "has_skill": has_skill,
                            "matched_option": best_skill,
                            "points": round(skill_points, 1),
                            "max_points": round(points_per_skill, 1),
                            "is_or_group": True
                        })
                    else:
                        strength = skill_strength.get(skill_name, "missing").lower()
                        has_skill = strength != "missing"
                        skill_points = points_per_skill if has_skill else 0
                        nice_to_have_bonus += skill_points
                        nice_to_have_breakdown.append({
                            "skill": skill_name,
                            "has_skill": has_skill,
                            "points": round(skill_points, 1),
                            "max_points": round(points_per_skill, 1)
                        })
            
            breakdown.append({
                "category": "Nice-to-Have Skills (Bonus)",
                "total_points": round(nice_to_have_bonus, 1),
                "max_points": self.nice_to_have_max,
                "skills": nice_to_have_breakdown
            })
        
        return round(must_have_score), round(nice_to_have_bonus), breakdown
    
    def calculate_suitability_score(self, engineering_depth: int) -> int:
        """Calculate JD suitability score from engineering depth (0-15 scaled to 0-25)."""
        scaled = round(engineering_depth * (self.suitability_max / 15.0))
        return max(0, min(self.suitability_max, scaled))
    
    def check_experience(
        self,
        candidate_total: float,
        required_total: float,
        relevant_required: Dict[str, float],
        relevant_candidate: Dict[str, float]
    ) -> Tuple[List[str], List[str]]:
        """Check experience and return explanations and notes (no penalties)."""
        explanations = []
        notes = []
        
        candidate_total = self.round_experience(candidate_total)
        required_total = self.round_experience(required_total)
        
        tolerance = 1
        
        if candidate_total >= required_total:
            explanations.append(f"✓ Has {candidate_total}+ years (required: {required_total})")
        elif candidate_total >= required_total - tolerance:
            explanations.append(f"~ Has {candidate_total} years (required: {required_total}, within tolerance)")
        else:
            gap = required_total - candidate_total
            notes.append(f"Experience gap: {gap} years below requirement")
            explanations.append(f"⚠ Has {candidate_total} years (required: {required_total})")
        
        return explanations, notes
    
    def calculate_final_score(
        self,
        must_have_score: float,
        nice_to_have_score: float,
        suitability_score: float,
        formatting_score: int
    ) -> float:
        """Calculate final resume score (0-100)."""
        # Base (40) + Must-Have (30) + Nice-to-Have (5) + Suitability (25)
        # Formatting is informational only
        total = self.base_score + must_have_score + nice_to_have_score + suitability_score
        return round(min(100, max(0, total)), 1)
    
    def score_candidate(
        self,
        resume_analysis: Dict[str, Any],
        jd_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Complete scoring for a candidate.
        Returns score breakdown and final score.
        """
        # Extract data
        skill_strength = resume_analysis.get("skill_strength", {})
        must_have = jd_analysis.get("must_have_skills", [])
        nice_to_have = jd_analysis.get("nice_to_have_skills", [])
        
        # Score skills
        must_have_score, nice_to_have_score, skills_breakdown = self.score_skills(
            must_have, nice_to_have, skill_strength
        )
        
        # Calculate suitability
        engineering_depth = resume_analysis.get("engineering_depth_score", 8)
        suitability_score = self.calculate_suitability_score(engineering_depth)
        
        # Get formatting
        formatting_score = resume_analysis.get("formatting_score", 2)
        
        # Check experience (no penalties, just notes)
        exp_explanations, exp_notes = self.check_experience(
            resume_analysis.get("estimated_total_experience", 0),
            jd_analysis.get("total_experience_required", 0),
            jd_analysis.get("relevant_experience_required", {}),
            resume_analysis.get("estimated_relevant_experience", {})
        )
        
        # Calculate final score
        final_score = self.calculate_final_score(
            must_have_score, nice_to_have_score, suitability_score, formatting_score
        )
        
        return {
            "final_score": final_score,
            "breakdown": {
                "base_score": self.base_score,
                "must_have_score": must_have_score,
                "nice_to_have_score": nice_to_have_score,
                "suitability_score": suitability_score,
                "formatting_score": formatting_score,
                "total": final_score,
                "skills_breakdown": skills_breakdown,
                "experience_notes": exp_explanations,
                "notes": exp_notes
            }
        }
