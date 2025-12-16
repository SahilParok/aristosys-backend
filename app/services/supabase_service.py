"""
Supabase Service
Handles database operations for JDs, clients, and screening reports
"""
from supabase import create_client, Client
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


class SupabaseService:
    """Service for Supabase database operations."""
    
    def __init__(self, url: str, key: str):
        self.client: Client = create_client(url, key)
    
    # ==========================================================================
    # CLIENTS
    # ==========================================================================
    
    def get_clients(self, company_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all clients, optionally filtered by company."""
        try:
            query = self.client.table("clients").select("*")
            if company_id:
                query = query.eq("company_id", company_id)
            result = query.order("created_at", desc=True).execute()
            return result.data or []
        except Exception as e:
            print(f"Error loading clients: {e}")
            return []
    
    def get_client_by_id(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get a single client by ID."""
        try:
            result = self.client.table("clients").select("*").eq("id", client_id).single().execute()
            return result.data
        except Exception as e:
            print(f"Error getting client: {e}")
            return None
    
    def create_client(
        self, 
        name: str, 
        evaluation_preferences: Optional[str] = None,
        notes: Optional[str] = None,
        company_id: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Optional[str]:
        """Create a new client. Returns client ID."""
        try:
            client_id = str(uuid.uuid4())
            data = {
                "id": client_id,
                "name": name,
                "evaluation_preferences": evaluation_preferences,
                "notes": notes,
                "company_id": company_id,
                "created_by": created_by,
                "created_at": datetime.now().isoformat()
            }
            self.client.table("clients").insert(data).execute()
            return client_id
        except Exception as e:
            print(f"Error creating client: {e}")
            return None
    
    def update_client(
        self,
        client_id: str,
        name: Optional[str] = None,
        evaluation_preferences: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """Update a client."""
        try:
            data = {}
            if name is not None:
                data["name"] = name
            if evaluation_preferences is not None:
                data["evaluation_preferences"] = evaluation_preferences
            if notes is not None:
                data["notes"] = notes
            
            if data:
                self.client.table("clients").update(data).eq("id", client_id).execute()
            return True
        except Exception as e:
            print(f"Error updating client: {e}")
            return False
    
    def delete_client(self, client_id: str) -> bool:
        """Delete a client."""
        try:
            self.client.table("clients").delete().eq("id", client_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting client: {e}")
            return False
    
    # ==========================================================================
    # JOB DESCRIPTIONS
    # ==========================================================================
    
    def get_job_descriptions(self, company_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all saved job descriptions."""
        try:
            query = self.client.table("saved_jds").select("*")
            if company_id:
                query = query.eq("company_id", company_id)
            result = query.order("created_at", desc=True).execute()
            return result.data or []
        except Exception as e:
            print(f"Error loading JDs: {e}")
            return []
    
    def get_jd_by_id(self, jd_id: str) -> Optional[Dict[str, Any]]:
        """Get a single JD by ID."""
        try:
            result = self.client.table("saved_jds").select("*").eq("id", jd_id).single().execute()
            return result.data
        except Exception as e:
            print(f"Error getting JD: {e}")
            return None
    
    def save_job_description(
        self,
        title: str,
        content: str,
        analysis: Optional[Dict[str, Any]] = None,
        client_id: Optional[str] = None,
        company_id: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Optional[str]:
        """Save a job description. Returns JD ID."""
        try:
            jd_id = str(uuid.uuid4())
            data = {
                "id": jd_id,
                "title": title,
                "jd_text": content,
                "analysis_json": analysis,
                "client_id": client_id,
                "company_id": company_id,
                "created_by": created_by,
                "created_at": datetime.now().isoformat()
            }
            self.client.table("saved_jds").insert(data).execute()
            return jd_id
        except Exception as e:
            print(f"Error saving JD: {e}")
            return None
    
    def delete_job_description(self, jd_id: str) -> bool:
        """Delete a job description."""
        try:
            self.client.table("saved_jds").delete().eq("id", jd_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting JD: {e}")
            return False
    
    # ==========================================================================
    # SCREENING REPORTS
    # ==========================================================================
    
    def save_screening_report(
        self,
        jd_id: str,
        candidates: List[Dict[str, Any]],
        report_html: str,
        client_id: Optional[str] = None,
        company_id: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Optional[str]:
        """Save a screening report. Returns report ID."""
        try:
            report_id = str(uuid.uuid4())
            data = {
                "id": report_id,
                "jd_id": jd_id,
                "candidates_json": candidates,
                "report_html": report_html,
                "client_id": client_id,
                "company_id": company_id,
                "created_by": created_by,
                "created_at": datetime.now().isoformat()
            }
            self.client.table("screening_reports").insert(data).execute()
            return report_id
        except Exception as e:
            print(f"Error saving report: {e}")
            return None
    
    def get_screening_reports(
        self, 
        company_id: Optional[str] = None,
        jd_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get screening reports."""
        try:
            query = self.client.table("screening_reports").select("*")
            if company_id:
                query = query.eq("company_id", company_id)
            if jd_id:
                query = query.eq("jd_id", jd_id)
            result = query.order("created_at", desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            print(f"Error loading reports: {e}")
            return []
    
    def get_report_by_id(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get a single report by ID."""
        try:
            result = self.client.table("screening_reports").select("*").eq("id", report_id).single().execute()
            return result.data
        except Exception as e:
            print(f"Error getting report: {e}")
            return None
