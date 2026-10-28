# Doubt Desk (Vite + React)

## Setup
    npm install
    npm run dev        # http://localhost:5173

Requires Node 18+. Vite proxies `/api/*` to `http://127.0.0.1:8000`, so no CORS setup is needed.
To call the backend directly instead, create `.env` with `VITE_API_URL=http://127.0.0.1:8000` and enable CORS on FastAPI.

## Use
1. Instructor tab → "Add a video" (or type an existing Video ID and URL at the top).
2. Instructor tab → paste chapters JSON → Import.
3. Learn tab → watch, click "Ask a doubt at mm:ss", send. Answers stream with cache badges and cost footer.
