"""All Supabase access lives here so the routes stay free of query details.

Reads go through the game_catalog / user_library views defined in supabase/schema.sql.
"""
from datetime import UTC, datetime

from postgrest.exceptions import APIError

from backend.db import get_client

# PostgreSQL error codes
FOREIGN_KEY_VIOLATION = "23503"
UNIQUE_VIOLATION = "23505"
NO_DATA_FOUND = "P0002"


def _now():
    return datetime.now(UTC).isoformat()


# --- Catalog ---------------------------------------------------------------

def list_games():
    return get_client().table("game_catalog").select("*").order("title").execute().data


def get_game(game_id):
    rows = (
        get_client().table("game_catalog").select("*").eq("game_id", game_id).limit(1).execute()
    ).data
    return rows[0] if rows else None


# --- Users -----------------------------------------------------------------

def find_user_by_email(email):
    rows = get_client().table("users").select("*").eq("email", email).limit(1).execute().data
    return rows[0] if rows else None


def create_user(username, email, password_hash):
    """Returns False if the email is already registered."""
    try:
        get_client().table("users").insert(
            {"username": username, "email": email, "password_hash": password_hash}
        ).execute()
    except APIError as e:
        if e.code == UNIQUE_VIOLATION:
            return False
        raise
    return True


# --- Library ---------------------------------------------------------------

def owned_game_ids(user_id):
    rows = get_client().table("library").select("game_id").eq("user_id", user_id).execute().data
    return {row["game_id"] for row in rows}


def list_library(user_id):
    return (
        get_client().table("user_library").select("*").eq("user_id", user_id).order("title")
        .execute()
    ).data


def purchase_game(user_id, game_id):
    """True if added, False if already owned, None if the game does not exist."""
    try:
        return get_client().rpc(
            "purchase_game", {"p_user_id": user_id, "p_game_id": game_id}
        ).execute().data
    except APIError as e:
        if e.code == NO_DATA_FOUND:
            return None
        raise


def mark_played(user_id, game_id):
    """Returns False if the user does not own the game."""
    rows = (
        get_client().table("plays").update({"last_played": _now()})
        .eq("user_id", user_id).eq("game_id", game_id).execute()
    ).data
    return bool(rows)


# --- Reviews ---------------------------------------------------------------

def list_reviews(game_id):
    rows = (
        get_client().table("review")
        .select("user_id, rating, body, updated_at, users(username)")
        .eq("game_id", game_id).order("updated_at", desc=True).execute()
    ).data
    for row in rows:
        row["username"] = (row.pop("users", None) or {}).get("username", "Unknown player")
    return rows


def save_review(user_id, game_id, rating, body):
    """Create or replace the user's review. Returns False if they do not own the game."""
    try:
        get_client().table("review").upsert(
            {
                "user_id": user_id,
                "game_id": game_id,
                "rating": rating,
                "body": body or None,
                "updated_at": _now(),
            },
            on_conflict="user_id,game_id",
        ).execute()
    except APIError as e:
        if e.code == FOREIGN_KEY_VIOLATION:
            return False
        raise
    return True
