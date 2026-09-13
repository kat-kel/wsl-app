import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { PlayersPage } from "./pages/players";
import "flag-icons/css/flag-icons.min.css";
import "./styles.css";

function App() {
  if (window.location.pathname === "/players") {
    return <PlayersPage />;
  }

  return (
    <main>
      <p>WSL frontend</p>
      <h1>Fullstack foundation ready.</h1>
      <a href="/players">View players</a>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
