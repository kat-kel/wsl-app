import "@testing-library/jest-dom/vitest";
import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { PlayersPage } from "../../src/pages/players";

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
});

afterEach(() => {
  vi.unstubAllGlobals();
});

it("renders the players page", () => {
  render(<PlayersPage />);

  expect(
    screen.getByRole("heading", { name: "Players" }),
  ).toBeInTheDocument();
});

it("renders players returned by the API", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        {
          id: 1,
          display_name: "Alex Morgan",
          normalized_name: "alex morgan",
          position: "Forward",
          country: "USA",
        },
      ],
    }),
  );

  render(<PlayersPage />);

  expect(await screen.findByRole("heading", { name: "Alex Morgan" })).toBeInTheDocument();
  expect(screen.getByText("Forward")).toBeInTheDocument();
  expect(screen.getByText("USA")).toBeInTheDocument();
});
