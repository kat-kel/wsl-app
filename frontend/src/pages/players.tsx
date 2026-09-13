import { useEffect, useState } from "react";
import { Player } from "@/types/player"
import { fetchPlayers } from "@api/players"
import { fetchCountries } from "@api/countries"
import { fetchTeams } from "@api/teams"
import { CountryFlag } from "@components/CountryFlag"


export function PlayersPage() {
    const [players, setPlayers] = useState<Player[]>([]);
    const [countryNames, setCountryNames] = useState<Record<string, string>>({});
    const [teamNames, setTeamNames] = useState<Record<string, string>>({});
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        Promise.all([fetchPlayers(), fetchCountries(), fetchTeams()])
        .then(([players, countries, teams]) => {
            setPlayers(players);
            setCountryNames(Object.fromEntries(countries.map((c) => [c.code, c.name])));
            setTeamNames(Object.fromEntries(teams.map((t) => [t.code, t.short_name])));
        })
        .catch((reason) => setError(reason.message))
        .finally(() => setIsLoading(false));
    }, []);

    return (
        <main className="max-w-[1100px] mx-auto px-8 py-28 max-md:px-5 max-md:py-16">
            <header className="flex items-end justify-between gap-8 mb-12 max-md:flex-col max-md:items-start max-md:gap-4 max-md:mb-8">
                <p>WSL player directory</p>
                <h1 className="m-0">Players</h1>
                {!isLoading && !error && (
                    <span className="text-brand-muted text-[1.1rem]">{players.length} players</span>
                )}
            </header>

            {isLoading && <p role="status">Loading players...</p>}
            {error && <p role="alert">Could not load players: {error}</p>}
            {!isLoading && !error && players.length === 0 && <p>No players found.</p>}

            {!isLoading && !error && players.length > 0 && (
                <section
                    className="grid gap-4 grid-cols-[repeat(auto-fit,minmax(220px,1fr))]"
                    aria-label="Players"
                >
                    {players.map((player) => (
                        <article
                            className="p-6 border border-brand-border bg-brand-surface"
                            key={player.id}
                        >
                            <h2 className="m-0 mb-8 text-2xl font-normal">
                                <span className="flex items-start justify-between gap-2">
                                    <span className="flex-1">{player.no}</span>
                                    <span className="min-w-0 flex-3">{player.shirt_name}</span>
                                    <span className="shrink-0 text-xs">
                                        <CountryFlag countryCode={player.country_code} />
                                    </span>
                                </span>
                            </h2>

                            <dl className="grid gap-3 m-0">
                                <div className="flex justify-between gap-4 border-t border-brand-border-light pt-2.5">
                                    <dt className="text-brand-muted text-xs tracking-wider uppercase">Name</dt>
                                    <dd className="m-0">{player.full_name ?? "Unknown"}</dd>
                                </div>
                                <div className="flex justify-between gap-4 border-t border-brand-border-light pt-2.5">
                                    <dt className="text-brand-muted text-xs tracking-wider uppercase">Position</dt>
                                    <dd className="m-0">{player.position}</dd>
                                </div>
                                <div className="flex justify-between gap-4 border-t border-brand-border-light pt-2.5">
                                    <dt className="text-brand-muted text-xs tracking-wider uppercase">Country</dt>
                                    <dd className="m-0">
                                        {countryNames[player.country_code] ?? "Unknown"}
                                    </dd>
                                </div>
                                <div className="flex justify-between gap-4 border-t border-brand-border-light pt-2.5">
                                    <dt className="text-brand-muted text-xs tracking-wider uppercase">Team</dt>
                                    <dd className="m-0">
                                        {(player.team_code && teamNames[player.team_code]) ?? "Unknown"}
                                    </dd>
                                </div>
                            </dl>
                        </article>
                    ))}
                </section>
            )}
        </main>
    );
}
