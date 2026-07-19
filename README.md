# ARAM Baboon Tracker

A personal web application for a friend group that plays League of Legends ARAM: Mayhem together. It registers friends by Riot ID, imports eligible ARAM: Mayhem matches, and crowns the registered friend or friends with the lowest `totalDamageDealtToChampions` as the Baboon.

## Current Batch 2 Capabilities

- FastAPI backend with SQLite persistence.
- Riot Account-V1 friend registration by Riot ID from the `/friends` page.
- Riot Match-v5 manual match synchronization.
- ARAM: Mayhem filtering for queue `2400`.
- Baboon and Co-Baboon calculation from champion damage only.
- Persistent match history with registered friend participant snapshots.
- Current Baboon derived from the newest imported eligible match.
- React/Vite frontend with dashboard, friends, match history, and match detail routes.
- Backend tests with mocked Riot responses and isolated test databases.

## Friend Accounts

Friend accounts are managed from the `/friends` page. Add a friendly display name and a Riot ID in this format:

```text
GameName#TagLine
```

The frontend splits the Riot ID on the final `#` character, so game names with spaces are supported. The backend resolves the Riot ID through Riot Account-V1 and stores the Riot-provided PUUID plus canonical `gameName` and `tagLine` in SQLite.

Users never enter PUUIDs manually. PUUIDs are treated as internal identifiers and are not shown prominently in the interface.

Registered friends in SQLite are the source of truth for the friend group. Static backend account lists are not used.

At least two registered Riot accounts are required before shared-match synchronization can produce a Baboon result.

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

Run the backend on the standard local development port:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Using `python -m uvicorn` ensures Uvicorn is executed through the active Python environment.

You can also run without activating the virtual environment:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Or use the helper script from the repository root:

```powershell
.\backend\run-dev.ps1
```

The API runs at `http://127.0.0.1:8001`.

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

```powershell
npm run dev
```

Or use the helper script from the repository root:

```powershell
.\frontend\run-dev.ps1
```

The frontend runs at `http://localhost:5173`.

## Running Both Apps

Local development normally uses two processes:

- Vite serves the React frontend.
- FastAPI serves the backend API.
- Browser requests to `/api/...` go to Vite first, then Vite proxies them to FastAPI at `http://127.0.0.1:8001`.

Start both from the repository root:

```powershell
.\start-dev.ps1
```

Expected local addresses:

```text
Frontend: http://localhost:5173
Backend:  http://127.0.0.1:8001
Swagger:  http://127.0.0.1:8001/docs
```

Port `8001` is used because port `8000` may be unavailable or reserved on some Windows systems.

## Environment Variables

Backend:

```env
RIOT_API_KEY=
RIOT_REGIONAL_ROUTE=europe
DATABASE_URL=sqlite:///./aram_baboon.db
FRONTEND_ORIGIN=http://localhost:5173
MATCH_LOOKBACK_PER_FRIEND=10
MATCH_SYNC_CANDIDATE_LIMIT=40
MINIMUM_MATCH_DURATION_SECONDS=300
```

Frontend:

```env
# Leave empty during local development to use the Vite /api proxy.
VITE_API_BASE_URL=
```

For a separately deployed backend, set a backend origin such as `VITE_API_BASE_URL=https://api.example.com`. Do not put Riot API keys or other secrets in `VITE_` variables.

`MATCH_LOOKBACK_PER_FRIEND` controls how many recent queue `2400` IDs are requested per friend. `MATCH_SYNC_CANDIDATE_LIMIT` caps full match-detail fetches per sync so the frontend cannot trigger unbounded Riot requests.

## Riot API Key

1. Sign in at the Riot Developer Portal.
2. Generate a development API key.
3. Put the key in `backend/.env` as `RIOT_API_KEY`.
4. Restart the backend after changing the key.

The backend sends the key to Riot with the `X-Riot-Token` header. The frontend never receives or stores the key. If Riot returns `429`, the backend surfaces a rate-limit message and forwards `Retry-After` when Riot provides it.

## Match Synchronization Rules

Use **Check for new matches** on the dashboard to manually synchronize recent Riot Match-v5 history. The app requests queue `2400`, verifies the full match response is still queue `2400`, and rejects ordinary ARAM queue `450`.

Only registered friends from SQLite are compared. Participants are matched by PUUID, random players are ignored, and random players are not stored.

Eligible matches require at least two registered friends on the same team. The Baboon is the registered participant with the lowest `totalDamageDealtToChampions`. If several registered friends tie for the lowest champion damage, all tied players are Co-Baboons.

Matches shorter than `MINIMUM_MATCH_DURATION_SECONDS` are skipped. Matches where a registered participant explicitly has `gameEndedInEarlySurrender=true` are treated as remakes or early endings and skipped.

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

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Frontend build and TypeScript check:

```powershell
cd frontend
npm run build
```

Backend health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/health
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
