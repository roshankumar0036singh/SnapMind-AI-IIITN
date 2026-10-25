from functools import lru_cache
from supabase import create_client, Client
from src.config import get_settings

settings = get_settings()

@lru_cache()
def get_supabase_client() -> Client:
    """
    Returns a cached Supabase client instance using the publishable/anon key.
    Ideal for client-facing read queries.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

@lru_cache()
def get_supabase_admin() -> Client:
    """
    Returns a cached Supabase admin client using the service role key.
    Use this for backend operations, data ingestion, vector operations, and migrations
    to bypass RLS (Row Level Security) when necessary.
    """
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
    return create_client(url, key)
