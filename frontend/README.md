# Frontend (Vite + React)

## Quick start

1. Install dependencies:
   - `npm install`
2. Optional API base override:
   - `echo 'VITE_API_BASE=http://localhost:18080' > .env`
3. Run:
   - `npm run dev`

## Start frontend + backend together

From `frontend/`, run:

- `npm run dev` (or `npm run dev:full`)

This command:

- Starts backend first (only if not already running)
- Waits for backend health at `http://127.0.0.1:18080/health`
- Starts Vite frontend dev server

If you only want frontend Vite without backend startup:

- `npm run dev:frontend`
