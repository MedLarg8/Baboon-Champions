import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, Loader2, Plus, Trash2, UserPlus, Users } from "lucide-react";

import { ApiError, friendApi } from "../api/client";
import type { CreateFriendRequest, Friend } from "../types/friend";

type FormState = CreateFriendRequest;

const initialFormState: FormState = {
  display_name: "",
  game_name: "",
  tag_line: "",
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
    if (!formState.game_name.trim()) {
      return "Riot game name is required.";
    }
    if (!formState.tag_line.trim()) {
      return "Riot tag line is required.";
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
    const trimmedPayload = {
      display_name: formState.display_name.trim(),
      game_name: formState.game_name.trim(),
      tag_line: formState.tag_line.trim(),
    };

    if (validationError) {
      setFormError(validationError);
      return;
    }

    createFriendMutation.mutate(trimmedPayload);
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

            <div className="riot-id-row">
              <label>
                <span>Riot game name</span>
                <input
                  value={formState.game_name}
                  onChange={(event) => updateField("game_name", event.target.value)}
                  placeholder="Windshitter"
                  autoComplete="off"
                  disabled={submitDisabled}
                />
              </label>
              <span className="riot-separator" aria-hidden="true">
                #
              </span>
              <label>
                <span>Tag line</span>
                <input
                  value={formState.tag_line}
                  onChange={(event) => updateField("tag_line", event.target.value)}
                  placeholder="EUW"
                  autoComplete="off"
                  disabled={submitDisabled}
                />
              </label>
            </div>

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
            <ListState tone="empty" message="No friends registered yet." />
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

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}
