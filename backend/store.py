from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Callable


class GameStore:
    """A tiny JSON-backed data store for quiz games."""

    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()
        if not self.storage_path.exists():
            self._write({"games": {}})

    def _read(self) -> dict:
        """Read the game database from disk."""

        with self.storage_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _write(self, payload: dict) -> None:
        """Write the game database to disk."""

        with self.storage_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)

    def get_game(self, game_id: str) -> dict | None:
        """Return a single game by ID if it exists."""

        with self.lock:
            data = self._read()
            game = data.get("games", {}).get(game_id)
            return deepcopy(game) if game else None

    def save_game(self, game: dict) -> None:
        """Persist the provided game back to disk."""

        with self.lock:
            data = self._read()
            data.setdefault("games", {})[game["id"]] = game
            self._write(data)

    def createGame(self, username: str, generate_id: Callable[[], str], now_iso: Callable[[], str]) -> dict:
        """Create a new game with an initial player."""

        with self.lock:
            data = self._read()
            games = data.setdefault("games", {})

            game_id = generate_id()
            while game_id in games:
                game_id = generate_id()

            player_id = f"p-{game_id.lower()}"
            game = {
                "id": game_id,
                "createdAt": now_iso(),
                "status": "active",
                "currentQuestionIndex": 0,
                "currentQuestionStartedAt": now_iso(),
                "players": [
                    {
                        "id": player_id,
                        "username": username,
                        "score": 0,
                        "joinedAt": now_iso(),
                    }
                ],
                "answers": {},
            }

            games[game_id] = game
            self._write(data)
            return deepcopy(game)

    def joinGame(self, game_id: str, username: str, now_iso: Callable[[], str]) -> dict:
        """Add a player to an existing game."""

        with self.lock:
            data = self._read()
            game = data.get("games", {}).get(game_id)
            if not game:
                raise ValueError("Game not found.")

            if any(player["username"].lower() == username.lower() for player in game["players"]):
                raise ValueError("That username is already taken in this game.")

            player_id = f"p{len(game['players']) + 1}-{game_id.lower()}"
            game["players"].append(
                {
                    "id": player_id,
                    "username": username,
                    "score": 0,
                    "joinedAt": now_iso(),
                }
            )

            data["games"][game_id] = game
            self._write(data)
            return deepcopy(game)

    def _parse_time(self, value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    def _question_answers(self, game: dict, question_index: int) -> dict:
        return game.setdefault("answers", {}).setdefault(str(question_index), {})

    def _advance_if_needed(self, game: dict, questions: list[dict], time_limit_seconds: int, now: datetime | None = None) -> dict:
        """Move the game to the next question when time expires or everyone answers."""

        now = now or datetime.now(timezone.utc)
        if game.get("status") == "finished":
            return game

        while True:
            current_index = game.get("currentQuestionIndex", 0)
            if current_index >= len(questions):
                game["status"] = "finished"
                return game

            started_at = self._parse_time(game["currentQuestionStartedAt"])
            elapsed = (now - started_at).total_seconds()
            answers = self._question_answers(game, current_index)
            if elapsed < time_limit_seconds and len(answers) < len(game.get("players", [])):
                return game

            game["currentQuestionIndex"] = current_index + 1
            if game["currentQuestionIndex"] >= len(questions):
                game["status"] = "finished"
                return game

            game["currentQuestionStartedAt"] = now.isoformat()

    def advance_game_if_needed(self, game: dict, questions: list[dict], time_limit_seconds: int) -> dict:
        """Public wrapper around the state progression helper."""

        with self.lock:
            game = deepcopy(game)
            advanced_game = self._advance_if_needed(game, questions, time_limit_seconds)
            data = self._read()
            data.setdefault("games", {})[advanced_game["id"]] = advanced_game
            self._write(data)
            return deepcopy(advanced_game)

    def submitAnswer(
        self,
        game: dict,
        questions: list[dict],
        time_limit_seconds: int,
        player_id: str,
        answer: str,
        now_iso: Callable[[], str],
    ) -> tuple[dict, dict]:
        """Check an answer, update score if correct, and return the response payload."""

        with self.lock:
            game = deepcopy(game)
            now = self._parse_time(now_iso())
            game = self._advance_if_needed(game, questions, time_limit_seconds, now)

            if game.get("status") == "finished":
                raise ValueError("This game has already finished.")

            player = next((item for item in game.get("players", []) if item["id"] == player_id), None)
            if not player:
                raise ValueError("Player not found in this game.")

            question_index = game.get("currentQuestionIndex", 0)
            if question_index >= len(questions):
                game["status"] = "finished"
                return game, {"status": "finished", "correct": False, "score": player["score"]}

            answers = self._question_answers(game, question_index)
            if player_id in answers:
                raise ValueError("You already answered this question.")

            question = questions[question_index]
            correct = answer.strip().lower() == str(question["correctAnswer"]).strip().lower()
            answers[player_id] = answer
            if correct:
                player["score"] += 1

            game = self._advance_if_needed(game, questions, time_limit_seconds, now)

            data = self._read()
            data.setdefault("games", {})[game["id"]] = game
            self._write(data)
            return deepcopy(game), {
                "status": "ok",
                "correct": correct,
                "score": player["score"],
                "message": "Correct answer!" if correct else "Answer saved.",
            }

    def getLeaderboard(self, game: dict) -> list[dict]:
        """Return players ordered by score, highest first."""

        players = deepcopy(game.get("players", []))
        return sorted(players, key=lambda player: (-player["score"], player["joinedAt"], player["username"].lower()))

    def get_public_state(
        self,
        game: dict,
        questions: list[dict],
        player_id: str,
        time_limit_seconds: int,
    ) -> dict:
        """Return a frontend-friendly snapshot of the current game state."""

        game = self._advance_if_needed(deepcopy(game), questions, time_limit_seconds)
        current_index = game.get("currentQuestionIndex", 0)
        current_question = questions[current_index] if current_index < len(questions) and game.get("status") != "finished" else None
        started_at = self._parse_time(game["currentQuestionStartedAt"])
        remaining = max(0, time_limit_seconds - int((datetime.now(timezone.utc) - started_at).total_seconds()))

        current_player = next((player for player in game.get("players", []) if player["id"] == player_id), None)
        return {
            "gameId": game["id"],
            "status": game.get("status", "active"),
            "currentQuestionIndex": current_index,
            "timeRemaining": 0 if current_question is None else remaining,
            "currentQuestion": None
            if current_question is None
            else {
                "id": current_question["id"],
                "text": current_question["question"],
                "options": current_question["options"],
            },
            "currentPlayer": current_player,
            "players": self.getLeaderboard(game),
            "totalQuestions": len(questions),
        }