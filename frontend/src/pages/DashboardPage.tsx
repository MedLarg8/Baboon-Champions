import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, Crown, History, Loader2, RefreshCw, Trophy } from "lucide-react";
import { Link } from "react-router-dom";

import { ApiError, baboonApi, matchApi } from "../api/client";
import { MatchParticipantsTable } from "../components/MatchParticipantsTable";
import type { MatchSyncSummary } from "../types/match";
import {
  formatDateTime,
  formatDuration,
  formatKda,
  formatNumber,
  formatRiotId,
} from "../utils/format";

export function DashboardPage() {
  const queryClient = useQueryClient();
  const currentBaboonQuery = useQuery({
    queryKey: ["currentBaboon"],
    queryFn: baboonApi.getCurrentBaboon,
  });
  const latestMatchesQuery = useQuery({
    queryKey: ["matches", { limit: 1, offset: 0 }],
    queryFn: () => matchApi.listMatches({ limit: 1, offset: 0 }),
  });

  const syncMutation = useMutation({
    mutationFn: matchApi.syncMatches,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["currentBaboon"] });
      void queryClient.invalidateQueries({ queryKey: ["matches"] });
    },
  });

  const current = currentBaboonQuery.data;
  const latestMatch = latestMatchesQuery.data?.[0];
  const hasCoBaboons = (current?.baboons.length ?? 0) > 1;

  return (
    <div className="page dashboard-page">
      <section className="dashboard-topline">
        <div className="page-heading">
          <p className="eyebrow">ARAM: Mayhem queue 2400</p>
          <h1>{hasCoBaboons ? "Current Co-Baboons" : "Current Baboon"}</h1>
          <p>Manual sync checks recent Riot matches for registered friends and imports eligible shared games.</p>
        </div>

        <button
          className="sync-button"
          type="button"
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
        >
          {syncMutation.isPending ? (
            <Loader2 className="spin" size={19} aria-hidden="true" />
          ) : (
            <RefreshCw size={19} aria-hidden="true" />
          )}
          <span>{syncMutation.isPending ? "Checking Riot match history..." : "Check for new matches"}</span>
        </button>
      </section>

      {syncMutation.data ? <SyncSummary summary={syncMutation.data} /> : null}
      {syncMutation.isError ? <DashboardState tone="error" message={getErrorMessage(syncMutation.error)} /> : null}

      <section className="current-baboon-zone">
        {currentBaboonQuery.isLoading ? <DashboardState tone="info" message="Loading current Baboon..." /> : null}
        {currentBaboonQuery.isError ? (
          <DashboardState tone="error" message={getErrorMessage(currentBaboonQuery.error)} />
        ) : null}

        {current && !current.has_current_baboon ? (
          <section className="surface no-history-panel">
            <Trophy size={42} aria-hidden="true" />
            <div>
              <h2>No Baboon has been crowned yet.</h2>
              <p>
                Register at least two friends, play an ARAM: Mayhem match together, then sync the latest games.
              </p>
            </div>
          </section>
        ) : null}

        {current?.has_current_baboon ? (
          <section className="baboon-hero">
            <div className="baboon-hero-copy">
              <p className="eyebrow">{hasCoBaboons ? "Current Co-Baboons" : "Current Baboon"}</p>
              <h2>Crowned after dealing the least champion damage.</h2>
              {current.match ? (
                <Link className="secondary-action" to={`/matches/${current.match.id}`}>
                  View the match
                </Link>
              ) : null}
            </div>

            <div className="baboon-card-grid">
              {current.baboons.map((baboon) => (
                <article className="baboon-card" key={`${baboon.friend_id}-${baboon.display_name}`}>
                  <span className="baboon-badge">
                    <Crown size={18} aria-hidden="true" />
                    {hasCoBaboons ? "Co-Baboon" : "Baboon"}
                  </span>
                  <h3>{baboon.display_name}</h3>
                  <p>{formatRiotId(baboon.game_name, baboon.tag_line)}</p>
                  <dl className="baboon-stats">
                    <div>
                      <dt>Champion</dt>
                      <dd>{baboon.champion_name ?? "Unknown"}</dd>
                    </div>
                    <div>
                      <dt>Damage</dt>
                      <dd>{formatNumber(baboon.damage_to_champions)}</dd>
                    </div>
                    <div>
                      <dt>KDA</dt>
                      <dd>{formatKda(baboon.kills, baboon.deaths, baboon.assists)}</dd>
                    </div>
                    <div>
                      <dt>Result</dt>
                      <dd>{baboon.win ? "Win" : "Loss"}</dd>
                    </div>
                  </dl>
                  {current.match ? <small>Match ended {formatDateTime(current.match.game_end_time)}</small> : null}
                </article>
              ))}
            </div>
          </section>
        ) : null}
      </section>

      <section className="surface">
        <div className="section-title">
          <History size={22} aria-hidden="true" />
          <h2>Latest imported match</h2>
        </div>

        {latestMatchesQuery.isLoading ? <DashboardState tone="info" message="Loading latest match..." /> : null}
        {latestMatchesQuery.isError ? (
          <DashboardState tone="error" message={getErrorMessage(latestMatchesQuery.error)} />
        ) : null}
        {latestMatchesQuery.isSuccess && !latestMatch ? (
          <DashboardState tone="empty" message="No imported matches yet." />
        ) : null}
        {latestMatch ? (
          <div className="latest-match-block">
            <div className="latest-match-meta">
              <span>{formatDateTime(latestMatch.game_end_time)}</span>
              <span>{formatDuration(latestMatch.duration_seconds)}</span>
              <span>{latestMatch.team_won ? "Win" : "Loss"}</span>
            </div>
            <MatchParticipantsTable participants={latestMatch.participants} />
          </div>
        ) : null}
      </section>
    </div>
  );
}

function SyncSummary({ summary }: { summary: MatchSyncSummary }) {
  const tone = summary.matches_imported > 0 ? "success" : summary.matches_skipped > 0 ? "warning" : "info";
  return (
    <section className={`sync-summary ${tone}`}>
      <AlertCircle size={20} aria-hidden="true" />
      <div>
        <strong>{syncSummaryTitle(summary)}</strong>
        <p>{syncSummaryDetail(summary)}</p>
      </div>
    </section>
  );
}

function syncSummaryTitle(summary: MatchSyncSummary): string {
  if (summary.matches_imported > 0) {
    return `${summary.matches_imported} new match${summary.matches_imported === 1 ? "" : "es"} imported.`;
  }
  if (summary.status === "not_enough_friends") {
    return "At least two friends are needed before syncing.";
  }
  if (summary.matches_skipped > 0) {
    return "Matches were found, but none were eligible.";
  }
  return "No new match found.";
}

function syncSummaryDetail(summary: MatchSyncSummary): string {
  const skipped = Object.entries(summary.skipped_reasons)
    .map(([reason, count]) => `${count} ${reason.replace(/_/g, " ")}`)
    .join(", ");

  if (summary.matches_imported > 0) {
    return `${summary.friends_checked} friends checked, ${summary.candidate_match_ids} candidates found.`;
  }
  if (skipped) {
    return skipped;
  }
  return `${summary.friends_checked} friends checked, ${summary.matches_already_known} matches already known.`;
}

function DashboardState({ tone, message }: { tone: "error" | "info" | "empty"; message: string }) {
  const Icon = tone === "info" ? Loader2 : AlertCircle;

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
