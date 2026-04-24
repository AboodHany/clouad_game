from __future__ import annotations

import json
import random
import string
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from store import GameStore


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"
DATA_DIR = BASE_DIR / "data"
QUESTIONS_PATH = DATA_DIR / "questions.json"
GAMES_PATH = DATA_DIR / "games.json"
QUESTION_TIME_LIMIT_SECONDS = 20


def load_questions() -> list[dict]:
    """Load quiz questions from disk and return a small sample set."""

    if not QUESTIONS_PATH.exists():
        return []

    with QUESTIONS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def now_iso() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""

    return datetime.now(timezone.utc).isoformat()


def generate_game_id(length: int = 6) -> str:
    """Generate a short uppercase game code for players to share."""

    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def create_app() -> Flask:
    """Create and configure the Flask application."""

    app = Flask(__name__, static_folder=None)
    store = GameStore(GAMES_PATH)
    questions = load_questions()

    if not questions:
        raise RuntimeError("No questions found. Please add backend/data/questions.json.")

    def get_game_or_404(game_id: str) -> tuple[dict, dict]:
        game = store.get_game(game_id)
        if not game:
            return {}, {"error": "Game not found."}

        game = store.advance_game_if_needed(game, questions, QUESTION_TIME_LIMIT_SECONDS)
        store.save_game(game)
        return game, {}

    @app.get("/")
    def home() -> object:
        """Serve the home page."""

        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/game.html")
    def game_page() -> object:
        """Serve the game screen."""

        return send_from_directory(FRONTEND_DIR, "game.html")

    @app.get("/leaderboard.html")
    def leaderboard_page() -> object:
        """Serve the leaderboard page."""

        return send_from_directory(FRONTEND_DIR, "leaderboard.html")

    @app.get("/<path:filename>")
    def frontend_assets(filename: str) -> object:
        """Serve frontend assets like CSS and JavaScript files."""

        if filename.startswith("api/"):
            return {"error": "Not found."}, 404

        file_path = FRONTEND_DIR / filename
        if not file_path.exists():
            return {"error": "Not found."}, 404

        return send_from_directory(FRONTEND_DIR, filename)

    @app.get("/api/health")
    def health() -> object:
        """Return a simple health check response."""

        return jsonify({"status": "ok"})

    @app.post("/api/games")
    def create_game() -> object:
        """Create a new game and add the creator as the first player."""

        payload = request.get_json(silent=True) or {}
        username = str(payload.get("username", "")).strip()

        if not username:
            return jsonify({"error": "Username is required."}), 400

        game = store.createGame(username, generate_game_id, now_iso)
        store.save_game(game)

        return jsonify(
            {
                "gameId": game["id"],
                "playerId": game["players"][0]["id"],
                "username": username,
            }
        ), 201

    @app.post("/api/games/join")
    def join_game() -> object:
        """Join an existing game with a unique username."""

        payload = request.get_json(silent=True) or {}
        game_id = str(payload.get("gameId", "")).strip().upper()
        username = str(payload.get("username", "")).strip()

        if not game_id or not username:
            return jsonify({"error": "Game code and username are required."}), 400

        try:
            game = store.joinGame(game_id, username, now_iso)
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

        store.save_game(game)
        player = next(player for player in game["players"] if player["username"].lower() == username.lower())

        return jsonify({"gameId": game["id"], "playerId": player["id"], "username": player["username"]})

    @app.get("/api/games/<game_id>/state")
    def game_state(game_id: str) -> object:
        """Return the current public game state for the frontend."""

        game, error_response = get_game_or_404(game_id.upper())
        if error_response:
            return jsonify(error_response), 404

        player_id = request.args.get("playerId", "").strip()
        state = store.get_public_state(game, questions, player_id, QUESTION_TIME_LIMIT_SECONDS)
        return jsonify(state)

    @app.post("/api/games/<game_id>/answers")
    def submit_answer(game_id: str) -> object:
        """Submit an answer for the current question."""

        payload = request.get_json(silent=True) or {}
        player_id = str(payload.get("playerId", "")).strip()
        answer = str(payload.get("answer", "")).strip()

        if not player_id or not answer:
            return jsonify({"error": "Player ID and answer are required."}), 400

        game = store.get_game(game_id.upper())
        if not game:
            return jsonify({"error": "Game not found."}), 404

        try:
            updated_game, result = store.submitAnswer(
                game,
                questions,
                QUESTION_TIME_LIMIT_SECONDS,
                player_id,
                answer,
                now_iso,
            )
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

        store.save_game(updated_game)
        return jsonify(result)

    @app.get("/api/games/<game_id>/leaderboard")
    def leaderboard(game_id: str) -> object:
        """Return the ranked player list for a game."""

        game, error_response = get_game_or_404(game_id.upper())
        if error_response:
            return jsonify(error_response), 404

        return jsonify({"gameId": game["id"], "players": store.getLeaderboard(game)})

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)