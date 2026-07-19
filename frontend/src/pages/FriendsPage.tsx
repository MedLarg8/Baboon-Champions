import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, Loader2, Plus, Trash2, UserPlus, Users } from "lucide-react";

import { ApiError, friendApi } from "../api/client";
import type { Friend } from "../types/friend";
import { formatDate } from "../utils/format";

type FormState = {
  display_name: string;
  riot_id: string;
};

const initialFormState: FormState = {
  display_name: "",
  riot_id: "",
};

export function FriendsPage() {
  const queryClient = useQueryClient();
  const [formState, setFormState] = useState<FormState>(initialFormState);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [deletingFriendId, setDeletingFriendId] = useState<number | null>(null);

  const friendsQuery = useQuery({
    queryKey: ["friends"],
    queryFn: friendApi.listFriends,
  });

  const createFriendMutation = useMutation({
    mutationFn: friendApi.createFriend,
    onSuccess: (friend) => {
      setFormState(initialFormState);
      setFormError(null);
      setSuccessMessage(`${friend.display_name} registered as ${friend.game_name}#${friend.tag_line}.`);
      void queryClient.invalidateQueries({ queryKey: ["friends"] });
    },
    onError: (error: unknown) => {
      setSuccessMessage(null);
      setFormError(getErrorMessage(error));
    },
  });

  const deleteFriendMutation = useMutation({
    mutationFn: friendApi.deleteFriend,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["friends"] });
    },
    onSettled: () => {
      setDeletingFriendId(null);
    },
  });

  const validationError = useMemo(() => {
    if (!formState.display_name.trim()) {
      return "Friendly display name is required.";
    }
    const parsedRiotId = parseRiotId(formState.riot_id);
    if (!parsedRiotId.ok) {
      return parsedRiotId.message;
    }
    return null;
  }, [formState]);

  function updateField(field: keyof FormState, value: string) {
    setFormState((current) => ({ ...current, [field]: value }));
    setFormError(null);
    setSuccessMessage(null);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsedRiotId = parseRiotId(formState.riot_id);

    if (!formState.display_name.trim()) {
      setFormError("Friendly display name is required.");
      return;
    }
    if (!parsedRiotId.ok) {
      setFormError(parsedRiotId.message);
      return;
    }

    const payload = {
      display_name: formState.display_name.trim(),
      game_name: parsedRiotId.gameName,
      tag_line: parsedRiotId.tagLine,
    };

    if (validationError) {
      setFormError(validationError);
      return;
    }

    createFriendMutation.mutate(payload);
  }

  function handleDelete(friend: Friend) {
    const confirmed = window.confirm(`Remove ${friend.display_name} from the friend roster?`);
    if (!confirmed) {
      return;
    }

    setDeletingFriendId(friend.id);
    deleteFriendMutation.mutate(friend.id);
  }

  const submitDisabled = createFriendMutation.isPending;

  return (
    <div className="page friends-page">
      <section className="page-heading">
        <p className="eyebrow">Friend registration</p>
        <h1>Register the squad before the shame begins.</h1>
      </section>

      <div className="friends-layout">
        <section className="surface form-surface" aria-labelledby="registration-heading">
          <div className="section-title">
            <UserPlus size={22} aria-hidden="true" />
            <h2 id="registration-heading">Add a friend</h2>
          </div>

          <form className="friend-form" onSubmit={handleSubmit}>
            <label>
              <span>Friendly display name</span>
              <input
                value={formState.display_name}
                onChange={(event) => updateField("display_name", event.target.value)}
                placeholder="Mohamed"
                autoComplete="off"
                disabled={submitDisabled}
              />
            </label>

            <label>
              <span>Riot ID</span>
              <input
                value={formState.riot_id}
                onChange={(event) => updateField("riot_id", event.target.value)}
                placeholder="GameName#TagLine"
                autoComplete="off"
                disabled={submitDisabled}
              />
            </label>

            {formError ? (
              <StatusMessage tone="error" message={formError} />
            ) : null}
            {successMessage ? (
              <StatusMessage tone="success" message={successMessage} />
            ) : null}
            {createFriendMutation.isPending ? (
              <StatusMessage tone="info" message="Checking Riot account..." />
            ) : null}

            <button className="submit-button" type="submit" disabled={submitDisabled}>
              {createFriendMutation.isPending ? (
                <Loader2 className="spin" size={18} aria-hidden="true" />
              ) : (
                <Plus size={18} aria-hidden="true" />
              )}
              <span>{createFriendMutation.isPending ? "Checking" : "Register friend"}</span>
            </button>
          </form>
        </section>

        <section className="surface list-surface" aria-labelledby="friends-heading">
          <div className="section-title">
            <Users size={22} aria-hidden="true" />
            <h2 id="friends-heading">Registered friends</h2>
          </div>

          {friendsQuery.isLoading ? <ListState tone="info" message="Loading friends..." /> : null}
          {friendsQuery.isError ? (
            <ListState tone="error" message={getErrorMessage(friendsQuery.error)} />
          ) : null}
          {deleteFriendMutation.isError ? (
            <ListState tone="error" message={getErrorMessage(deleteFriendMutation.error)} />
          ) : null}
          {friendsQuery.isSuccess && friendsQuery.data.length === 0 ? (
            <ListState
              tone="empty"
              message="No accounts have been registered yet. Add the Riot IDs of the friends who should be included in the Baboon competition."
            />
          ) : null}

          {friendsQuery.isSuccess && friendsQuery.data.length > 0 ? (
            <ul className="friend-list">
              {friendsQuery.data.map((friend) => (
                <li className="friend-card" key={friend.id}>
                  <div className="friend-main">
                    <strong>{friend.display_name}</strong>
                    <span>{friend.game_name}#{friend.tag_line}</span>
                    <small>Registered {formatDate(friend.created_at)}</small>
                  </div>
                  <button
                    className="icon-button danger"
                    type="button"
                    aria-label={`Delete ${friend.display_name}`}
                    title={`Delete ${friend.display_name}`}
                    onClick={() => handleDelete(friend)}
                    disabled={deleteFriendMutation.isPending && deletingFriendId === friend.id}
                  >
                    {deleteFriendMutation.isPending && deletingFriendId === friend.id ? (
                      <Loader2 className="spin" size={18} aria-hidden="true" />
                    ) : (
                      <Trash2 size={18} aria-hidden="true" />
                    )}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      </div>
    </div>
  );
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

function ListState({ tone, message }: { tone: "error" | "info" | "empty"; message: string }) {
  const Icon = tone === "error" ? AlertCircle : Users;

  return (
    <div className={`list-state ${tone}`}>
      <Icon size={24} aria-hidden="true" />
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

type ParsedRiotId =
  | { ok: true; gameName: string; tagLine: string }
  | { ok: false; message: string };

function parseRiotId(value: string): ParsedRiotId {
  const trimmedValue = value.trim();
  if (!trimmedValue) {
    return { ok: false, message: "Riot ID is required." };
  }

  const separatorIndex = trimmedValue.lastIndexOf("#");
  if (separatorIndex === -1) {
    return { ok: false, message: "Riot ID must include #, like GameName#TagLine." };
  }

  const gameName = trimmedValue.slice(0, separatorIndex).trim();
  const tagLine = trimmedValue.slice(separatorIndex + 1).trim();

  if (!gameName) {
    return { ok: false, message: "Riot ID must include a game name before #." };
  }
  if (!tagLine) {
    return { ok: false, message: "Riot ID must include a tag line after #." };
  }

  return { ok: true, gameName, tagLine };
}
