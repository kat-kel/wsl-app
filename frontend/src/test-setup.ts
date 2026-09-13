import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Not automatic here: React Testing Library only self-registers cleanup when
// vitest runs with globals enabled. Without this, each render stays in the DOM
// and later queries match elements left behind by earlier tests.
afterEach(cleanup);
