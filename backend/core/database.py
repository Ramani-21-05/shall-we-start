from supabase import create_client, Client
from core.config import settings

def get_supabase() -> Client:
    """Returns a thread-safe Supabase client instance."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY must be set in .env before using the database."
        )
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
