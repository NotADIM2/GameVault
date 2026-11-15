from flask import Blueprint, abort, render_template, session

from backend import queries

main_bp = Blueprint('main', __name__)

FEATURED_COUNT = 4
ROW_SIZE = 10


def _owned_ids():
    user_id = session.get('user_id')
    return queries.owned_game_ids(user_id) if user_id else set()


@main_bp.route("/")
def home():
    games = queries.list_games()

    def released(game):
        return game['release_date'] or ''

    popular = sorted(
        games,
        key=lambda g: (g['owner_count'], g['avg_rating'] or 0, released(g)),
        reverse=True,
    )
    featured = popular[:FEATURED_COUNT]
    rest = popular[FEATURED_COUNT:]

    # (heading, store query string, games)
    sections = [
        ("Popular right now", "sort=popular", [g for g in rest if g['owner_count']]),
        ("New releases", "sort=new", sorted(filter(released, rest), key=released, reverse=True)),
        (
            "Top rated",
            "sort=rating",
            sorted((g for g in games if g['avg_rating']), key=lambda g: g['avg_rating'],
                   reverse=True),
        ),
        ("Free to play", "price=free", [g for g in rest if not g['price']]),
    ]
    sections = [(title, query, rows[:ROW_SIZE]) for title, query, rows in sections if rows]

    return render_template(
        "index.html", featured=featured, sections=sections, owned_ids=_owned_ids()
    )


@main_bp.route("/store")
def store():
    games = queries.list_games()
    genres = sorted({genre for game in games for genre in game['genres']})
    return render_template("store.html", games=games, genres=genres, owned_ids=_owned_ids())


@main_bp.route("/game/<int:game_id>")
def game(game_id):
    game = queries.get_game(game_id)
    if game is None:
        abort(404)

    user_id = session.get('user_id')
    reviews = queries.list_reviews(game_id)
    return render_template(
        "game.html",
        game=game,
        reviews=reviews,
        owned=game_id in _owned_ids(),
        my_review=next((r for r in reviews if r['user_id'] == user_id), None),
    )
