import type { CreateFriendRequest, Friend } from "../types/friend";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

type ApiErrorDetail = string | Array<{ msg?: string }>;

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const detail = await parseErrorDetail(response);
    throw new ApiError(detail, response.status);
  }

  return (await response.json()) as T;
}

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: ApiErrorDetail };
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    if (Array.isArray(payload.detail)) {
      return payload.detail
        .map((item) => item.msg)
        .filter(Boolean)
        .join(" ");
    }
  } catch {
    return "The backend returned an unreadable error.";
  }

  return "Something went wrong.";
}

export const friendApi = {
  listFriends: () => request<Friend[]>("/api/friends"),
  createFriend: (payload: CreateFriendRequest) =>
    request<Friend>("/api/friends", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteFriend: (friendId: number) =>
    request<{ detail: string }>(`/api/friends/${friendId}`, {
      method: "DELETE",
    }),
};
