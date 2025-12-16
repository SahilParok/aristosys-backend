"""
Clients Router
API endpoints for client management
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional

from ..config import get_settings, Settings
from ..services import SupabaseService
from ..models.schemas import ClientCreate, ClientUpdate, ClientResponse


router = APIRouter(prefix="/clients", tags=["Clients"])


def get_supabase(settings: Settings = Depends(get_settings)) -> SupabaseService:
    """Dependency to get Supabase service."""
    return SupabaseService(settings.supabase_url, settings.supabase_key)


@router.get("", response_model=List[ClientResponse])
async def list_clients(
    supabase: SupabaseService = Depends(get_supabase)
):
    """Get all clients."""
    clients = supabase.get_clients()
    return clients


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: str,
    supabase: SupabaseService = Depends(get_supabase)
):
    """Get a specific client."""
    client = supabase.get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.post("", response_model=ClientResponse)
async def create_client(
    client: ClientCreate,
    supabase: SupabaseService = Depends(get_supabase)
):
    """Create a new client."""
    client_id = supabase.create_client(
        name=client.name,
        evaluation_preferences=client.evaluation_preferences,
        notes=client.notes
    )
    
    if not client_id:
        raise HTTPException(status_code=500, detail="Failed to create client")
    
    return supabase.get_client_by_id(client_id)


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: str,
    client: ClientUpdate,
    supabase: SupabaseService = Depends(get_supabase)
):
    """Update a client."""
    existing = supabase.get_client_by_id(client_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")
    
    success = supabase.update_client(
        client_id=client_id,
        name=client.name,
        evaluation_preferences=client.evaluation_preferences,
        notes=client.notes
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update client")
    
    return supabase.get_client_by_id(client_id)


@router.delete("/{client_id}")
async def delete_client(
    client_id: str,
    supabase: SupabaseService = Depends(get_supabase)
):
    """Delete a client."""
    existing = supabase.get_client_by_id(client_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")
    
    success = supabase.delete_client(client_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete client")
    
    return {"message": "Client deleted", "id": client_id}
