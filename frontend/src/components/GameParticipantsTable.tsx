import type { GameParticipant } from "../types/game";
import { formatNumber } from "../utils/format";
import { ChampionPortrait } from "./ChampionPortrait";

type Props = {
  participants: GameParticipant[];
};

export function GameParticipantsTable({ participants }: Props) {
  const sortedParticipants = [...participants].sort(
    (first, second) => second.damage_to_champions - first.damage_to_champions,
  );
  const baboonCount = sortedParticipants.filter((participant) => participant.is_baboon).length;

  return (
    <div className="result-table-wrap">
      <table className="result-table">
        <thead>
          <tr>
            <th>Player</th>
            <th>Champion</th>
            <th className="numeric">Damage</th>
            <th>Verdict</th>
          </tr>
        </thead>
        <tbody>
          {sortedParticipants.map((participant) => (
            <tr className={participant.is_baboon ? "baboon-row" : undefined} key={participant.id}>
              <td data-label="Player">
                <strong>{participant.display_name}</strong>
              </td>
              <td data-label="Champion">
                <span className="champion-name">
                  <ChampionPortrait championName={participant.champion_name} />
                  <span>{participant.champion_name}</span>
                </span>
              </td>
              <td className="numeric" data-label="Damage">
                {formatNumber(participant.damage_to_champions)}
              </td>
              <td data-label="Verdict">
                <span className={participant.is_baboon ? "verdict-badge baboon" : "verdict-badge safe"}>
                  {participant.is_baboon ? (baboonCount > 1 ? "Co-Baboon" : "Baboon") : "Safe"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
