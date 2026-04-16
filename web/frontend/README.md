# Cocktail Web Frontend (Phase 0)

Lightweight React + Vite shell for validating API connectivity and data parity.

## Run

```powershell
npm install
npm run dev
```

App URL: `http://127.0.0.1:5173`

## Notes
- API base URL can be configured via `VITE_API_BASE`.
- Default frontend fallback API is `http://127.0.0.1:8001`.
- Example PowerShell before `npm run dev`:
  - `$env:VITE_API_BASE = "http://127.0.0.1:8001"`
- Read-only display only in this phase.
- Built for parallel-run with the existing PyQt app.
