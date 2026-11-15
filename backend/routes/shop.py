from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from backend import queries
from backend.routes.auth import login_required

shop_bp = Blueprint('shop', __name__)

MAX_REVIEW_LENGTH = 2000


@shop_bp.post("/buy/<int:game_id>")
@login_required
def buy_game(game_id):
    """Add a game to the user's library (one transaction, see purchase_game in schema.sql)."""
    added = queries.purchase_game(session['user_id'], game_id)
    if added is None:
        abort(404)
    if added:
        flash("Game added to your library!", "success")
    else:
        flash("You already own this game.", "info")
    return redirect(url_for('shop.library', game=game_id))


@shop_bp.route("/library")
@login_required
def library():
    """Display user's game library"""
    games = queries.list_library(session['user_id'])
    return render_template("library.html", games=games)


@shop_bp.post("/library/<int:game_id>/play")
@login_required
def play_game(game_id):
    if not queries.mark_played(session['user_id'], game_id):
        abort(404)
    return '', 204


@shop_bp.post("/game/<int:game_id>/review")
@login_required
def review_game(game_id):
    body = request.form.get('body', '').strip()
    rating = request.form.get('rating', type=int)

    if rating is None or not 1 <= rating <= 5:
        flash("Pick a rating from 1 to 5.", "error")
    elif len(body) > MAX_REVIEW_LENGTH:
        flash(f"Reviews can be at most {MAX_REVIEW_LENGTH} characters.", "error")
    elif not queries.save_review(session['user_id'], game_id, rating, body):
        flash("You can only review games in your library.", "error")
    else:
        flash("Review saved.", "success")
    return redirect(url_for('main.game', game_id=game_id) + '#reviews')
