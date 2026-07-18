export type Friend = {
  id: number;
  display_name: string;
  game_name: string;
  tag_line: string;
  puuid: string;
  created_at: string;
  updated_at: string;
};

export type CreateFriendRequest = {
  display_name: string;
  game_name: string;
  tag_line: string;
};
