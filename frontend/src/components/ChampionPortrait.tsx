import { getChampionImageUrl } from "../data/champions";

type Props = {
  championName: string;
  size?: "sm" | "md";
};

export function ChampionPortrait({ championName, size = "sm" }: Props) {
  const imageUrl = getChampionImageUrl(championName);

  if (!imageUrl) {
    return <span className={`champion-avatar ${size}`} aria-hidden="true" />;
  }

  return (
    <img
      className={`champion-avatar ${size}`}
      src={imageUrl}
      alt=""
      loading="lazy"
      width={size === "md" ? 36 : 28}
      height={size === "md" ? 36 : 28}
    />
  );
}
