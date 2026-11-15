# Contributing to GameVault

Thanks for helping out! You can add a single game card or build a whole feature. This guide explains how to get set up and how to get your change merged.

## Ways to contribute

- **Catalog:** add games or fill in missing details. No Python knowledge needed, only JSON.
- **Features:** see the feature ideas in the [README](README.md#feature-ideas), or propose your own.
- **Bug fixes and UI polish:** layout, mobile support, accessibility.
- **Docs:** anything that was confusing when you set up the project.

Not sure where to start? Look for issues labelled `good first issue`, or pick a task from the [good first contributions](README.md#good-first-contributions) table.

## Setting up

**Catalog changes need no setup.** You don't need Python, a database or any keys to add or fix games. You can do it all on the GitHub website (see [Editing in your browser](#editing-in-your-browser)).

**Code changes** (features, bug fixes, UI) need the app running. Follow [Getting started](README.md#getting-started) in the README. You need your own free Supabase project: run `supabase/schema.sql` in its SQL editor, then load the catalog with `python -m scripts.seed`. It takes about five minutes.

## Editing in your browser

The quickest way to change the catalog:

1. Open [`data/games.json`](data/games.json) on GitHub and click the **pencil icon** (Edit this file). GitHub makes a fork for you automatically.
2. Make your change. The format is explained in [Adding a game](#adding-a-game) below.
3. Click **Commit changes...**, write a short message such as "Add Hollow Knight", and choose **Propose changes**.
4. Click **Create pull request**, and write `Closes #<issue number>` in the description if you're working on an issue.

That's it. An automatic check then tests your change (see [Automatic checks](#automatic-checks)).

## Workflow

1. **Fork** the repository and clone your fork.
2. **Create a branch** named after your change: `git checkout -b add-hollow-knight`.
3. **Make the change** and run the app to check that it works.
4. **Run the checks:** `python scripts/check_catalog.py` if you changed the catalog, and `pip install ruff`, then `ruff check .` if you changed code.
5. **Open a pull request** against `main` that says what you changed and how you tested it. For UI changes, add a screenshot.

Keep each pull request to one change. "Add Hollow Knight" or "Add wishlist page" are easy to review; "Add games, fix the navbar and refactor queries" is not. For the catalog, that means **one game per pull request**.

## Adding a game

Games live in `data/games.json`. Add an object to the end of the `games` array. Hollow Knight is a real example: it has id 91 reserved in an "Add games" issue.

```json
{
  "id": 91,
  "title": "Hollow Knight",
  "price": 459,
  "genres": ["Action", "Indie"],
  "developer": "Team Cherry",
  "release_date": "2017-02-24",
  "description": "Descend into a vast, ruined insect kingdom in this hand-drawn metroidvania.",
  "image_url": "https://cdn.cloudflare.steamstatic.com/steam/apps/367520/header.jpg"
}
```

| Field | Rules |
|---|---|
| `id` | If the game is listed in an ["Add games" issue](https://github.com/NotADIM2/GameVault/issues?q=is%3Aopen+label%3Acatalog+%22Add+games%22), use the id reserved for it there (91–240). For any other game, use the next unused number **from 1000 upward**. Never change an existing id, because it is part of the game's URL. |
| `title` | The game's official name. |
| `price` | Whole rupees (INR). Use `0` for free-to-play games. |
| `genres` | The **first** entry is the main genre shown on cards. Reuse existing genres where possible; check the list with a search of the file. |
| `developer` | Must match a `name` in the `developers` array at the top of the file. If the studio is new, add it there too: `{ "name": "Team Cherry", "country": "Australia" }`. |
| `release_date` | `YYYY-MM-DD`, or `null` if unknown. |
| `description` | One or two sentences **in your own words**. Do not paste store-page text. |
| `image_url` | For Steam games: `https://cdn.cloudflare.steamstatic.com/steam/apps/<app id>/header.jpg`. The app id is the number in the game's Steam store URL. |

Before opening the pull request, check that the `image_url` opens a picture when you paste it into your browser.

If you have the app running, you can also see your game in the store:

```bash
python -m scripts.seed
python app.py
```

## Automatic checks

Every pull request runs two checks on GitHub's servers:

- **Catalog** runs `scripts/check_catalog.py`. It finds invalid JSON (such as a missing comma), duplicate ids or titles, missing fields, prices that aren't whole numbers, dates that aren't `YYYY-MM-DD`, developers missing from the `developers` list, and image links that don't start with `https://`.
- **Lint** runs `ruff check .` on the Python code.

If a check fails, click **Details** next to it to see what's wrong, then fix it in the same pull request. On your first pull request, the checks start once a maintainer approves them.

## Changing the database

- Make every schema change in `supabase/schema.sql`, and explain in the pull request what existing users need to run to upgrade.
- All queries belong in `backend/queries.py`; routes should not build queries themselves.
- Ratings, review counts and owner counts are calculated from real rows. Please don't add hardcoded or generated ratings, reviews or stats.

## Ground rules

- **Never commit secrets.** `.env` is ignored by git; keep it that way. If you accidentally push a key, rotate it in Supabase straight away.
- Match the style of the surrounding code. `ruff check .` must pass.
- Be kind in issues and reviews. Everyone here is learning.

## Questions

Open an issue and ask. There's no such thing as a silly question here.
