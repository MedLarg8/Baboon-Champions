import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, CalendarClock, Hash, Loader2 } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { ApiError, matchApi } from "../api/client";
import { MatchParticipantsTable } from "../components/MatchParticipantsTable";
import { formatDateTime, formatDuration } from "../utils/format";

export function MatchDetailPage() {
  const { id } = useParams();
  const matchId = Number(id);
  const matchQuery = useQuery({
    queryKey: ["matches", matchId],
    queryFn: () => matchApi.getMatch(matchId),
    enabled: Number.isInteger(matchId) && matchId > 0,
  });

  if (!Number.isInteger(matchId) || matchId <= 0) {
    return (
      <div className="page">
        <PageState tone="error" message="Match not found." />
      </div>
    );
  }

  return (
    <div className="page match-detail-page">
      <Link className="back-link" to="/matches">
        <ArrowLeft size={18} aria-hidden="true" />
        <span>Match history</span>
      </Link>

      {matchQuery.isLoading ? <PageState tone="info" message="Loading match..." /> : null}
      {matchQuery.isError ? <PageState tone="error" message={getErrorMessage(matchQuery.error)} /> : null}

      {matchQuery.data ? (
        <>
          <section className="surface match-detail-header">
            <div>
              <p className="eyebrow">{matchQuery.data.baboons.length > 1 ? "Co-Baboons" : "Baboon"}</p>
              <h1>{matchQuery.data.baboons.map((baboon) => baboon.display_name).join(", ")}</h1>
            </div>
            <dl className="detail-metrics">
              <div>
                <dt>
                  <CalendarClock size={16} aria-hidden="true" />
                  Date
                </dt>
                <dd>{formatDateTime(matchQuery.data.game_end_time)}</dd>
              </div>
              <div>
                <dt>Duration</dt>
                <dd>{formatDuration(matchQuery.data.duration_seconds)}</dd>
              </div>
              <div>
                <dt>
                  <Hash size={16} aria-hidden="true" />
                  Riot match
                </dt>
                <dd>{matchQuery.data.riot_match_id}</dd>
              </div>
              <div>
                <dt>Game version</dt>
                <dd>{matchQuery.data.game_version ?? "Unknown"}</dd>
              </div>
            </dl>
          </section>

          <section className="surface">
            <div className="section-title">
              <Hash size={22} aria-hidden="true" />
              <h2>Registered participants</h2>
            </div>
            <MatchParticipantsTable participants={matchQuery.data.participants} />
          </section>
        </>
      ) : null}
    </div>
  );
}

function PageState({ tone, message }: { tone: "error" | "info"; message: string }) {
  return (
    <div className={`list-state ${tone}`}>
      <Loader2 className={tone === "info" ? "spin" : undefined} size={24} aria-hidden="true" />
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
