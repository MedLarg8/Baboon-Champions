# ARAM Baboon Tracker

A personal web application for a friend group that plays League of Legends ARAM: Mayhem together. It registers friends by Riot ID, lets you manually record a game, and crowns the selected friend or friends with the lowest champion damage as the Baboon.

## Features

- Riot Account-V1 friend registration from the `/friends` page.
- Fast manual game entry from `/games/new`.
- One-click player selection from registered friends.
- Local searchable champion catalog with no runtime Riot request.
- Damage entry that accepts plain, comma-formatted, or space-formatted whole numbers.
- Backend-calculated Baboon and Co-Baboon results.
- Saved game history, detail pages, and current Baboon dashboard.
- Historical participant snapshots preserved after friend deletion.
- Local React/Vite frontend and FastAPI backend.

## Manual Game Flow

Use **Record a game** to:

1. Pick the played date, which defaults to now.
2. Select at least two registered friends.
3. Enter each player's champion and champion damage.
4. Save the game.

The backend calculates the lowest `damage_to_champions` value and marks every tied lowest-damage participant as Baboon or Co-Baboon. The frontend never sends or persists the verdict.

## Local Development

The project is split into two apps:

- Backend: `http://127.0.0.1:8001`
- Frontend: `http://localhost:5173`

The Vite dev server proxies `/api` requests to the backend, so frontend code should keep using relative `/api/...` paths.

Start both apps:

```powershell
.\start-dev.ps1
```

Start only the backend:

```powershell
cd backend
.\run-dev.ps1
```

Start only the frontend:

```powershell
cd frontend
.\run-dev.ps1
```

## Backend Setup

Create and activate the virtual environment if needed:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `backend/.env` from `backend/.env.example` and put your Riot API key there:

```dotenv
RIOT_API_KEY=
RIOT_REGIONAL_ROUTE=europe
DATABASE_URL=sqlite:///./aram_baboon.db
FRONTEND_ORIGIN=http://localhost:5173
```

The Riot API key is used only for friend registration through Riot Account-V1. It is not sent to the frontend.

## Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

For normal local development, keep `VITE_API_BASE_URL` empty so the Vite proxy handles `/api`.

## API

Friend management:

- `GET /api/friends`
- `POST /api/friends`
- `DELETE /api/friends/{friend_id}`

Manual games:

- `POST /api/games`
- `GET /api/games?limit=20&offset=0`
- `GET /api/games/{game_id}`
- `DELETE /api/games/{game_id}`
- `GET /api/baboon/current`

Example game creation payload:

```json
{
  "played_at": "2026-07-19T21:30:00Z",
  "participants": [
    {
      "friend_id": 1,
      "champion_name": "Yone",
      "damage_to_champions": 31400
    },
    {
      "friend_id": 2,
      "champion_name": "Malphite",
      "damage_to_champions": 12300
    }
  ]
}
```

## Database

The backend uses SQLAlchemy table creation, not Alembic.

Current tables:

- `friends`
- `games`
- `game_participants`

Deleting a friend clears the live `friend_id` link from historical participants, but name snapshots remain. Deleting a game cascades to its participant rows.

## Verification

Backend tests:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Backend import check:

```powershell
cd backend
.\.venv\Scripts\python.exe -c "from app.main import app; print(app.title)"
```

Frontend production build:

```powershell
cd frontend
npm run build
```

## Current Limitations

- No automatic game import.
- No KDA, win/loss, augments, duration, or match metadata entry.
- No authentication or multiple friend groups.
- Champion portraits are not included in this batch.
