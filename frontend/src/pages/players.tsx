import { useEffect, useState } from "react";
import { Player } from "../types/player"
import { fetchPlayers } from "../api/players"


export function PlayersPage() {
    const [players, setPlayers] = useState<Player[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchPlayers()
        .then(setPlayers)
        .catch((reason) => setError(reason.message))
        .finally(() => setIsLoading(false));
    }, []);

    return (
        <main className="players-page">
            <header className="players-header">
                <p>WSL player directory</p>
                <h1>Players</h1>
                {!isLoading && !error && <span>{players.length} players</span>}
            </header>

            {isLoading && <p role="status">Loading players...</p>}
            {error && <p role="alert">Could not load players: {error}</p>}
            {!isLoading && !error && players.length === 0 && <p>No players found.</p>}

            {!isLoading && !error && players.length > 0 && (
                <section className="player-grid" aria-label="Players">
                    {players.map((player) => (
                        <article className="player-card" key={player.id}>
                            <h2>{player.display_name}</h2>
                            <dl>
                                <div>
                                    <dt>Position</dt>
                                    <dd>{player.position ?? "Unknown"}</dd>
                                </div>
                                <div>
                                    <dt>Country</dt>
                                    <dd>{player.country ?? "Unknown"}</dd>
                                </div>
                            </dl>
                        </article>
                    ))}
                </section>
            )}
        </main>
    );
}
