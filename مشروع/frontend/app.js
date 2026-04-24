import { createGame, joinGame } from "./api.js";

function navigateToGame(gameId, playerId, username) {
  const params = new URLSearchParams({ gameId, playerId, username });
  window.location.href = `game.html?${params.toString()}`;
}

document.getElementById("createGameForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = document.getElementById("createUsername").value.trim();

  try {
    const data = await createGame(username);
    localStorage.setItem("quizGameId", data.gameId);
    localStorage.setItem("quizPlayerId", data.playerId);
    localStorage.setItem("quizUsername", data.username);
    navigateToGame(data.gameId, data.playerId, data.username);
  } catch (error) {
    alert(error.message);
  }
});

document.getElementById("joinGameForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const gameId = document.getElementById("gameCode").value.trim().toUpperCase();
  const username = document.getElementById("joinUsername").value.trim();

  try {
    const data = await joinGame(gameId, username);
    localStorage.setItem("quizGameId", data.gameId);
    localStorage.setItem("quizPlayerId", data.playerId);
    localStorage.setItem("quizUsername", data.username);
    navigateToGame(data.gameId, data.playerId, data.username);
  } catch (error) {
    alert(error.message);
  }
});