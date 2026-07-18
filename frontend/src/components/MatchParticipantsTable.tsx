import type { MatchParticipant } from "../types/match";
import { formatKda, formatNumber } from "../utils/format";

type Props = {
  participants: MatchParticipant[];
};

export function MatchParticipantsTable({ participants }: Props) {
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
            <th className="numeric">K / D / A</th>
            <th>Result</th>
            <th>Verdict</th>
          </tr>
        </thead>
        <tbody>
          {sortedParticipants.map((participant) => (
            <tr className={participant.is_baboon ? "baboon-row" : undefined} key={participant.id}>
              <td data-label="Player">
                <strong>{participant.display_name}</strong>
              </td>
              <td data-label="Champion">{participant.champion_name ?? "Unknown"}</td>
              <td className="numeric" data-label="Damage">
                {formatNumber(participant.damage_to_champions)}
              </td>
              <td className="numeric" data-label="K / D / A">
                {formatKda(participant.kills, participant.deaths, participant.assists)}
              </td>
              <td data-label="Result">
                <span className={participant.win ? "result-badge win" : "result-badge loss"}>
                  {participant.win ? "Win" : "Loss"}
                </span>
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
