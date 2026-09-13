import type { Team } from "@/types/team";

const API_BASE = "/api";

export async function fetchTeams(): Promise<Team[]> {
  const response = await fetch(`${API_BASE}/teams`);
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json();
}
