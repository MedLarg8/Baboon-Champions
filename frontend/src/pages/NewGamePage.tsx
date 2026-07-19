import { FormEvent, KeyboardEvent, ReactNode, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  Loader2,
  Plus,
  RotateCcw,
  Save,
  Search,
  Trash2,
  Users,
} from "lucide-react";
import { Link } from "react-router-dom";

import { ApiError, friendApi, gameApi } from "../api/client";
import { ChampionPortrait } from "../components/ChampionPortrait";
import { CHAMPIONS, canonicalChampionName, normalizeChampionName } from "../data/champions";
import type { ChampionName } from "../data/champions";
import type { Friend } from "../types/friend";
import type { GameDetail, GameSummary } from "../types/game";
import { formatNumber } from "../utils/format";

type ParticipantDraft = {
  championInput: string;
  damageInput: string;
  championTouched: boolean;
  damageTouched: boolean;
};

type DamageParseResult =
  | { ok: true; value: number }
  | { ok: false; message: string };

const emptyDraft: ParticipantDraft = {
  championInput: "",
  damageInput: "",
  championTouched: false,
  damageTouched: false,
};

export function NewGamePage() {
  const queryClient = useQueryClient();
  const championRefs = useRef<Record<number, HTMLInputElement | null>>({});
  const damageRefs = useRef<Record<number, HTMLInputElement | null>>({});
  const [playedAt, setPlayedAt] = useState(() => toLocalDateTimeInput(new Date()));
  const [selectedFriendIds, setSelectedFriendIds] = useState<number[]>([]);
  const [drafts, setDrafts] = useState<Record<number, ParticipantDraft>>({});
  const [openChampionFriendId, setOpenChampionFriendId] = useState<number | null>(null);
  const [lastCreatedGame, setLastCreatedGame] = useState<GameDetail | null>(null);
  const [lastRosterIds, setLastRosterIds] = useState<number[]>([]);

  const friendsQuery = useQuery({
    queryKey: ["friends"],
    queryFn: friendApi.listFriends,
  });
  const recentGamesQuery = useQuery({
    queryKey: ["games", { limit: 20, offset: 0 }],
    queryFn: () => gameApi.listGames({ limit: 20, offset: 0 }),
  });

  const friends = friendsQuery.data ?? [];
  const friendsById = useMemo(() => new Map(friends.map((friend) => [friend.id, friend])), [friends]);
  const selectedFriends = selectedFriendIds
    .map((friendId) => friendsById.get(friendId))
    .filter((friend): friend is Friend => Boolean(friend));
  const latestRosterIds = useMemo(
    () => getLatestRosterIds(recentGamesQuery.data?.items ?? [], friendsById),
    [recentGamesQuery.data?.items, friendsById],
  );
  const recentChampionsByFriendId = useMemo(
    () => getRecentChampionsByFriendId(recentGamesQuery.data?.items ?? []),
    [recentGamesQuery.data?.items],
  );
  const validation = useMemo(
    () => validateForm({
      playedAt,
      selectedFriends,
      drafts,
    }),
    [drafts, playedAt, selectedFriends],
  );

  const createGameMutation = useMutation({
    mutationFn: gameApi.createGame,
    onSuccess: (game, variables) => {
      setLastCreatedGame(game);
      setLastRosterIds(variables.participants.map((participant) => participant.friend_id));
      setSelectedFriendIds([]);
      setDrafts({});
      setPlayedAt(toLocalDateTimeInput(new Date()));
      void queryClient.invalidateQueries({ queryKey: ["games"] });
      void queryClient.invalidateQueries({ queryKey: ["currentBaboon"] });
    },
  });

  function updateDraft(friendId: number, patch: Partial<ParticipantDraft>) {
    setDrafts((current) => ({
      ...current,
      [friendId]: {
        ...(current[friendId] ?? emptyDraft),
        ...patch,
      },
    }));
  }

  function toggleFriend(friend: Friend) {
    setLastCreatedGame(null);
    setSelectedFriendIds((current) => {
      if (current.includes(friend.id)) {
        return current.filter((friendId) => friendId !== friend.id);
      }
      return [...current, friend.id];
    });
    setDrafts((current) => {
      if (selectedFriendIds.includes(friend.id)) {
        const next = { ...current };
        delete next[friend.id];
        return next;
      }
      return {
        ...current,
        [friend.id]: current[friend.id] ?? { ...emptyDraft },
      };
    });
  }

  function selectRoster(friendIds: number[]) {
    const uniqueFriendIds = Array.from(new Set(friendIds)).filter((friendId) => friendsById.has(friendId));
    setSelectedFriendIds(uniqueFriendIds);
    setDrafts((current) => {
      const next: Record<number, ParticipantDraft> = {};
      for (const friendId of uniqueFriendIds) {
        next[friendId] = current[friendId] ?? { ...emptyDraft };
      }
      return next;
    });
    setLastCreatedGame(null);
    focusFirstChampion(uniqueFriendIds);
  }

  function clearRoster() {
    setSelectedFriendIds([]);
    setDrafts({});
    setLastCreatedGame(null);
  }

  function recordAnother() {
    selectRoster(lastRosterIds);
    setPlayedAt(toLocalDateTimeInput(new Date()));
    setLastCreatedGame(null);
  }

  function handleSubmit(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    if (!validation.isValid || createGameMutation.isPending || openChampionFriendId !== null) {
      markAllTouched();
      return;
    }

    createGameMutation.mutate({
      played_at: new Date(playedAt).toISOString(),
      participants: selectedFriends.map((friend) => {
        const draft = drafts[friend.id] ?? emptyDraft;
        const championName = canonicalChampionName(draft.championInput);
        const damage = parseDamage(draft.damageInput);
        return {
          friend_id: friend.id,
          champion_name: championName ?? draft.championInput.trim(),
          damage_to_champions: damage.ok ? damage.value : 0,
        };
      }),
    });
  }

  function handleFormKeyDown(event: KeyboardEvent<HTMLFormElement>) {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      if (openChampionFriendId === null && validation.isValid) {
        handleSubmit();
      }
    }
  }

  function markAllTouched() {
    setDrafts((current) => {
      const next = { ...current };
      for (const friend of selectedFriends) {
        next[friend.id] = {
          ...(next[friend.id] ?? emptyDraft),
          championTouched: true,
          damageTouched: true,
        };
      }
      return next;
    });
  }

  function moveFromDamage(friendId: number) {
    const currentIndex = selectedFriendIds.indexOf(friendId);
    const nextFriendId = selectedFriendIds[currentIndex + 1];
    if (nextFriendId) {
      championRefs.current[nextFriendId]?.focus();
      return;
    }
    if (validation.isValid && openChampionFriendId === null) {
      handleSubmit();
    }
  }

  function focusFirstChampion(friendIds: number[]) {
    const firstFriendId = friendIds[0];
    if (!firstFriendId) {
      return;
    }
    window.setTimeout(() => championRefs.current[firstFriendId]?.focus(), 0);
  }

  const saveDisabled = !validation.isValid || createGameMutation.isPending || openChampionFriendId !== null;

  return (
    <div className="page new-game-page">
      <section className="page-heading compact-heading">
        <p className="eyebrow">Manual entry</p>
        <h1>Record ARAM: Mayhem Game</h1>
      </section>

      {lastCreatedGame ? (
        <section className="status-message success result-message">
          <CheckCircle2 size={20} aria-hidden="true" />
          <div>
            <strong>{resultMessage(lastCreatedGame)}</strong>
            <div className="result-actions">
              <Link className="secondary-action" to={`/games/${lastCreatedGame.id}`}>
                View game
              </Link>
              <button className="icon-text-button" type="button" onClick={recordAnother}>
                <RotateCcw size={18} aria-hidden="true" />
                <span>Record another</span>
              </button>
            </div>
          </div>
        </section>
      ) : null}

      <form className="surface manual-game-form" onSubmit={handleSubmit} onKeyDown={handleFormKeyDown}>
        <div className="manual-game-toolbar">
          <label className="played-at-field">
            <span>
              <Clock3 size={16} aria-hidden="true" />
              Played
            </span>
            <input
              type="datetime-local"
              value={playedAt}
              onChange={(event) => setPlayedAt(event.target.value)}
            />
          </label>

          <div className="compact-actions">
            <button
              className="icon-text-button"
              type="button"
              onClick={() => selectRoster(latestRosterIds)}
              disabled={latestRosterIds.length < 2}
            >
              <RotateCcw size={18} aria-hidden="true" />
              <span>Use previous players</span>
            </button>
            <button
              className="icon-text-button"
              type="button"
              onClick={() => selectRoster(friends.map((friend) => friend.id))}
              disabled={friends.length === 0}
            >
              <Users size={18} aria-hidden="true" />
              <span>Select all</span>
            </button>
            <button
              className="icon-text-button"
              type="button"
              onClick={clearRoster}
              disabled={selectedFriendIds.length === 0}
            >
              <Trash2 size={18} aria-hidden="true" />
              <span>Clear</span>
            </button>
          </div>
        </div>

        <section className="player-picker" aria-labelledby="player-picker-heading">
          <div className="section-title">
            <Users size={22} aria-hidden="true" />
            <h2 id="player-picker-heading">Players</h2>
          </div>

          {friendsQuery.isLoading ? <InlineState tone="info" message="Loading friends..." /> : null}
          {friendsQuery.isError ? <InlineState tone="error" message={getErrorMessage(friendsQuery.error)} /> : null}
          {friendsQuery.isSuccess && friends.length === 0 ? (
            <InlineState
              tone="empty"
              message="No friends are registered yet."
              action={<Link to="/friends">Add friends</Link>}
            />
          ) : null}

          {friends.length > 0 ? (
            <div className="friend-chip-grid">
              {friends.map((friend) => {
                const selected = selectedFriendIds.includes(friend.id);
                return (
                  <button
                    className={selected ? "friend-chip selected" : "friend-chip"}
                    type="button"
                    key={friend.id}
                    onClick={() => toggleFriend(friend)}
                    aria-pressed={selected}
                  >
                    {selected ? <CheckCircle2 size={16} aria-hidden="true" /> : <Plus size={16} aria-hidden="true" />}
                    <span>{friend.display_name}</span>
                  </button>
                );
              })}
            </div>
          ) : null}
        </section>

        <section className="selected-player-section">
          <div className="section-title">
            <Users size={22} aria-hidden="true" />
            <h2>Selected players</h2>
          </div>

          {selectedFriends.length === 0 ? (
            <InlineState tone="empty" message="Select at least two players to start entering results." />
          ) : (
            <div className="participant-entry-list">
              {selectedFriends.map((friend) => {
                const draft = drafts[friend.id] ?? emptyDraft;
                const rowErrors = validation.rowErrors[friend.id] ?? {};
                const recentChampions = recentChampionsByFriendId.get(friend.id) ?? [];
                const blockedChampionNames = selectedFriends
                  .filter((selectedFriend) => selectedFriend.id !== friend.id)
                  .map((selectedFriend) => canonicalChampionName(drafts[selectedFriend.id]?.championInput ?? ""))
                  .filter((championName): championName is ChampionName => championName !== null);
                return (
                  <div className="participant-entry-row" key={friend.id}>
                    <div className="participant-name">
                      <strong>{friend.display_name}</strong>
                      <small>
                        {selectedFriendIds.indexOf(friend.id) + 1} of {selectedFriendIds.length}
                      </small>
                    </div>

                    <ChampionCombobox
                      value={draft.championInput}
                      recentChampions={recentChampions}
                      blockedChampionNames={blockedChampionNames}
                      disabled={createGameMutation.isPending}
                      inputRef={(element) => {
                        championRefs.current[friend.id] = element;
                      }}
                      onOpenChange={(open) => setOpenChampionFriendId(open ? friend.id : null)}
                      onChange={(value) =>
                        updateDraft(friend.id, {
                          championInput: value,
                          championTouched: true,
                        })
                      }
                      onSelect={(value) => {
                        updateDraft(friend.id, {
                          championInput: value,
                          championTouched: true,
                        });
                        window.setTimeout(() => damageRefs.current[friend.id]?.focus(), 0);
                      }}
                    />

                    <div className="damage-field">
                      <input
                        ref={(element) => {
                          damageRefs.current[friend.id] = element;
                        }}
                        value={draft.damageInput}
                        inputMode="numeric"
                        placeholder="12,345"
                        disabled={createGameMutation.isPending}
                        onFocus={(event) => event.currentTarget.select()}
                        onChange={(event) =>
                          updateDraft(friend.id, {
                            damageInput: event.target.value,
                            damageTouched: true,
                          })
                        }
                        onBlur={() =>
                          updateDraft(friend.id, {
                            damageInput: formatDamageForDisplay(draft.damageInput),
                            damageTouched: true,
                          })
                        }
                        onKeyDown={(event) => {
                          if (event.key === "Enter" && !event.ctrlKey && !event.metaKey) {
                            event.preventDefault();
                            moveFromDamage(friend.id);
                          }
                        }}
                        aria-label={`${friend.display_name} damage`}
                      />
                      {draft.damageTouched && rowErrors.damage ? <small>{rowErrors.damage}</small> : null}
                    </div>

                    <button
                      className="icon-button danger"
                      type="button"
                      aria-label={`Remove ${friend.display_name}`}
                      title={`Remove ${friend.display_name}`}
                      onClick={() => toggleFriend(friend)}
                    >
                      <Trash2 size={18} aria-hidden="true" />
                    </button>

                    {draft.championTouched && rowErrors.champion ? (
                      <p className="row-error">{rowErrors.champion}</p>
                    ) : null}
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {validation.formError ? <StatusMessage tone="error" message={validation.formError} /> : null}
        {createGameMutation.isError ? (
          <StatusMessage tone="error" message={getErrorMessage(createGameMutation.error)} />
        ) : null}

        <button className="submit-button save-game-button" type="submit" disabled={saveDisabled}>
          {createGameMutation.isPending ? (
            <Loader2 className="spin" size={18} aria-hidden="true" />
          ) : (
            <Save size={18} aria-hidden="true" />
          )}
          <span>{createGameMutation.isPending ? "Saving game..." : "Save game"}</span>
        </button>
      </form>
    </div>
  );
}

function ChampionCombobox({
  value,
  recentChampions,
  blockedChampionNames,
  disabled,
  inputRef,
  onChange,
  onSelect,
  onOpenChange,
}: {
  value: string;
  recentChampions: string[];
  blockedChampionNames: string[];
  disabled: boolean;
  inputRef: (element: HTMLInputElement | null) => void;
  onChange: (value: string) => void;
  onSelect: (value: string) => void;
  onOpenChange: (open: boolean) => void;
}) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const selectedChampion = canonicalChampionName(value);
  const options = useMemo(
    () => getChampionOptions(value, recentChampions, blockedChampionNames),
    [blockedChampionNames, recentChampions, value],
  );

  function setDropdownOpen(nextOpen: boolean) {
    setOpen(nextOpen);
    onOpenChange(nextOpen);
  }

  function selectChampion(champion: string) {
    onSelect(champion);
    setActiveIndex(0);
    setDropdownOpen(false);
  }

  return (
    <div className="champion-combobox">
      <div className="combobox-input-wrap">
        {selectedChampion ? (
          <ChampionPortrait championName={selectedChampion} />
        ) : (
          <Search size={16} aria-hidden="true" />
        )}
        <input
          ref={inputRef}
          value={value}
          placeholder="Champion"
          autoComplete="off"
          disabled={disabled}
          role="combobox"
          aria-expanded={open}
          onFocus={() => setDropdownOpen(true)}
          onChange={(event) => {
            onChange(event.target.value);
            setActiveIndex(0);
            setDropdownOpen(true);
          }}
          onBlur={() => {
            window.setTimeout(() => setDropdownOpen(false), 120);
            const champion = canonicalChampionName(value);
            if (champion) {
              onChange(champion);
            }
          }}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown") {
              event.preventDefault();
              setDropdownOpen(true);
              setActiveIndex((current) => Math.min(options.length - 1, current + 1));
            }
            if (event.key === "ArrowUp") {
              event.preventDefault();
              setDropdownOpen(true);
              setActiveIndex((current) => Math.max(0, current - 1));
            }
            if (event.key === "Enter" && open && options.length > 0) {
              event.preventDefault();
              selectChampion(options[activeIndex] ?? options[0]);
            }
            if (event.key === "Escape") {
              setDropdownOpen(false);
            }
          }}
        />
      </div>
      {open && options.length > 0 ? (
        <div className="champion-options" role="listbox">
          {options.map((champion, index) => (
            <button
              className={index === activeIndex ? "champion-option active" : "champion-option"}
              type="button"
              key={champion}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => selectChampion(champion)}
              role="option"
              aria-selected={index === activeIndex}
            >
              <ChampionPortrait championName={champion} />
              <span>{champion}</span>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function validateForm({
  playedAt,
  selectedFriends,
  drafts,
}: {
  playedAt: string;
  selectedFriends: Friend[];
  drafts: Record<number, ParticipantDraft>;
}) {
  const rowErrors: Record<number, { champion?: string; damage?: string }> = {};
  let rowErrorCount = 0;
  const championCounts = new Map<string, number>();

  for (const friend of selectedFriends) {
    const championName = canonicalChampionName(drafts[friend.id]?.championInput ?? "");
    if (championName) {
      const normalizedChampionName = normalizeChampionName(championName);
      championCounts.set(normalizedChampionName, (championCounts.get(normalizedChampionName) ?? 0) + 1);
    }
  }

  for (const friend of selectedFriends) {
    const draft = drafts[friend.id] ?? emptyDraft;
    const championName = canonicalChampionName(draft.championInput);
    const damage = parseDamage(draft.damageInput);
    rowErrors[friend.id] = {};

    if (!championName) {
      rowErrors[friend.id].champion = draft.championInput.trim()
        ? "Pick a champion from the list."
        : "Champion required.";
      rowErrorCount += 1;
    } else if ((championCounts.get(normalizeChampionName(championName)) ?? 0) > 1) {
      rowErrors[friend.id].champion = "Champion already picked.";
      rowErrorCount += 1;
    }
    if (!damage.ok) {
      rowErrors[friend.id].damage = damage.message;
      rowErrorCount += 1;
    }
  }

  let formError: string | null = null;
  if (!playedAt || Number.isNaN(new Date(playedAt).getTime())) {
    formError = "Played date is required.";
  } else if (selectedFriends.length < 2) {
    formError = "Select at least two players.";
  }

  return {
    rowErrors,
    formError,
    isValid: !formError && rowErrorCount === 0,
  };
}

function getChampionOptions(query: string, recentChampions: string[], blockedChampionNames: string[]): string[] {
  const normalizedQuery = query.trim().toLowerCase();
  const blocked = new Set(blockedChampionNames.map(normalizeChampionName));
  const recent = recentChampions.filter((champion) =>
    champion.toLowerCase().includes(normalizedQuery) && !blocked.has(normalizeChampionName(champion)),
  );
  const remaining = CHAMPIONS.filter(
    (champion) =>
      champion.toLowerCase().includes(normalizedQuery) &&
      !blocked.has(normalizeChampionName(champion)) &&
      !recent.some((recentChampion) => recentChampion.toLowerCase() === champion.toLowerCase()),
  );
  return [...recent, ...remaining].slice(0, 8);
}

function parseDamage(value: string): DamageParseResult {
  const trimmedValue = value.trim();
  if (!trimmedValue) {
    return { ok: false, message: "Damage required." };
  }

  const normalizedValue = trimmedValue.replace(/[,\s]/g, "");
  if (!/^\d+$/.test(normalizedValue)) {
    return { ok: false, message: "Use a whole number." };
  }

  const damage = Number(normalizedValue);
  if (!Number.isSafeInteger(damage)) {
    return { ok: false, message: "Damage is too large." };
  }

  return { ok: true, value: damage };
}

function formatDamageForDisplay(value: string): string {
  const damage = parseDamage(value);
  return damage.ok ? formatNumber(damage.value) : value;
}

function toLocalDateTimeInput(value: Date): string {
  const offsetMs = value.getTimezoneOffset() * 60 * 1000;
  return new Date(value.getTime() - offsetMs).toISOString().slice(0, 16);
}

function getLatestRosterIds(games: GameSummary[], friendsById: Map<number, Friend>): number[] {
  const latestGame = games[0];
  if (!latestGame) {
    return [];
  }
  const rosterIds = latestGame.participants
    .map((participant) => participant.friend_id)
    .filter((friendId): friendId is number => typeof friendId === "number" && friendsById.has(friendId));
  return Array.from(new Set(rosterIds));
}

function getRecentChampionsByFriendId(games: GameSummary[]): Map<number, string[]> {
  const championsByFriendId = new Map<number, string[]>();
  for (const game of games) {
    for (const participant of game.participants) {
      if (participant.friend_id === null) {
        continue;
      }
      const champions = championsByFriendId.get(participant.friend_id) ?? [];
      if (!champions.includes(participant.champion_name)) {
        champions.push(participant.champion_name);
      }
      championsByFriendId.set(participant.friend_id, champions.slice(0, 4));
    }
  }
  return championsByFriendId;
}

function resultMessage(game: GameDetail): string {
  const names = joinNames(game.baboons.map((baboon) => baboon.display_name));
  const damage = formatNumber(game.lowest_damage_to_champions);
  if (game.baboons.length > 1) {
    return `${names} are the new Co-Baboons with ${damage} damage.`;
  }
  return `${names} is the new Baboon with ${damage} damage.`;
}

function joinNames(names: string[]): string {
  if (names.length <= 1) {
    return names[0] ?? "";
  }
  if (names.length === 2) {
    return `${names[0]} and ${names[1]}`;
  }
  return `${names.slice(0, -1).join(", ")}, and ${names[names.length - 1]}`;
}

function StatusMessage({ tone, message }: { tone: "error" | "success" | "info"; message: string }) {
  const Icon = tone === "success" ? CheckCircle2 : tone === "error" ? AlertCircle : Loader2;

  return (
    <div className={`status-message ${tone}`}>
      <Icon className={tone === "info" ? "spin" : undefined} size={18} aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}

function InlineState({
  tone,
  message,
  action,
}: {
  tone: "error" | "info" | "empty";
  message: string;
  action?: ReactNode;
}) {
  const Icon = tone === "error" ? AlertCircle : Users;

  return (
    <div className={`inline-state ${tone}`}>
      <Icon className={tone === "info" ? "spin" : undefined} size={20} aria-hidden="true" />
      <span>{message}</span>
      {action}
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
