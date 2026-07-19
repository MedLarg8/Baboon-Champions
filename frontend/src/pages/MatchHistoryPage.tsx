import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, History, Loader2, Trophy } from "lucide-react";
import { Link } from "react-router-dom";

import { ApiError, matchApi } from "../api/client";
import { formatDateTime, formatDuration, formatNumber } from "../utils/format";

const PAGE_SIZE = 10;

export function MatchHistoryPage() {
  const [offset, setOffset] = useState(0);
  const matchesQuery = useQuery({
    queryKey: ["matches", { limit: PAGE_SIZE, offset }],
    queryFn: () => matchApi.listMatches({ limit: PAGE_SIZE, offset }),
  });

  const matches = matchesQuery.data?.items ?? [];
  const canGoBack = offset > 0;
  const canGoForward = matchesQuery.data ? offset + matches.length < matchesQuery.data.total : false;

  return (
    <div className="page matches-page">
      <section className="page-heading">
        <p className="eyebrow">Match history</p>
        <h1>Eligible ARAM: Mayhem receipts.</h1>
      </section>

      <section className="surface">
        <div className="section-title">
          <History size={22} aria-hidden="true" />
          <h2>Imported matches</h2>
        </div>

        {matchesQuery.isLoading ? <PageState tone="info" message="Loading matches..." /> : null}
        {matchesQuery.isError ? <PageState tone="error" message={getErrorMessage(matchesQuery.error)} /> : null}
        {matchesQuery.isSuccess && matches.length === 0 && offset === 0 ? (
          <PageState tone="empty" message="No eligible matches have been imported yet." />
        ) : null}
        {matchesQuery.isSuccess && matches.length === 0 && offset > 0 ? (
          <PageState tone="empty" message="No more matches on this page." />
        ) : null}

        {matches.length > 0 ? (
          <div className="match-card-list">
            {matches.map((match) => {
              const coBaboon = match.baboons.length > 1;
              return (
                <article className="match-card" key={match.id}>
                  <div className="match-card-main">
                    <div>
                      <p className="match-date">{formatDateTime(match.game_end_time)}</p>
                      <h2>{coBaboon ? "Co-Baboons" : "Baboon"}: {match.baboons.map((baboon) => baboon.display_name).join(", ")}</h2>
                    </div>
                    <span className={match.team_won ? "result-badge win" : "result-badge loss"}>
                      {match.team_won ? "Win" : "Loss"}
                    </span>
                  </div>
                  <dl className="match-metrics">
                    <div>
                      <dt>Friends</dt>
                      <dd>{match.registered_friend_count}</dd>
                    </div>
                    <div>
                      <dt>Lowest damage</dt>
                      <dd>{formatNumber(match.lowest_damage_to_champions)}</dd>
                    </div>
                    <div>
                      <dt>Duration</dt>
                      <dd>{formatDuration(match.duration_seconds)}</dd>
                    </div>
                  </dl>
                  <Link className="secondary-action" to={`/matches/${match.id}`}>
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
            disabled={!canGoBack || matchesQuery.isFetching}
          >
            <ChevronLeft size={18} aria-hidden="true" />
            <span>Previous</span>
          </button>
          <button
            className="icon-text-button"
            type="button"
            onClick={() => setOffset((current) => current + PAGE_SIZE)}
            disabled={!canGoForward || matchesQuery.isFetching}
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
