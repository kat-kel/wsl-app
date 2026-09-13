import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { PlayersPage } from "@/pages/players";

const PLAYER = {
  id: 1,
  full_name: "Ella Toone",
  normalized_name: "ella toone",
  shirt_name: "Toone",
  position: "midfielder",
  country_code: "GB-ENG",
  no: 7,
  team_code: "MUN",
};

const COUNTRY = { code: "GB-ENG", fa_code: "ENG", name: "England" };

const TEAM = {
  id: 1,
  code: "MUN",
  full_name: "Manchester United FC",
  short_name: "Manchester United",
};

function stubFetch(overrides: Record<string, unknown[]> = {}) {
  const bodies: Record<string, unknown[]> = {
    "/api/players": [PLAYER],
    "/api/countries": [COUNTRY],
    "/api/teams": [TEAM],
    ...overrides,
  };

  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => ({
      ok: true,
      json: async () => bodies[url] ?? [],
    })),
  );
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
});

afterEach(() => {
  vi.unstubAllGlobals();
});

it("renders the players page", () => {
  render(<PlayersPage />);

  expect(screen.getByRole("heading", { name: "Players" })).toBeInTheDocument();
});

it("renders players returned by the API", async () => {
  stubFetch();
  render(<PlayersPage />);

  // The heading's accessible name also includes the flag's aria-label.
  expect(await screen.findByRole("heading", { name: /Toone/ })).toBeInTheDocument();
  expect(screen.getByText("Ella Toone")).toBeInTheDocument();
  expect(screen.getByText("midfielder")).toBeInTheDocument();
});

it("resolves the country code to a country name", async () => {
  stubFetch();
  render(<PlayersPage />);

  expect(await screen.findByText("England")).toBeInTheDocument();
});

it("resolves the team code to a team name", async () => {
  stubFetch();
  render(<PlayersPage />);

  expect(await screen.findByText("Manchester United")).toBeInTheDocument();
});

it("shows Unknown when a player has no team", async () => {
  stubFetch({ "/api/players": [{ ...PLAYER, team_code: null }] });
  render(<PlayersPage />);

  expect(await screen.findByText("Unknown")).toBeInTheDocument();
});

it("shows Unknown when the team code matches no team", async () => {
  stubFetch({ "/api/teams": [] });
  render(<PlayersPage />);

  expect(await screen.findByText("Unknown")).toBeInTheDocument();
});
