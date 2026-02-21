# AI Medical Triage System (Monorepo)

## Repository Structure
- `backend/`: FastAPI API (routers, schemas, services, tests)
- `frontend/`: React + Vite + TypeScript app
- `scripts/`: root helper scripts for dev/test
- `.github/workflows/ci.yml`: CI for backend and frontend

## API Endpoints
- Versioned:
  - `GET /api/v1/health`
  - `POST /api/v1/triage`
- Backward-compatible legacy paths:
  - `GET /health`
  - `POST /triage`

Legacy paths are hidden from OpenAPI docs and route to the same handlers.

## One-Time Setup

### Backend (PowerShell)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
```

### Frontend (PowerShell)
```powershell
cd frontend
npm install
Copy-Item .env.example .env
```

## Run Locally

### Option A: Root Scripts (PowerShell)
```powershell
.\scripts\dev-backend.ps1
.\scripts\dev-frontend.ps1
.\scripts\test-backend.ps1
.\scripts\test-frontend.ps1
```

### Option B: Direct Commands (PowerShell)
```powershell
cd backend
.\.venv\Scripts\activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 19001
```

```powershell
cd frontend
npm run dev
```

### Cross-Platform (bash)
```bash
bash scripts/dev-backend.sh
bash scripts/dev-frontend.sh
bash scripts/test-backend.sh
bash scripts/test-frontend.sh
```

## Tests and Lint

### Backend
```powershell
cd backend
.\.venv\Scripts\activate
pytest
ruff check app tests
black --check app tests
```

### Frontend
```powershell
cd frontend
npm run lint
npm run test
npm run build
```

## Environment Variables

### `backend/.env`
- `APP_NAME=AI Medical Triage System API`
- `API_V1_PREFIX=/api/v1`
- `LOG_LEVEL=INFO`
- `CORS_ORIGINS=http://localhost:5173,http://localhost:3000`
- `RAG_DATA_DIR=./data`
- `RAG_RETRIEVER=stub` (`stub`, `tfidf`, `embedding`)
- `RAG_TOP_K=3`
- `TFIDF_MAX_FEATURES=1000`
- `TFIDF_NGRAM_MIN=1`
- `TFIDF_NGRAM_MAX=2`

### `frontend/.env`
- `VITE_API_BASE_URL=http://localhost:19001`

## Troubleshooting
- Port conflict on backend:
  - update backend port in run command and set matching `VITE_API_BASE_URL` in `frontend/.env`.
- CORS errors:
  - ensure frontend origin is present in `CORS_ORIGINS`.
  - restart backend after `.env` changes.
- Frontend fails at startup with env error:
  - ensure `frontend/.env` exists and includes `VITE_API_BASE_URL`.
