export type MatchParticipant = {
  id: number;
  friend_id: number | null;
  display_name: string;
  game_name: string;
  tag_line: string;
  champion_id: number | null;
  champion_name: string | null;
  team_id: number;
  kills: number;
  deaths: number;
  assists: number;
  damage_to_champions: number;
  win: boolean;
  is_baboon: boolean;
};

export type MatchSummary = {
  id: number;
  riot_match_id: string;
  queue_id: number;
  game_end_time: string;
  duration_seconds: number;
  game_version: string | null;
  registered_friend_count: number;
  team_won: boolean | null;
  lowest_damage_to_champions: number | null;
  participants: MatchParticipant[];
  baboons: MatchParticipant[];
};

export type PaginatedMatches = {
  items: MatchSummary[];
  limit: number;
  offset: number;
  total: number;
};

export type MatchDetail = {
  id: number;
  riot_match_id: string;
  queue_id: number;
  game_creation: string | null;
  game_start_time: string | null;
  game_end_time: string;
  duration_seconds: number;
  game_version: string | null;
  imported_at: string;
  participants: MatchParticipant[];
  baboons: MatchParticipant[];
};

export type CurrentBaboonPlayer = {
  friend_id: number | null;
  display_name: string;
  game_name: string;
  tag_line: string;
  champion_id: number | null;
  champion_name: string | null;
  kills: number;
  deaths: number;
  assists: number;
  damage_to_champions: number;
  win: boolean;
};

export type CurrentBaboonResponse = {
  has_current_baboon: boolean;
  match: {
    id: number;
    riot_match_id: string;
    game_end_time: string;
    duration_seconds: number;
  } | null;
  baboons: CurrentBaboonPlayer[];
};

export type MatchSyncSummary = {
  status: string;
  friends_checked: number;
  candidate_match_ids: number;
  new_candidates_examined: number;
  matches_imported: number;
  matches_already_known: number;
  matches_skipped: number;
  skipped_reasons: Record<string, number>;
  imported_match_ids: string[];
  current_baboons: Array<{
    display_name: string;
    damage_to_champions: number;
  }>;
};
