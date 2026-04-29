# AI Medical Triage System

Monorepo for a graduation-project medical triage platform built around:
- `backend/`: FastAPI + SQLAlchemy + Alembic + local RAG/LLM orchestration
- `frontend/`: React + TypeScript + Vite dashboard
- `docker-compose.yml`: local infrastructure stack and optional backend container profile
- `scripts/`: development, test, and seeding helpers

## Verified Stack
- FastAPI
- SQLAlchemy + Alembic
- React + TypeScript + Vite
- Ollama for local inference
- TF-IDF / embedding retrievers with FAISS persistence
- Postgres for team dev database

## Team Development Workflow

### Preferred daily workflow
Use Docker only for infrastructure:
- `postgres`
- `ollama`

Run application code locally:
- backend locally with `uvicorn --reload`
- frontend locally with `vite`

This avoids rebuilding the backend image on every code change and keeps the frontend completely out of Docker during development.

### First-time setup

#### 1. Clone and switch to the working branch
```powershell
git fetch origin
git switch --track origin/triage-phase5-improvements
```

#### 2. Backend setup
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
```

#### 3. Frontend setup
```powershell
cd ..\frontend
npm install
Copy-Item .env.example .env
```

#### 4. Start infrastructure only
```powershell
cd ..
Copy-Item .env.example .env -ErrorAction SilentlyContinue
docker compose up -d postgres ollama
```

#### 5. Run migrations
```powershell
cd backend
.\.venv\Scripts\activate
alembic upgrade head
```

#### 6. Seed the public doctor directory data
```powershell
cd ..
.\backend\.venv\Scripts\python scripts\seed_doctors.py
```

#### 7. Reset local demo data to a clean Egypt-like dataset
```powershell
cd ..
.\backend\.venv\Scripts\python scripts\reset_local_project_data.py
```

#### 8. Start the backend locally
```powershell
cd backend
.\.venv\Scripts\activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 19001
```

#### 9. Start the frontend locally
```powershell
cd ..\frontend
npm run dev
```

### Daily development after setup

#### Start infrastructure
```powershell
cd D:\Personal\Projects\ai-medical-triage-system-friend-updates-2026-04-20
docker compose up -d postgres ollama
```

#### Run backend locally
```powershell
cd backend
.\.venv\Scripts\activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 19001
```

#### Run frontend locally
```powershell
cd frontend
npm run dev
```

### After pulling new code
```powershell
git pull
cd backend
.\.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
cd ..
.\backend\.venv\Scripts\python scripts\seed_doctors.py
.\backend\.venv\Scripts\python scripts\reset_local_project_data.py
cd frontend
npm install
npm run dev
```

## Docker usage rules

### `docker compose up` is enough when:
- you only need Postgres and Ollama running
- you changed application code but are running backend/frontend locally
- you are restarting infrastructure after a reboot or a branch pull

Recommended command:
```powershell
docker compose up -d postgres ollama
```

### `docker compose up --build` is needed only when:
- you explicitly want the optional backend container profile
- `backend/Dockerfile` changed
- backend Python dependencies changed and you want them inside the backend image

Optional backend container workflow:
```powershell
docker compose --profile backend up --build backend postgres ollama
```

## Optional helper scripts

### Infrastructure only
```powershell
.\scripts\dev-infra.ps1
```

### Backend
```powershell
.\scripts\dev-backend.ps1
```

### Frontend
```powershell
.\scripts\dev-frontend.ps1
```

## URLs
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:19001`
- Backend docs: `http://localhost:19001/docs`
- Ollama API: `http://localhost:11434`
- Postgres: `localhost:5432`

### Change Model (Ollama)
Edit root `.env`:
```env
OLLAMA_MODEL=llama3.2
```
Then restart:
```powershell
.\backend\.venv\Scripts\python scripts\seed_doctors.py
```

## Doctor directory seed data

Canonical doctor seed file:
- `backend/data/doctors/alexandria_public_directory_seed.json`

Import command:
```powershell
.\backend\.venv\Scripts\python scripts\seed_doctors.py
```

Optional maintainer refresh command:
```powershell
.\backend\.venv\Scripts\python scripts\build_alexandria_doctor_seed.py
```

What it does:
- imports a curated public doctor directory dataset focused on Alexandria first
- the current canonical seed contains 119 Alexandria-focused public doctor listings
- stores provenance on each seeded doctor:
  - `source_name`
  - `source_url`
  - `booking_url`
  - `area`
  - `city`
- removes legacy fake prototype doctors from older friend-branch data
- upserts by `source_url` / doctor identity so the seed stays reproducible

Public data source used in this branch:
- Vezeeta public doctor directory/profile pages
- specialty coverage in the canonical seed includes Cardiology, Neurology, Neurosurgery, Internal Medicine, Gastroenterology, Dermatology, Psychiatry, Ophthalmology, Orthopedics, ENT, Pediatrics, and Family Medicine

## Clean local demo dataset

Canonical local cleanup + reseed command:
```powershell
.\backend\.venv\Scripts\python scripts\reset_local_project_data.py
```

What it does:
- removes local smoke-test and dummy records from:
  - `users`
  - `patient_profiles`
  - `doctor_profiles`
  - `appointments`
  - `visits`
- recreates the schema if the local SQLite file is empty
- reimports the canonical Alexandria public doctor directory seed
- seeds valid local login accounts for one admin, several doctors, and several patients
- populates the database with Egypt-like patient profiles, visit history, and 76 appointments with 58 past appointments

Seeded local credentials after reset:
- admin: `admin.ops@aimts-eg.com` / `AdminPass123!`
- doctor: `doctor.neurology@aimts-eg.com` / `DoctorPass123!`
- patient: `patient.mariam.hassan@aimts-eg.com` / `PatientPass123!`

Use this script for local/demo data only. It is intended to replace residue from smoke tests and previous manual experiments.

## Hybrid triage response

`POST /api/v1/triage` returns a structured, patient-friendly response that combines:
- `urgency_level` / legacy-compatible `triage_level`
- `urgency_label`
- `urgency_reason`
- `patient_friendly_explanation`
- `clinical_summary`
- ranked `suspected_conditions`
- `recommended_specialty`
- `specialty_reason`
- `suggested_doctors`
- `recommended_actions`
- `supporting_references`
- `history_used`
- `disclaimer`

Behavior:
- anonymous triage is allowed for `query` only
- `patient_id` requires authentication and authorization
- possible conditions are not presented as a confirmed diagnosis
- recommended doctor cards can hand off directly into appointment booking

## Patient national ID parsing

Patient registration and profile editing support:
- `national_id`
- derived `date_of_birth`
- derived `inferred_governorate_code`
- derived `inferred_governorate`
- editable `current_governorate`

Rules:
- `national_id` must be a valid 14-digit Egyptian national ID
- date of birth is derived from the ID
- the governorate encoded in the ID is stored separately from current residence
- gender is restricted to `Male` or `Female`

## Validation

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
npm run test -- --run
npm run build
```

## API surface
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
- `GET /api/v1/doctors/specialty/{specialty}`
- `POST /api/v1/appointments/`
- `PATCH /api/v1/appointments/{appointment_id}/status`
- `GET /api/v1/appointments/`
- `POST /api/v1/visits/`
- `GET /api/v1/visits/`
- `GET /api/v1/visits/patient/{patient_id}`
- `POST /api/v1/records/import`

Legacy compatibility:
- `GET /health`
- `POST /triage`

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
- `OLLAMA_MODEL=llama3.2`
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
- `OLLAMA_MODEL=llama3.2`
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
