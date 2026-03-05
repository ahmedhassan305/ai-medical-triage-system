# AI Medical Triage System (Monorepo)

## Repository Structure
- `backend/`: FastAPI API (routers, schemas, services, RAG, tests)
- `frontend/`: React + Vite + TypeScript app
- `scripts/`: helper scripts for local dev and tests
- `.github/workflows/ci.yml`: CI for backend and frontend
- `docker-compose.yml`: local Docker stack (backend + frontend + Ollama + Postgres)

## API Endpoints
- Versioned:
  - `GET /api/v1/health`
  - `POST /api/v1/triage`
  - `POST /api/v1/auth/register`
  - `POST /api/v1/auth/login`
  - `GET /api/v1/auth/me`
  - `POST /api/v1/patients/me`
  - `GET /api/v1/patients/me`
  - `GET /api/v1/patients/{patient_id}`
  - `POST /api/v1/doctors/me`
  - `GET /api/v1/doctors/me`
  - `GET /api/v1/doctors/{doctor_id}`
  - `POST /api/v1/appointments`
  - `PATCH /api/v1/appointments/{appointment_id}/status`
  - `GET /api/v1/appointments`
  - `POST /api/v1/visits`
  - `GET /api/v1/visits/patient/{patient_id}`
  - `POST /api/v1/records/import`
- Backward-compatible legacy paths:
  - `GET /health`
  - `POST /triage`

## One-Time Setup (Without Docker)

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

## Run Locally (Without Docker)

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

## How To Run Locally With Docker

### Prerequisites
- Docker Desktop installed and running
- Docker Desktop configured to use WSL2 backend
- WSL2 enabled on Windows

### First Run
```powershell
cd D:\Personal\Projects\ai-medical-triage-system
Copy-Item .env.example .env -ErrorAction SilentlyContinue
docker compose up --build
```

### Service URLs
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:19001`
- Ollama API: `http://localhost:11434`
- Postgres: `localhost:5432`

### Change Model (Ollama)
Edit root `.env`:
```env
OLLAMA_MODEL=llama3:8b-instruct-q4
```
Then restart:
```powershell
docker compose up --build
```

### Rebuild RAG Index
Set in root `.env`:
```env
RAG_REBUILD_INDEX=true
```
Run:
```powershell
docker compose up --build backend
```
After rebuild, switch it back to:
```env
RAG_REBUILD_INDEX=false
```

### Run RAG Evaluation
```powershell
cd backend
python -m app.rag.eval.evaluator --k 3 --retriever embedding
```
Report output:
```text
backend/reports/rag_eval_report.json
```

### Database Migrations (Alembic)
```powershell
cd backend
alembic upgrade head
```

## Docker Desktop Storage On D:\

If `C:\` is low on space, move Docker Desktop disk image to `D:\docker-wsl`.

### Preferred Method (Docker Desktop UI)
1. Quit Docker Desktop from tray icon: `Quit Docker Desktop`.
2. Open PowerShell and run:
```powershell
wsl --shutdown
```
3. Start Docker Desktop.
4. Open `Settings` -> `Resources` -> `Advanced`.
5. Set `Disk image location` to:
```text
D:\docker-wsl
```
6. Click `Apply & Restart`.

### Verify Move And Data
```powershell
docker info
docker system df
docker volume ls
docker images
```

Then verify project startup:
```powershell
cd D:\Personal\Projects\ai-medical-triage-system
docker compose up --build
```

## Tests And Lint

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
- `DATABASE_URL=sqlite:///./triage.db`
- `DB_AUTO_CREATE=false`
- `JWT_SECRET_KEY=change-me-in-production`
- `JWT_ALGORITHM=HS256`
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60`
- `RAG_DATA_DIR=./data`
- `RAG_RETRIEVER=stub` (`stub`, `tfidf`, `embedding`)
- `RAG_TOP_K=3`
- `OLLAMA_HOST=http://localhost:11434`
- `OLLAMA_MODEL=llama3:8b-instruct-q4`
- `REASONER_MODE=ollama`
- `STRICT_REASONER=false`
- `TFIDF_MAX_FEATURES=1000`
- `TFIDF_NGRAM_MIN=1`
- `TFIDF_NGRAM_MAX=2`
- `RAG_EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2`
- `RAG_CACHE_DIR=./.cache/rag`
- `RAG_CHUNK_SIZE=2000`
- `RAG_CHUNK_OVERLAP=200`
- `RAG_REBUILD_INDEX=false`
- `PATIENT_HISTORY_VISIT_LIMIT=10`
- `PATIENT_HISTORY_TOP_MATCHES=3`

### `frontend/.env`
- `VITE_API_BASE_URL=http://localhost:19001`

### Root `.env` (for Docker Compose)
- `OLLAMA_MODEL=llama3:8b-instruct-q4`
- `REASONER_MODE=ollama`
- `STRICT_REASONER=false`
- `RAG_REBUILD_INDEX=false`
- `VITE_API_BASE_URL=http://localhost:19001`
- `DATABASE_URL=postgresql+psycopg2://triage:triage@postgres:5432/triage`
- `POSTGRES_DB=triage`
- `POSTGRES_USER=triage`
- `POSTGRES_PASSWORD=triage`
- `JWT_SECRET_KEY=change-me-in-production`
- `DB_AUTO_CREATE=false`

## Troubleshooting
- Port conflict:
  - change local port mapping in `docker-compose.yml` and update `VITE_API_BASE_URL`.
- CORS errors:
  - ensure frontend origin is present in `CORS_ORIGINS` and restart backend.
- Missing WSL distro confusion:
  - run `wsl -l -v --all` to list all distros Docker can use.
