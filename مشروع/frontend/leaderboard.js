import { fetchLeaderboard } from "./api.js";

const params = new URLSearchParams(window.location.search);
const gameId = params.get("gameId") || localStorage.getItem("quizGameId") || "";
const leaderboardMeta = document.getElementById("leaderboardMeta");
const leaderboardList = document.getElementById("leaderboardList");

async function loadLeaderboard() {
  if (!gameId) {
    leaderboardMeta.textContent = "Missing game code.";
    return;
  }

  try {
    const data = await fetchLeaderboard(gameId);
    leaderboardMeta.textContent = `Room ${data.gameId}`;
    leaderboardList.innerHTML = data.players
      .map(
        (player, index) => `
          <li class="leaderboard-item">
            <strong>${index + 1}. ${player.username}</strong>
            <span>${player.score} points</span>
          </li>
        `,
      )
      .join("");
  } catch (error) {
    leaderboardMeta.textContent = error.message;
  }
}

window.addEventListener("load", loadLeaderboard);