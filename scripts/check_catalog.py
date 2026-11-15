"""Check data/games.json for mistakes. Uses only the standard library, so it needs no setup.

Usage (from the project root):
    python scripts/check_catalog.py
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "games.json"

GAME_FIELDS = {"id", "title", "price", "genres", "developer", "release_date", "description",
               "image_url"}
DEVELOPER_FIELDS = {"name", "country"}
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def is_text(value):
    return isinstance(value, str) and value.strip() != ""


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def check_developers(developers, errors):
    names = set()
    for i, dev in enumerate(developers):
        where = f"developers[{i}]"
        if not isinstance(dev, dict):
            errors.append(f"{where}: must be an object like {{\"name\": ..., \"country\": ...}}")
            continue
        for key in sorted(set(dev) - DEVELOPER_FIELDS):
            errors.append(f"{where}: unknown field \"{key}\"")
        name = dev.get("name")
        if not is_text(name):
            errors.append(f"{where}: \"name\" must be a non-empty string")
            continue
        if name in names:
            errors.append(f"{where}: developer \"{name}\" is listed twice")
        names.add(name)
        if dev.get("country") is not None and not is_text(dev["country"]):
            errors.append(f"{where} ({name}): \"country\" must be a string or null")
    return names


def check_game(game, i, developer_names, errors):
    if not isinstance(game, dict):
        errors.append(f"games[{i}]: must be an object")
        return
    where = f"games[{i}] (id {game.get('id')}, {game.get('title')!r})"

    for key in sorted(GAME_FIELDS - set(game)):
        errors.append(f"{where}: missing field \"{key}\" (use null if unknown)")
    for key in sorted(set(game) - GAME_FIELDS):
        errors.append(f"{where}: unknown field \"{key}\"")

    if "id" in game and not (is_int(game["id"]) and game["id"] > 0):
        errors.append(f"{where}: \"id\" must be a positive whole number")
    if "title" in game and not is_text(game["title"]):
        errors.append(f"{where}: \"title\" must be a non-empty string")
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
        errors.append(f"{where}: developer {dev!r} is not in the \"developers\" list "
                      "(add it there, spelled exactly the same)")

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
            if not (ROOT / image.lstrip("/")).is_file():
                errors.append(f"{where}: \"image_url\" points to {image}, which doesn't exist")
        elif not image.startswith("https://"):
            errors.append(f"{where}: \"image_url\" must start with https:// or /static/")


def check(catalog):
    errors = []
    if not isinstance(catalog, dict) or set(catalog) != {"developers", "games"}:
        return ["the file must be an object with exactly two keys: \"developers\" and \"games\""]
    if not isinstance(catalog["developers"], list) or not isinstance(catalog["games"], list):
        return ["\"developers\" and \"games\" must both be lists"]

    developer_names = check_developers(catalog["developers"], errors)
    ids, titles = {}, {}
    for i, game in enumerate(catalog["games"]):
        check_game(game, i, developer_names, errors)
        if not isinstance(game, dict):
            continue
        game_id, title = game.get("id"), game.get("title")
        if is_int(game_id):
            if game_id in ids:
                errors.append(f"games[{i}]: id {game_id} is already used by {ids[game_id]!r}")
            ids.setdefault(game_id, title)
        if is_text(title):
            key = title.casefold()
            if key in titles:
                errors.append(f"games[{i}]: {title!r} is already in the catalog "
                              f"(games[{titles[key]}])")
            titles.setdefault(key, i)
    return errors


def main():
    try:
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"data/games.json is not valid JSON: {e.msg} at line {e.lineno}, column {e.colno}.")
        print("Look for a missing comma, quote or bracket just before that spot.")
        return 1

    errors = check(catalog)
    if errors:
        print(f"Found {len(errors)} problem(s) in data/games.json:\n")
        print("\n".join(f"  - {e}" for e in errors))
        return 1
    print(f"data/games.json looks good: {len(catalog['games'])} games, "
          f"{len(catalog['developers'])} developers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
