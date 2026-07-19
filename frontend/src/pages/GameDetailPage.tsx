import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CalendarClock, Loader2, Trash2, Users } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ApiError, gameApi } from "../api/client";
import { ChampionPortrait } from "../components/ChampionPortrait";
import { GameParticipantsTable } from "../components/GameParticipantsTable";
import { formatDateTime, formatNumber } from "../utils/format";

export function GameDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const gameId = Number(id);
  const gameQuery = useQuery({
    queryKey: ["games", gameId],
    queryFn: () => gameApi.getGame(gameId),
    enabled: Number.isInteger(gameId) && gameId > 0,
  });
  const deleteMutation = useMutation({
    mutationFn: gameApi.deleteGame,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["games"] });
      void queryClient.invalidateQueries({ queryKey: ["currentBaboon"] });
      navigate("/games");
    },
  });

  function handleDelete() {
    if (!Number.isInteger(gameId) || gameId <= 0 || deleteMutation.isPending) {
      return;
    }
    const confirmed = window.confirm("Delete this recorded game?");
    if (!confirmed) {
      return;
    }
    deleteMutation.mutate(gameId);
  }

  if (!Number.isInteger(gameId) || gameId <= 0) {
    return (
      <div className="page">
        <PageState tone="error" message="Game not found." />
      </div>
    );
  }

  return (
    <div className="page match-detail-page">
      <Link className="back-link" to="/games">
        <ArrowLeft size={18} aria-hidden="true" />
        <span>Game history</span>
      </Link>

      {gameQuery.isLoading ? <PageState tone="info" message="Loading game..." /> : null}
      {gameQuery.isError ? <PageState tone="error" message={getErrorMessage(gameQuery.error)} /> : null}
      {deleteMutation.isError ? <PageState tone="error" message={getErrorMessage(deleteMutation.error)} /> : null}

      {gameQuery.data ? (
        <>
          <section className="surface match-detail-header">
            <div>
              <p className="eyebrow">{gameQuery.data.baboons.length > 1 ? "Co-Baboons" : "Baboon"}</p>
              <h1>{gameQuery.data.baboons.map((baboon) => baboon.display_name).join(", ")}</h1>
            </div>
            <dl className="detail-metrics">
              <div>
                <dt>
                  <CalendarClock size={16} aria-hidden="true" />
                  Played
                </dt>
                <dd>{formatDateTime(gameQuery.data.played_at)}</dd>
              </div>
              <div>
                <dt>
                  <Users size={16} aria-hidden="true" />
                  Players
                </dt>
                <dd>{gameQuery.data.player_count}</dd>
              </div>
              <div>
                <dt>Lowest damage</dt>
                <dd>{formatNumber(gameQuery.data.lowest_damage_to_champions)}</dd>
              </div>
              <div>
                <dt>Champion</dt>
                <dd className="champion-list">
                  {gameQuery.data.baboons.map((baboon) => (
                    <span className="champion-name" key={`${baboon.id}-${baboon.champion_name}`}>
                      <ChampionPortrait championName={baboon.champion_name} />
                      <span>{baboon.champion_name}</span>
                    </span>
                  ))}
                </dd>
              </div>
            </dl>
          </section>

          <section className="surface">
            <div className="section-title section-title-with-action">
              <div>
                <Users size={22} aria-hidden="true" />
                <h2>Participants</h2>
              </div>
              <button
                className="icon-button danger"
                type="button"
                aria-label="Delete game"
                title="Delete game"
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending ? (
                  <Loader2 className="spin" size={18} aria-hidden="true" />
                ) : (
                  <Trash2 size={18} aria-hidden="true" />
                )}
              </button>
            </div>
            <GameParticipantsTable participants={gameQuery.data.participants} />
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
