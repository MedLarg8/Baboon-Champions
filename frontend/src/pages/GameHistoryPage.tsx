import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, History, Loader2, Plus, Trophy } from "lucide-react";
import { Link } from "react-router-dom";

import { ApiError, gameApi } from "../api/client";
import { formatDateTime, formatNumber } from "../utils/format";

const PAGE_SIZE = 10;

export function GameHistoryPage() {
  const [offset, setOffset] = useState(0);
  const gamesQuery = useQuery({
    queryKey: ["games", { limit: PAGE_SIZE, offset }],
    queryFn: () => gameApi.listGames({ limit: PAGE_SIZE, offset }),
  });

  const games = gamesQuery.data?.items ?? [];
  const canGoBack = offset > 0;
  const canGoForward = gamesQuery.data ? offset + games.length < gamesQuery.data.total : false;

  return (
    <div className="page games-page">
      <section className="dashboard-topline">
        <div className="page-heading">
          <p className="eyebrow">Game history</p>
          <h1>Saved ARAM: Mayhem results.</h1>
        </div>
        <Link className="primary-action dashboard-action" to="/games/new">
          <Plus size={19} aria-hidden="true" />
          <span>Record a game</span>
        </Link>
      </section>

      <section className="surface">
        <div className="section-title">
          <History size={22} aria-hidden="true" />
          <h2>Games</h2>
        </div>

        {gamesQuery.isLoading ? <PageState tone="info" message="Loading games..." /> : null}
        {gamesQuery.isError ? <PageState tone="error" message={getErrorMessage(gamesQuery.error)} /> : null}
        {gamesQuery.isSuccess && games.length === 0 && offset === 0 ? (
          <PageState tone="empty" message="No games have been recorded yet." />
        ) : null}
        {gamesQuery.isSuccess && games.length === 0 && offset > 0 ? (
          <PageState tone="empty" message="No more games on this page." />
        ) : null}

        {games.length > 0 ? (
          <div className="match-card-list">
            {games.map((game) => {
              const coBaboon = game.baboons.length > 1;
              return (
                <article className="match-card" key={game.id}>
                  <div className="match-card-main">
                    <div>
                      <p className="match-date">{formatDateTime(game.played_at)}</p>
                      <h2>
                        {coBaboon ? "Co-Baboons" : "Baboon"}:{" "}
                        {game.baboons.map((baboon) => baboon.display_name).join(", ")}
                      </h2>
                    </div>
                    <span className="verdict-badge baboon">{coBaboon ? "Co-Baboons" : "Baboon"}</span>
                  </div>
                  <dl className="match-metrics">
                    <div>
                      <dt>Players</dt>
                      <dd>{game.player_count}</dd>
                    </div>
                    <div>
                      <dt>Lowest damage</dt>
                      <dd>{formatNumber(game.lowest_damage_to_champions)}</dd>
                    </div>
                    <div>
                      <dt>Result</dt>
                      <dd>{game.baboons.map((baboon) => baboon.display_name).join(", ")}</dd>
                    </div>
                  </dl>
                  <Link className="secondary-action" to={`/games/${game.id}`}>
                    View details
                  </Link>
                </article>
              );
            })}
          </div>
        ) : null}

        <div className="pagination-row">
          <button
            className="icon-text-button"
            type="button"
            onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}
            disabled={!canGoBack || gamesQuery.isFetching}
          >
            <ChevronLeft size={18} aria-hidden="true" />
            <span>Previous</span>
          </button>
          <button
            className="icon-text-button"
            type="button"
            onClick={() => setOffset((current) => current + PAGE_SIZE)}
            disabled={!canGoForward || gamesQuery.isFetching}
          >
            <span>Next</span>
            <ChevronRight size={18} aria-hidden="true" />
          </button>
        </div>
      </section>
    </div>
  );
}

function PageState({ tone, message }: { tone: "error" | "info" | "empty"; message: string }) {
  const Icon = tone === "info" ? Loader2 : Trophy;

  return (
    <div className={`list-state ${tone}`}>
      <Icon className={tone === "info" ? "spin" : undefined} size={24} aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Something went wrong.";
}
