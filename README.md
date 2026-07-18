# ARAM Baboon Tracker

A personal web application for a friend group that plays League of Legends ARAM: Mayhem together. The eventual goal is to crown the registered friend with the lowest `totalDamageDealtToChampions` as the Baboon after every tracked match.

## Current Batch 1 Capabilities

- FastAPI backend with SQLite persistence.
- Riot ID friend registration through Riot Account-V1.
- Friend listing and deletion.
- React/Vite frontend with dashboard and friend-management routes.
- Backend tests with mocked Riot responses.

The app does not retrieve matches, calculate the Baboon, show statistics, authenticate users, or scrape any website yet.

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
```

Frontend:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Riot API Key

1. Sign in at the Riot Developer Portal.
2. Generate a development API key.
3. Put the key in `backend/.env` as `RIOT_API_KEY`.
4. Restart the backend after changing the key.

The backend sends the key to Riot with the `X-Riot-Token` header. The frontend never receives or stores the key.

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

## Deferred Features

- Riot match retrieval.
- ARAM: Mayhem match filtering.
- Baboon calculation.
- Current Baboon display.
- Match history.
- Long-term statistics.
- Hall of Shame counts and streaks.
- Authentication and permissions.
- Deployment infrastructure.
