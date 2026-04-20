# Free-Tier Deployment (Render + Cloudflare Pages)

This guide deploys the app for anywhere access at $0 cost (personal use, 1-2 users):
- Backend API: Render free web service
- Frontend: Cloudflare Pages free tier
- Data and images: Supabase

## 1) Prerequisites

- GitHub repo with this project pushed
- Supabase project already configured
- Render and Cloudflare accounts

## 2) Render backend deployment

1. In Render, click **New** -> **Blueprint** (recommended, uses `render.yaml`) or **Web Service**.
2. Connect repo: `jaysevillajr-collab/cocktail-database`.
3. If using Web Service manually, set:
   - Root Directory: `web/backend`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Set environment variables:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `SUPABASE_DB_URL`
   - `SUPABASE_STORAGE_BUCKET=images`
   - `STORAGE_MODE=supabase`
   - `LOCAL_MIRROR_ENABLED=false`
   - `LOCAL_MIRROR_BEST_EFFORT=true`
5. Deploy and confirm:
   - `GET /health` returns `{"status":"ok"}`

## 3) Cloudflare Pages frontend deployment

1. In Cloudflare dashboard: **Workers & Pages** -> **Create application** -> **Pages** -> **Connect to Git**.
2. Select repo: `jaysevillajr-collab/cocktail-database`.
3. Build settings:
   - Framework preset: `Vite`
   - Root directory: `web/frontend`
   - Build command: `npm run build`
   - Build output directory: `dist`
4. In Pages project settings, add env var:
   - `VITE_API_BASE=https://<your-render-service>.onrender.com`
5. Trigger redeploy and open Pages URL.

## 4) Validation checklist

- Frontend loads without localhost API calls.
- `GET /meta/counts` returns data.
- Alcohol and cocktail lists load.
- Aperol (or any known item) image renders from Supabase storage.
- CRUD smoke passes against Render backend.

## 5) Free-tier operational notes

- Render free service may sleep; first request after idle can be slow.
- Keep service URLs (Render + Pages) bookmarked.
- For local mirror repair or local backups, use `web/backend/scripts/supabase_to_local_sync.py`.

## 6) Post-go-live security

- Rotate exposed secrets after first successful deployment:
  - `SUPABASE_SERVICE_ROLE_KEY`
  - Any AI provider keys in backend `.env`
- Update rotated keys in Render env vars and redeploy.
