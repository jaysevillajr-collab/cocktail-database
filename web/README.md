# Web Migration Scaffold (Phase 0)

This folder contains the first migration scaffold for moving from PyQt to a modern web app while preserving existing SQLite data.

## Structure

- `backend/` - FastAPI read-only API over existing `cocktail_database.db`
- `frontend/` - React/Vite UI shell to validate connectivity and data parity

## Parallel-Run Safety

- Existing PyQt app remains unchanged.
- Web backend is read-only in this phase.
- No schema changes are applied.

## Quick Start

### 1) Start backend
```powershell
cd web\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2) Start frontend
```powershell
cd web\frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## Build Windows Installer (Web App)

From the project root:

```powershell
./build_web_installer.ps1
```

This will:

1. Build frontend production assets (`web/frontend/dist`)
2. Compile backend into `CocktailWebBackend.exe`
3. Package backend executable + built frontend with Inno Setup
4. Generate `Output/CocktailDatabaseWebInstaller.exe`

Installed app behavior:

- Launch shortcut runs `web/Launch Web App.cmd`
- Script starts bundled backend executable on `http://127.0.0.1:8002`
- No Python install is required on the target machine
- Backend serves the built frontend at `/`
