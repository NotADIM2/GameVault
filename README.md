# GameVault

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

A digital game store and library built with Flask and Supabase (PostgreSQL). Browse a catalog of 90 games, buy or add free games to your library, and leave reviews for the games you own.

**GameVault is open to contributors.** Add a game to the catalog, fill in missing details, or build a new feature. The [contributing guide](CONTRIBUTING.md) explains how, and [good first contributions](#good-first-contributions) lists places to start.

## Features

- **Store** – search, filter by genre and price, and sort by popularity, rating, release date or price. Filters are kept in the URL, so any view can be shared.
- **Game pages** – details, developer, ratings and player reviews. Ratings and owner counts are calculated from real rows in the database.
- **Accounts** – sign up and log in with hashed passwords.
- **Library** – the games you own, with purchase date, price paid and last played.
- **Reviews** – only owners of a game can review it; this is enforced by the database.

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, Flask |
| Database | Supabase (PostgreSQL) |
| Frontend | Jinja templates, plain CSS and JavaScript |

## Getting started

### 1. Install dependencies

```bash
git clone https://github.com/NotADIM2/GameVault.git
cd GameVault
python -m venv .venv
.venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Create the database

1. Create a project at [supabase.com](https://supabase.com).
2. Open the SQL editor, paste the contents of `supabase/schema.sql` and run it.

### 3. Configure the environment

Copy `.env.example` to `.env` and fill it in:

| Variable | Value |
|---|---|
| `SUPABASE_URL` | Your project URL (Project Settings → API) |
| `SUPABASE_KEY` | The **service_role** (secret) key. The anon key will not work, because Row Level Security is enabled on every table. |
| `SECRET_KEY` | A random string for signing sessions: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `SESSION_COOKIE_SECURE` | `1` when serving over HTTPS, otherwise `0` |

Never commit `.env`. The service_role key bypasses all database security, so it must stay on the server.

### 4. Load the catalog and run

```bash
python -m scripts.seed
python app.py
```

Open http://127.0.0.1:5000. Set `FLASK_DEBUG=1` in `.env` for auto-reload while developing.

## Project structure

```
app.py                 Entry point
backend/
  __init__.py          App factory, config, CSRF protection, template filters
  db.py                Supabase client
  queries.py           All database access
  routes/              main (home, store, game), auth, shop (buy, library, reviews)
data/games.json        Catalog seed data
scripts/seed.py        Loads the catalog into Supabase (safe to re-run)
supabase/schema.sql    Tables, views, purchase function and security rules
templates/             Jinja templates
static/                CSS, JavaScript and images
```

## Database design

- **Entities:** `users`, `developer`, `game`, `genre`
- **Relations:** `have` (game ↔ genre), `library` (user owns game), `plays` (playtime), `review`
- **Views:** `game_catalog` and `user_library` supply everything the pages read.
- **Purchases** run through the `purchase_game` function, so a purchase is a single transaction.

The Flask server is the only client of the database. Row Level Security is enabled with no policies, so the public anon key can read and write nothing.

## Development

```bash
pip install ruff
ruff check .
```

## Contributing

Contributions of any size are welcome, from one new game card to a whole feature. Read [CONTRIBUTING.md](CONTRIBUTING.md) for setup, the catalog format and the pull request checklist.

### Good first contributions

| Task | Where |
|---|---|
| **Add a game** to the catalog | `data/games.json` |
| **Write descriptions**: 80 of 90 games have none | `data/games.json` |
| **Add release dates**: 80 of 90 games are missing one | `data/games.json` |
| **Find artwork** for Genshin Impact, Honkai: Star Rail and Alan Wake 2, which use placeholder art | `data/games.json` |
| **Replace the 6 fictional titles** (ids 75–80) with real games; they currently borrow other games' artwork | `data/games.json` |

### Feature ideas

- Wishlist stored in the database (it currently lives in the browser)
- Cart and a mock checkout with order history
- A "Your stats" page: hours and spending by genre
- Recommendations ("because you own X") from shared genres
- Full-text search with PostgreSQL
- Automated tests for the routes and database queries

Open an issue before starting a large feature, so we can agree on the approach first.

## Notes

- Purchases are simulated; there is no payment processing.
- Game artwork is loaded from the Steam CDN and belongs to its respective owners.

## License

[MIT](LICENSE)
