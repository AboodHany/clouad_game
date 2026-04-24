import { fetchGameState, submitAnswer } from "./api.js";

const params = new URLSearchParams(window.location.search);
const gameId = params.get("gameId") || localStorage.getItem("quizGameId") || "";
const playerId = params.get("playerId") || localStorage.getItem("quizPlayerId") || "";
const username = params.get("username") || localStorage.getItem("quizUsername") || "Player";

const roomMeta = document.getElementById("roomMeta");
const gameStatus = document.getElementById("gameStatus");
const timer = document.getElementById("timer");
const questionText = document.getElementById("questionText");
const answerOptions = document.getElementById("answerOptions");
const answerForm = document.getElementById("answerForm");
const answerFeedback = document.getElementById("answerFeedback");
const playerScore = document.getElementById("playerScore");
const playerList = document.getElementById("playerList");

let currentQuestionId = null;
let currentTimeRemaining = 0;
let countdownHandle = null;

function renderPlayers(players) {
  playerList.innerHTML = players
    .map((player) => `<li class="player-item"><strong>${player.username}</strong> - ${player.score} pts</li>`)
    .join("");
}

function renderQuestion(question) {
  if (!question) {
    questionText.textContent = "The game is finished. Check the leaderboard.";
    answerOptions.innerHTML = "";
    answerForm.querySelector("button").disabled = true;
    return;
  }

  questionText.textContent = question.text;
  answerOptions.innerHTML = question.options
    .map(
      (option, index) => `
        <label class="answer-option">
          <input type="radio" name="answer" value="${option}" ${index === 0 ? "checked" : ""} />
          <span>${option}</span>
        </label>
      `,
    )
    .join("");
  answerForm.querySelector("button").disabled = false;
}

function updateCountdown(seconds) {
  currentTimeRemaining = seconds;
  timer.textContent = `${seconds}s`;
  timer.style.background = seconds <= 5 ? "#fde2e1" : "var(--accent-soft)";
}

function startCountdown(seconds) {
  clearInterval(countdownHandle);
  updateCountdown(seconds);

  countdownHandle = setInterval(() => {
    if (currentTimeRemaining <= 0) {
      clearInterval(countdownHandle);
      return;
    }

    updateCountdown(currentTimeRemaining - 1);
  }, 1000);
}

async function refreshState() {
  if (!gameId || !playerId) {
    roomMeta.textContent = "Missing game data. Go back to the home page.";
    return;
  }

  try {
    const state = await fetchGameState(gameId, playerId);
    roomMeta.textContent = `Room ${state.gameId} • ${username}`;
    gameStatus.textContent = state.status === "finished" ? "Finished" : `Question ${state.currentQuestionIndex + 1} of ${state.totalQuestions}`;

    const currentPlayer = state.currentPlayer || { score: 0 };
    playerScore.textContent = currentPlayer.score;
    renderPlayers(state.players);

    if (state.currentQuestion?.id !== currentQuestionId) {
      currentQuestionId = state.currentQuestion?.id || null;
      renderQuestion(state.currentQuestion);
      answerFeedback.textContent = "";
    }

    if (state.currentQuestion) {
      startCountdown(state.timeRemaining);
    } else {
      clearInterval(countdownHandle);
      timer.textContent = "0s";
    }
  } catch (error) {
    roomMeta.textContent = error.message;
  }
}

answerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const selectedAnswer = answerForm.querySelector("input[name='answer']:checked");

  if (!selectedAnswer) {
    answerFeedback.textContent = "Please choose an answer.";
    return;
  }

  if (currentTimeRemaining <= 0) {
    answerFeedback.textContent = "Time is up. Wait for the next question.";
    return;
  }

  try {
    const response = await submitAnswer(gameId, playerId, selectedAnswer.value);
    answerFeedback.textContent = response.message;
    await refreshState();
  } catch (error) {
    answerFeedback.textContent = error.message;
  }
});

window.addEventListener("load", async () => {
  await refreshState();
  setInterval(refreshState, 2500);
});