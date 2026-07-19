export type GameParticipant = {
  id: number;
  friend_id: number | null;
  display_name: string;
  game_name: string;
  tag_line: string;
  champion_name: string;
  damage_to_champions: number;
  is_baboon: boolean;
};

export type GameSummary = {
  id: number;
  played_at: string;
  created_at: string;
  updated_at: string;
  notes: string | null;
  player_count: number;
  lowest_damage_to_champions: number | null;
  participants: GameParticipant[];
  baboons: GameParticipant[];
};

export type PaginatedGames = {
  items: GameSummary[];
  limit: number;
  offset: number;
  total: number;
};

export type GameDetail = GameSummary;

export type CreateGameRequest = {
  played_at: string;
  notes?: string | null;
  participants: Array<{
    friend_id: number;
    champion_name: string;
    damage_to_champions: number;
  }>;
};

export type CurrentBaboonPlayer = {
  friend_id: number | null;
  display_name: string;
  game_name: string;
  tag_line: string;
  champion_name: string;
  damage_to_champions: number;
};

export type CurrentBaboonResponse = {
  has_current_baboon: boolean;
  game: {
    id: number;
    played_at: string;
  } | null;
  baboons: CurrentBaboonPlayer[];
};
