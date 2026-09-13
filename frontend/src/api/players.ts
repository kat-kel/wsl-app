import type { Player } from "../types/player";

const API_BASE = "/api";

export async function fetchPlayers(): Promise<Player[]> {
  const response = await fetch(`${API_BASE}/players`);
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json();
}
