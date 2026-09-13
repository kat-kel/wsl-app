import type { Country } from "../types/country";

const API_BASE = "/api";

export async function fetchCountries(): Promise<Country[]> {
  const response = await fetch(`${API_BASE}/countries`);
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json();
}
