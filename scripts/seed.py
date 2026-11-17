"""Load the catalog (data/games/ and data/developers/) into Supabase. Safe to re-run: every
write is an upsert.

Usage (from the project root, after running supabase/schema.sql):
    python -m scripts.seed           # catalog only
    python -m scripts.seed --demo    # catalog plus sample users, for local testing

Never use --demo on a live site: the sample accounts share a password printed below.
"""
import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

from scripts.check_catalog import check

ROOT = Path(__file__).resolve().parent.parent

DEMO_PASSWORD = "gamevault-demo"
# (username, email, number of games owned, number of those games reviewed)
DEMO_USERS = [
    ("demo_player", "player@gamevault.test", 4, 0),
    ("demo_critic", "critic@gamevault.test", 6, 3),
]
DEMO_REVIEWS = [
    (5, "One of the best games I've played. Easy to recommend."),
    (4, "Really good, with a few rough edges."),
    (3, "Fun for a while, but it didn't hold my attention."),
]


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


def seed_demo(client, catalog):
    """Sample users who own, play and review games, so the library and review pages have
    data without registering and buying by hand. Goes through purchase_game like the app."""
    game_ids = sorted(g["id"] for g in catalog["games"])
    password_hash = generate_password_hash(DEMO_PASSWORD)

    client.table("users").upsert(
        [
            {"username": username, "email": email, "password_hash": password_hash}
            for username, email, _, _ in DEMO_USERS
        ],
        on_conflict="email",
    ).execute()
    emails = [email for _, email, _, _ in DEMO_USERS]
    rows = client.table("users").select("id, email").in_("email", emails).execute().data
    user_ids = {r["email"]: r["id"] for r in rows}

    now = datetime.now(UTC).isoformat()
    for username, email, owned, reviewed in DEMO_USERS:
        user_id = user_ids[email]
        for i, game_id in enumerate(game_ids[:owned]):
            client.rpc("purchase_game", {"p_user_id": user_id, "p_game_id": game_id}).execute()
            (
                client.table("plays").update({"hours": 12.5 * (i + 1), "last_played": now})
                .eq("user_id", user_id).eq("game_id", game_id).execute()
            )

        reviews = [
            {"user_id": user_id, "game_id": game_id, "rating": rating, "body": body}
            for game_id, (rating, body) in zip(game_ids[:reviewed], DEMO_REVIEWS, strict=False)
        ]
        if reviews:
            client.table("review").upsert(reviews, on_conflict="user_id,game_id").execute()
        print(f"demo user {username}: owns {owned}, reviewed {len(reviews)}")

    print(f"\nLog in as any of {', '.join(emails)} with password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load the catalog into Supabase.")
    parser.add_argument(
        "--demo", action="store_true",
        help="also create sample users with a shared password (local testing only)",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    from backend.db import get_client

    client = get_client()
    catalog = load_catalog()
    seed(client, catalog)
    if args.demo:
        seed_demo(client, catalog)
    print("Seed complete.")
