"""Supabase client. Created on first use so importing the app never needs credentials."""
import base64
import json
import os
from functools import lru_cache

from supabase import Client, create_client


def _is_public_key(key):
    """True for the anon/publishable key, which Row Level Security locks out of every table."""
    if key.startswith("sb_publishable_"):
        return True
    try:
        payload = key.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (IndexError, ValueError):
        return False
    return claims.get("role") == "anon"


@lru_cache(maxsize=1)
def get_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set. See .env.example.")
    if _is_public_key(key):
        raise RuntimeError(
            "SUPABASE_KEY is the anon/publishable key. The server needs the service_role "
            "(secret) key because Row Level Security denies the anon key. See .env.example."
        )
    return create_client(url, key)
