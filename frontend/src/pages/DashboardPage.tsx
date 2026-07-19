import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Crown, History, Loader2, Plus, Trophy } from "lucide-react";
import { Link } from "react-router-dom";

import { ApiError, baboonApi, friendApi, gameApi } from "../api/client";
import { ChampionPortrait } from "../components/ChampionPortrait";
import { GameParticipantsTable } from "../components/GameParticipantsTable";
import { formatDateTime, formatNumber, formatRiotId } from "../utils/format";

export function DashboardPage() {
  const currentBaboonQuery = useQuery({
    queryKey: ["currentBaboon"],
    queryFn: baboonApi.getCurrentBaboon,
  });
  const latestGamesQuery = useQuery({
    queryKey: ["games", { limit: 1, offset: 0 }],
    queryFn: () => gameApi.listGames({ limit: 1, offset: 0 }),
  });
  const friendsQuery = useQuery({
    queryKey: ["friends"],
    queryFn: friendApi.listFriends,
  });

  const current = currentBaboonQuery.data;
  const latestGame = latestGamesQuery.data?.items[0];
  const hasCoBaboons = (current?.baboons.length ?? 0) > 1;
  const registeredFriendCount = friendsQuery.data?.length ?? 0;

  return (
    <div className="page dashboard-page">
      <section className="dashboard-topline">
        <div className="page-heading">
          <p className="eyebrow">Manual ARAM: Mayhem ledger</p>
          <h1>{hasCoBaboons ? "Current Co-Baboons" : "Current Baboon"}</h1>
          <p>Record the roster, champions, and damage. The backend crowns the lowest damage automatically.</p>
        </div>

        <Link className="primary-action dashboard-action" to="/games/new">
          <Plus size={19} aria-hidden="true" />
          <span>Record a game</span>
        </Link>
      </section>

      <section className="friend-status-row">
        <span>
          {friendsQuery.isLoading
            ? "Loading registered friends..."
            : `${registeredFriendCount} registered friend${registeredFriendCount === 1 ? "" : "s"}`}
        </span>
        {!friendsQuery.isLoading && registeredFriendCount < 2 ? (
          <Link to="/friends">Register at least two friends before recording a game.</Link>
        ) : null}
        {friendsQuery.isError ? <span className="status-inline-error">{getErrorMessage(friendsQuery.error)}</span> : null}
      </section>

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
              <p>Record your first ARAM: Mayhem game to begin.</p>
            </div>
          </section>
        ) : null}

        {current?.has_current_baboon ? (
          <section className="baboon-hero">
            <div className="baboon-hero-copy">
              <p className="eyebrow">{hasCoBaboons ? "Current Co-Baboons" : "Current Baboon"}</p>
              <h2>Crowned after dealing the least champion damage.</h2>
              {current.game ? (
                <Link className="secondary-action" to={`/games/${current.game.id}`}>
                  View game
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
                      <dd>
                        <span className="champion-name">
                          <ChampionPortrait championName={baboon.champion_name} />
                          <span>{baboon.champion_name}</span>
                        </span>
                      </dd>
                    </div>
                    <div>
                      <dt>Damage</dt>
                      <dd>{formatNumber(baboon.damage_to_champions)}</dd>
                    </div>
                  </dl>
                  {current.game ? <small>Played {formatDateTime(current.game.played_at)}</small> : null}
                </article>
              ))}
            </div>
          </section>
        ) : null}
      </section>

      <section className="surface">
        <div className="section-title">
          <History size={22} aria-hidden="true" />
          <h2>Latest game</h2>
        </div>

        {latestGamesQuery.isLoading ? <DashboardState tone="info" message="Loading latest game..." /> : null}
        {latestGamesQuery.isError ? (
          <DashboardState tone="error" message={getErrorMessage(latestGamesQuery.error)} />
        ) : null}
        {latestGamesQuery.isSuccess && !latestGame ? (
          <DashboardState tone="empty" message="No games have been recorded yet." />
        ) : null}
        {latestGame ? (
          <div className="latest-match-block">
            <div className="latest-match-meta">
              <span>{formatDateTime(latestGame.played_at)}</span>
              <span>
                {latestGame.player_count} player{latestGame.player_count === 1 ? "" : "s"}
              </span>
              <span>{formatNumber(latestGame.lowest_damage_to_champions)} lowest damage</span>
            </div>
            <GameParticipantsTable participants={latestGame.participants} />
          </div>
        ) : null}
      </section>
    </div>
  );
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
