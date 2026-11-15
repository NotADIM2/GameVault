"""Check the catalog in data/games/ and data/developers/ for mistakes.

Uses only the standard library, so it needs no setup. Usage (from the project root):
    python scripts/check_catalog.py

Each game is one file, data/games/<id>-<title>.json, and each studio is one file,
data/developers/<name>.json. Keeping them separate means pull requests that add
different games never conflict with each other.
"""
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

GAME_FIELDS = {"id", "title", "price", "genres", "developer", "release_date", "description",
               "image_url"}
DEVELOPER_FIELDS = {"name", "country"}
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def slugify(text):
    """'Baldur's Gate 3' -> 'baldurs-gate-3'."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"['’]", "", text.lower())
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "untitled"


def game_filename(game):
    return f"{game['id']}-{slugify(game['title'])}.json"


def developer_filename(dev):
    return f"{slugify(dev['name'])}.json"


def is_text(value):
    return isinstance(value, str) and value.strip() != ""


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def read_folder(root, folder, errors):
    """Yield (path shown in messages, parsed JSON) for every file in data/<folder>/."""
    path = root / "data" / folder
    if not path.is_dir():
        errors.append(f"data/{folder}/ is missing")
        return
    for file in sorted(path.iterdir()):
        where = file.relative_to(root).as_posix()
        if file.is_dir() or file.suffix != ".json":
            errors.append(f"{where}: only .json files belong in data/{folder}/")
            continue
        try:
            yield where, json.loads(file.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            errors.append(f"{where}: save the file as UTF-8")
        except json.JSONDecodeError as e:
            errors.append(f"{where}: not valid JSON ({e.msg} at line {e.lineno}, "
                          f"column {e.colno}). Look for a missing comma, quote or bracket "
                          "just before that spot.")


def check_developer(where, dev, errors):
    if not isinstance(dev, dict):
        errors.append(f"{where}: must be an object like {{\"name\": ..., \"country\": ...}}")
        return None
    for key in sorted(set(dev) - DEVELOPER_FIELDS):
        errors.append(f"{where}: unknown field \"{key}\"")
    if not is_text(dev.get("name")):
        errors.append(f"{where}: \"name\" must be a non-empty string")
        return None
    if dev.get("country") is not None and not is_text(dev["country"]):
        errors.append(f"{where}: \"country\" must be a string or null")
    expected = developer_filename(dev)
    if not where.endswith("/" + expected):
        errors.append(f"{where}: rename this file to data/developers/{expected}")
    return dev["name"]


def check_game(where, game, developer_names, root, errors):
    """Validate one game. Returns True when its id and title are usable for duplicate checks."""
    if not isinstance(game, dict):
        errors.append(f"{where}: must be an object")
        return False
    for key in sorted(GAME_FIELDS - set(game)):
        errors.append(f"{where}: missing field \"{key}\" (use null if unknown)")
    for key in sorted(set(game) - GAME_FIELDS):
        errors.append(f"{where}: unknown field \"{key}\"")

    good_id = is_int(game.get("id")) and game["id"] > 0
    if "id" in game and not good_id:
        errors.append(f"{where}: \"id\" must be a positive whole number")
    good_title = is_text(game.get("title"))
    if "title" in game and not good_title:
        errors.append(f"{where}: \"title\" must be a non-empty string")
    if good_id and good_title and not where.endswith("/" + game_filename(game)):
        errors.append(f"{where}: rename this file to data/games/{game_filename(game)}")

    if "price" in game and not (is_int(game["price"]) and game["price"] >= 0):
        errors.append(f"{where}: \"price\" must be a whole number of rupees, 0 or more")

    genres = game.get("genres")
    if "genres" in game:
        if not isinstance(genres, list) or not genres or not all(is_text(g) for g in genres):
            errors.append(f"{where}: \"genres\" must be a non-empty list of strings")
        elif len(set(genres)) != len(genres):
            errors.append(f"{where}: \"genres\" lists the same genre twice")

    dev = game.get("developer")
    if dev is not None and dev not in developer_names:
        errors.append(f"{where}: developer {dev!r} has no file in data/developers/ "
                      "(add one, with the name spelled exactly the same)")

    released = game.get("release_date")
    if released is not None:
        try:
            if not (isinstance(released, str) and DATE_RE.fullmatch(released)):
                raise ValueError
            date.fromisoformat(released)
        except ValueError:
            errors.append(f"{where}: \"release_date\" must be a real date as YYYY-MM-DD, or null")

    description = game.get("description")
    if description is not None and not is_text(description):
        errors.append(f"{where}: \"description\" must be a non-empty string, or null")

    image = game.get("image_url")
    if "image_url" in game:
        if not isinstance(image, str):
            errors.append(f"{where}: \"image_url\" must be a string")
        elif image.startswith("/static/"):
            if not (root / image.lstrip("/")).is_file():
                errors.append(f"{where}: \"image_url\" points to {image}, which doesn't exist")
        elif not image.startswith("https://"):
            errors.append(f"{where}: \"image_url\" must start with https:// or /static/")
    return good_id and good_title


def check(root=ROOT):
    """Read and validate the catalog. Returns ({"developers": [...], "games": [...]}, errors)."""
    errors = []
    developers, dev_files = [], {}
    for where, dev in read_folder(root, "developers", errors):
        name = check_developer(where, dev, errors)
        if name is None:
            continue
        if name in dev_files:
            errors.append(f"{where}: developer \"{name}\" already has a file ({dev_files[name]})")
            continue
        dev_files[name] = where
        developers.append(dev)

    games, ids, titles = [], {}, {}
    for where, game in read_folder(root, "games", errors):
        if not check_game(where, game, dev_files, root, errors):
            continue
        if game["id"] in ids:
            errors.append(f"{where}: id {game['id']} is already used by {ids[game['id']]}")
        ids.setdefault(game["id"], where)
        key = game["title"].casefold()
        if key in titles:
            errors.append(f"{where}: {game['title']!r} is already in the catalog ({titles[key]})")
        titles.setdefault(key, where)
        games.append(game)

    games.sort(key=lambda g: g["id"])
    return {"developers": developers, "games": games}, errors


def main():
    catalog, errors = check()
    if errors:
        print(f"Found {len(errors)} problem(s) in the catalog:\n")
        print("\n".join(f"  - {e}" for e in errors))
        return 1
    print(f"Catalog looks good: {len(catalog['games'])} games, "
          f"{len(catalog['developers'])} developers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
