const API_BASE = "/api";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || "Request failed.");
  }

  return data;
}

export function createGame(username) {
  return request("/games", {
    method: "POST",
    body: JSON.stringify({ username }),
  });
}

export function joinGame(gameId, username) {
  return request("/games/join", {
    method: "POST",
    body: JSON.stringify({ gameId, username }),
  });
}

export function fetchGameState(gameId, playerId) {
  const playerQuery = playerId ? `?playerId=${encodeURIComponent(playerId)}` : "";
  return request(`/games/${encodeURIComponent(gameId)}/state${playerQuery}`);
}

export function submitAnswer(gameId, playerId, answer) {
  return request(`/games/${encodeURIComponent(gameId)}/answers`, {
    method: "POST",
    body: JSON.stringify({ playerId, answer }),
  });
}

export function fetchLeaderboard(gameId) {
  return request(`/games/${encodeURIComponent(gameId)}/leaderboard`);
}