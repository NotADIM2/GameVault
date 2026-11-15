"""Load the catalog (data/games/ and data/developers/) into Supabase. Safe to re-run: every
write is an upsert.

Usage (from the project root, after running supabase/schema.sql):
    python -m scripts.seed
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

from scripts.check_catalog import check

ROOT = Path(__file__).resolve().parent.parent


def load_catalog():
    """Read and validate the catalog; refuse to seed if it has problems."""
    catalog, errors = check(ROOT)
    if errors:
        print("The catalog has problems, so nothing was loaded:\n")
        print("\n".join(f"  - {e}" for e in errors))
        sys.exit(1)
    return catalog


def seed(client, catalog):
    developers = catalog["developers"]
    games = catalog["games"]

    client.table("developer").upsert(developers, on_conflict="name").execute()
    rows = client.table("developer").select("developer_id, name").execute().data
    dev_ids = {r["name"]: r["developer_id"] for r in rows}
    print(f"developers: {len(dev_ids)}")

    genre_names = sorted({name for g in games for name in g["genres"]})
    client.table("genre").upsert([{"name": n} for n in genre_names], on_conflict="name").execute()
    rows = client.table("genre").select("genre_id, name").execute().data
    genre_ids = {r["name"]: r["genre_id"] for r in rows}
    print(f"genres: {len(genre_ids)}")

    client.table("game").upsert(
        [
            {
                "game_id": g["id"],
                "title": g["title"],
                "developer_id": dev_ids.get(g["developer"]),
                "price": g["price"],
                "release_date": g["release_date"],
                "description": g["description"],
                "image_url": g["image_url"],
            }
            for g in games
        ],
        on_conflict="game_id",
    ).execute()
    print(f"games: {len(games)}")

    # Replace genre links for seeded games so removed tags don't linger.
    game_ids = [g["id"] for g in games]
    client.table("have").delete().in_("game_id", game_ids).execute()
    links = [
        {"game_id": g["id"], "genre_id": genre_ids[name], "is_primary": i == 0}
        for g in games
        for i, name in enumerate(g["genres"])
    ]
    client.table("have").insert(links).execute()
    print(f"genre links: {len(links)}")


if __name__ == "__main__":
    load_dotenv(ROOT / ".env")
    from backend.db import get_client

    seed(get_client(), load_catalog())
    print("Seed complete.")
