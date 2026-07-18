# ARAM Baboon Tracker

A personal web application for a friend group that plays League of Legends ARAM: Mayhem together. It registers friends by Riot ID, imports eligible ARAM: Mayhem matches, and crowns the registered friend or friends with the lowest `totalDamageDealtToChampions` as the Baboon.

## Current Batch 2 Capabilities

- FastAPI backend with SQLite persistence.
- Riot Account-V1 friend registration by Riot ID.
- Riot Match-v5 manual match synchronization.
- ARAM: Mayhem filtering for queue `2400`.
- Baboon and Co-Baboon calculation from champion damage only.
- Persistent match history with registered friend participant snapshots.
- Current Baboon derived from the newest imported eligible match.
- React/Vite frontend with dashboard, friends, match history, and match detail routes.
- Backend tests with mocked Riot responses and isolated test databases.

## How Synchronization Works

Synchronization is manual in this batch. Press **Check for new matches** on the dashboard to ask the backend to:

1. Load currently registered friends.
2. Request recent Match-v5 match IDs for each friend with `queue=2400`.
3. Deduplicate match IDs and skip matches already imported.
4. Apply the configured candidate limit.
5. Fetch full match details from Riot.
6. Verify `info.queueId == 2400`.
7. Keep only registered friend participants.
8. Require at least two registered friends on the same team.
9. Skip remakes, early surrenders, and matches shorter than the configured minimum duration.
10. Compare only `totalDamageDealtToChampions`.
11. Mark every tied lowest-damage friend as a Co-Baboon.
12. Store the match and registered friend results in one database transaction.

Random teammates and opponents are never persisted.

## Rules

- Eligible queue: `2400`, Riot's ARAM: Mayhem queue.
- Minimum friends: at least two registered friends must appear in the match.
- Same-team requirement: registered friends must be on one team.
- Damage metric: `totalDamageDealtToChampions`.
- Ties: all tied lowest-damage friends are Co-Baboons.
- Current Baboon: derived from the newest imported eligible match by match end time.
- Short match default exclusion: less than `300` seconds.

## Prerequisites

- Python 3.12 or newer.
- Node.js 20 or newer.
- A Riot development API key from the Riot Developer Portal.

Riot development keys expire and may need to be regenerated.

## Backend Setup

```bash
cd backend
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Unix-like shells:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Create a local environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Set `RIOT_API_KEY` in `backend/.env`. Keep this key backend-only. Never add it to the frontend or commit it.

Run the backend:

```bash
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`.

## Frontend Setup

```bash
cd frontend
npm install
```

Create a local environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Run the frontend:

```bash
npm run dev
```

The frontend runs at `http://localhost:5173`.

## Environment Variables

Backend:

```env
RIOT_API_KEY=
RIOT_REGIONAL_ROUTE=europe
DATABASE_URL=sqlite:///./aram_baboon.db
FRONTEND_ORIGIN=http://localhost:5173
MATCH_LOOKBACK_PER_FRIEND=10
MATCH_SYNC_CANDIDATE_LIMIT=30
MINIMUM_MATCH_DURATION_SECONDS=300
```

Frontend:

```env
VITE_API_BASE_URL=http://localhost:8000
```

`MATCH_LOOKBACK_PER_FRIEND` controls how many recent queue `2400` IDs are requested per friend. `MATCH_SYNC_CANDIDATE_LIMIT` caps full match-detail fetches per sync so the frontend cannot trigger unbounded Riot requests.

## Riot API Key

1. Sign in at the Riot Developer Portal.
2. Generate a development API key.
3. Put the key in `backend/.env` as `RIOT_API_KEY`.
4. Restart the backend after changing the key.

The backend sends the key to Riot with the `X-Riot-Token` header. The frontend never receives or stores the key. If Riot returns `429`, the backend surfaces a rate-limit message and forwards `Retry-After` when Riot provides it.

## Database Notes

This local app currently uses SQLAlchemy table creation, not Alembic. Batch 2 adds `matches` and `match_participants` tables. If you already created a Batch 1 development database, the new tables are created on backend startup.

If you want a clean local database while developing:

```powershell
Remove-Item backend\aram_baboon.db
```

Then restart the backend. This deletes local development data only.

Deleting a friend removes that friend from future synchronization anchors, but already imported match history remains because participant snapshots are stored.

## Tests and Checks

Backend tests:

```bash
cd backend
pytest
```

Frontend build and TypeScript check:

```bash
cd frontend
npm run build
```

Backend health check:

```bash
curl http://localhost:8000/api/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "aram-baboon-backend"
}
```

## Current Limitations

- No automatic background polling.
- No scheduled tasks or queues.
- No Hall of Shame totals.
- No Baboon streaks.
- No long-term statistics.
- No champion portraits through Data Dragon.
- No authentication or multiple friend groups.
- No live-game detection or notifications.
- No match deletion UI or manual verdict editing.
- No scraping.
- No deployment configuration.
