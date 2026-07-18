import { Crown, History, ShieldAlert } from "lucide-react";
import { Link } from "react-router-dom";

export function DashboardPage() {
  return (
    <div className="page dashboard-page">
      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">Batch 1 foundation</p>
          <h1>The Baboon crown is warming up.</h1>
          <p>
            Friend registration is ready now. Current Baboon, match imports, streaks,
            and the Hall of Shame are intentionally waiting for later batches.
          </p>
          <Link className="primary-action" to="/friends">
            Register friends
          </Link>
        </div>
        <div className="crown-stage" aria-hidden="true">
          <Crown size={96} strokeWidth={1.35} />
        </div>
      </section>

      <section className="future-grid" aria-label="Upcoming areas">
        <article className="future-item">
          <ShieldAlert size={24} aria-hidden="true" />
          <div>
            <h2>Current Baboon</h2>
            <p>Reserved for the lowest-damage friend after match retrieval exists.</p>
          </div>
        </article>
        <article className="future-item">
          <History size={24} aria-hidden="true" />
          <div>
            <h2>Match History</h2>
            <p>Reserved for verified ARAM: Mayhem matches from Riot APIs.</p>
          </div>
        </article>
      </section>
    </div>
  );
}
