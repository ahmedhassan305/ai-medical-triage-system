# AI Medical Triage System - Technical Audit

## 1. Repository Map

### Audit Scope

- Repository root: `ai-medical-triage-system`
- Audit basis: every tracked file in the Git repository
- Excluded from scope because they are local untracked files:
  - `backend/triage.db`
  - `project_tree.txt`
- Large files inspected structurally:
  - `backend/data/*.json`
  - `frontend/package-lock.json`

### Complete Tracked Directory Tree

```text
/
├ .github/
│ └ workflows/
│   └ ci.yml
├ backend/
│ ├ alembic/
│ │ ├ versions/
│ │ │ └ 0001_crm_initial.py
│ │ ├ env.py
│ │ └ script.py.mako
│ ├ app/
│ │ ├ api/
│ │ │ ├ routes/
│ │ │ │ ├ __init__.py
│ │ │ │ ├ appointments.py
│ │ │ │ ├ auth.py
│ │ │ │ ├ doctors.py
│ │ │ │ ├ health.py
│ │ │ │ ├ patients.py
│ │ │ │ ├ records_import.py
│ │ │ │ ├ triage.py
│ │ │ │ └ visits.py
│ │ │ ├ __init__.py
│ │ │ ├ deps.py
│ │ │ └ router.py
│ │ ├ core/
│ │ │ ├ __init__.py
│ │ │ ├ config.py
│ │ │ ├ handlers.py
│ │ │ ├ logging.py
│ │ │ ├ middleware.py
│ │ │ └ security.py
│ │ ├ db/
│ │ │ ├ __init__.py
│ │ │ ├ models.py
│ │ │ └ session.py
│ │ ├ model/
│ │ │ ├ __init__.py
│ │ │ └ reasoner.py
│ │ ├ rag/
│ │ │ ├ eval/
│ │ │ │ ├ __init__.py
│ │ │ │ ├ eval_dataset.jsonl
│ │ │ │ └ evaluator.py
│ │ │ ├ __init__.py
│ │ │ ├ chunking.py
│ │ │ ├ dataset_loader.py
│ │ │ ├ embedding_model.py
│ │ │ ├ embedding_retriever.py
│ │ │ ├ faiss_store.py
│ │ │ ├ retriever.py
│ │ │ ├ tfidf_index.py
│ │ │ └ tfidf_retriever.py
│ │ ├ schemas/
│ │ │ ├ __init__.py
│ │ │ ├ appointment.py
│ │ │ ├ auth.py
│ │ │ ├ doctor.py
│ │ │ ├ error.py
│ │ │ ├ patient.py
│ │ │ ├ records.py
│ │ │ ├ triage.py
│ │ │ └ visit.py
│ │ ├ services/
│ │ │ ├ __init__.py
│ │ │ ├ patient_context.py
│ │ │ └ triage_service.py
│ │ ├ __init__.py
│ │ └ main.py
│ ├ data/
│ │ ├ mayo_dataset_part_1.json
│ │ ├ mayo_dataset_part_10.json
│ │ ├ mayo_dataset_part_2.json
│ │ ├ mayo_dataset_part_3.json
│ │ ├ mayo_dataset_part_4.json
│ │ ├ mayo_dataset_part_5.json
│ │ ├ mayo_dataset_part_6.json
│ │ ├ mayo_dataset_part_7.json
│ │ ├ mayo_dataset_part_8.json
│ │ └ mayo_dataset_part_9.json
│ ├ reports/
│ │ └ .gitkeep
│ ├ tests/
│ │ ├ fixtures/
│ │ │ ├ mayo_conditions.json
│ │ │ └ nhs_conditions.json
│ │ ├ conftest.py
│ │ ├ test_auth.py
│ │ ├ test_embedding_retriever.py
│ │ ├ test_health.py
│ │ ├ test_rag_retriever.py
│ │ ├ test_triage.py
│ │ └ test_triage_integration.py
│ ├ .dockerignore
│ ├ .env.example
│ ├ Dockerfile
│ ├ alembic.ini
│ ├ pyproject.toml
│ └ requirements.txt
├ frontend/
│ ├ src/
│ │ ├ api/
│ │ │ ├ appointments.ts
│ │ │ ├ auth.ts
│ │ │ ├ client.ts
│ │ │ ├ doctors.ts
│ │ │ ├ dto.ts
│ │ │ ├ errors.ts
│ │ │ ├ paths.ts
│ │ │ ├ patients.ts
│ │ │ ├ records.ts
│ │ │ ├ triage.ts
│ │ │ └ visits.ts
│ │ ├ components/
│ │ │ ├ AppointmentsPanel.tsx
│ │ │ ├ AuthPanel.tsx
│ │ │ ├ DashboardNav.tsx
│ │ │ ├ OverviewPanel.tsx
│ │ │ ├ ProfilePanel.tsx
│ │ │ ├ RecordsImportPanel.tsx
│ │ │ ├ SectionPanel.tsx
│ │ │ ├ TriageForm.tsx
│ │ │ ├ TriagePanel.tsx
│ │ │ └ VisitsPanel.tsx
│ │ ├ lib/
│ │ │ └ session.ts
│ │ ├ pages/
│ │ │ └ HomePage.tsx
│ │ ├ App.tsx
│ │ ├ index.css
│ │ └ main.tsx
│ ├ tests/
│ │ └ api-paths.test.ts
│ ├ .dockerignore
│ ├ .env.example
│ ├ Dockerfile
│ ├ eslint.config.js
│ ├ index.html
│ ├ package-lock.json
│ ├ package.json
│ ├ tsconfig.app.json
│ ├ tsconfig.json
│ ├ tsconfig.node.json
│ └ vite.config.ts
├ scripts/
│ ├ dev-backend.ps1
│ ├ dev-backend.sh
│ ├ dev-frontend.ps1
│ ├ dev-frontend.sh
│ ├ test-backend.ps1
│ ├ test-backend.sh
│ ├ test-frontend.ps1
│ └ test-frontend.sh
├ .env.example
├ .gitignore
├ .pre-commit-config.yaml
├ README.md
└ docker-compose.yml
```

## 2. System Architecture

### Purpose

- AI-assisted medical triage platform with CRM-style patient and doctor workflows.
- Combines clinical workflow management, patient history awareness, RAG retrieval, and local LLM reasoning.
- Built for local development, team collaboration, and future research iteration.

### Problem It Solves

- Gives a triage workflow that can use the current complaint, retrieved medical references, patient demographics, and prior visits.
- Provides adjacent clinical workflow scaffolding for auth, profiles, appointments, visits, and record imports.

### Intended Users

- Patients
- Doctors
- Admins
- Developers and researchers evaluating retrieval and reasoning quality

### High-Level Architecture

```text
User
  -> React frontend
  -> Axios API client
  -> FastAPI backend
  -> Triage service
      -> Patient history provider
      -> RAG retriever
      -> Reasoner
          -> Ollama
      -> SQLAlchemy / Postgres or SQLite
  -> JSON response
  -> Frontend rendering
```

### Architecture Description

- Frontend:
  - React + Vite + TypeScript single-page dashboard
  - auth, profile management, triage, appointments, visits, and record import
- Backend:
  - FastAPI app factory with versioned routing
  - JWT auth, role-based access, request logging, structured errors
- Reasoning layer:
  - runtime-selectable `ollama` or `stub`
- RAG layer:
  - runtime-selectable `stub`, `tfidf`, or `embedding`
- Database:
  - SQLite by default for backend-only local dev
  - Postgres in Docker for the integrated stack
- External services:
  - Ollama for local LLM inference
  - Postgres for relational persistence

### Diagram Narrative

- Users interact with the frontend dashboard.
- The frontend sends authenticated or unauthenticated requests to FastAPI.
- The backend routes either to CRUD flows backed by SQLAlchemy or to the triage service.
- The triage service combines heuristic risk classification, patient history, RAG retrieval, and summary generation.
- The reasoner can call Ollama over HTTP.
- The retriever can use TF-IDF or FAISS over local JSON knowledge files.

## 3. Triage Pipeline

### End-to-End Triage Flow

1. The user enters a symptom query in the frontend.
2. The frontend optionally includes `patient_id`.
3. The frontend sends `POST /api/v1/triage`.
4. `backend/app/api/routes/triage.py` calls `triage_service.triage()`.
5. `triage_service.py` normalizes the query.
6. `_classify()` assigns `low`, `medium`, or `high` risk using keyword rules.
7. `get_retriever()` resolves the configured retriever.
8. The retriever returns top contexts from the knowledge base.
9. If `patient_id` exists, `PatientContextProvider` loads demographics and recent visits from the database.
10. `get_reasoner()` resolves the configured reasoner.
11. The reasoner generates a summary using the complaint, triage level, patient history context, and RAG knowledge context.
12. `_build_actions()` maps the heuristic triage level to action suggestions.
13. The backend returns a `TriageResponse`.
14. The frontend renders the result, including `history_used`.

### Important Design Constraints

- The LLM does not decide the triage level.
- The triage level is currently determined only by keyword matching.
- The reasoner generates the narrative summary only.
- The output always includes a medical disclaimer.

### Keyword-Based Triage Rules

High-risk keywords:
- `chest pain`
- `shortness of breath`
- `difficulty breathing`
- `stroke`
- `seizure`
- `unconscious`
- `severe bleeding`
- `overdose`
- `suicidal`

Medium-risk keywords:
- `fever`
- `vomiting`
- `dehydration`
- `fracture`
- `burn`
- `infection`
- `migraine`

If nothing matches:
- `triage_level = low`

### Triage Response Shape

`TriageResponse` contains:
- `triage_level`
- `summary`
- `actions`
- `disclaimer`
- `history_used`

## 4. RAG System

### Purpose

- Injects retrieved medical reference content into the reasoner prompt.
- Supports a TF-IDF baseline and an embedding-based FAISS retriever.
- Exposes metadata for evaluation and provenance.

### RAG Modules

- `backend/app/rag/retriever.py`
- `backend/app/rag/dataset_loader.py`
- `backend/app/rag/chunking.py`
- `backend/app/rag/tfidf_index.py`
- `backend/app/rag/tfidf_retriever.py`
- `backend/app/rag/embedding_model.py`
- `backend/app/rag/faiss_store.py`
- `backend/app/rag/embedding_retriever.py`
- `backend/app/rag/eval/eval_dataset.jsonl`
- `backend/app/rag/eval/evaluator.py`

### Knowledge Base

Production corpus in Git:
- `backend/data/mayo_dataset_part_1.json`
- `backend/data/mayo_dataset_part_2.json`
- `backend/data/mayo_dataset_part_3.json`
- `backend/data/mayo_dataset_part_4.json`
- `backend/data/mayo_dataset_part_5.json`
- `backend/data/mayo_dataset_part_6.json`
- `backend/data/mayo_dataset_part_7.json`
- `backend/data/mayo_dataset_part_8.json`
- `backend/data/mayo_dataset_part_9.json`
- `backend/data/mayo_dataset_part_10.json`

Observed corpus facts:
- 10 JSON files
- 1161 total records
- Source family is primarily Mayo Clinic
- Test fixtures include tiny Mayo and NHS samples for deterministic tests

### Dataset Loader

`backend/app/rag/dataset_loader.py`:
- loads all JSON files from a configured directory
- supports multiple JSON container shapes
- normalizes records into `MedicalCondition`

`MedicalCondition` fields:
- `doc_id`
- `source_file`
- `source`
- `title`
- `url`
- `sections`
- `full_text`

Loader behavior:
- infers source from file name if absent
- builds `full_text` from explicit text or section fields
- retains section headings
- generates deterministic `doc_id` from source file and title

### Chunking

`backend/app/rag/chunking.py`:
- character-based chunking
- overlap preserved
- empty chunks removed

Relevant settings:
- `RAG_CHUNK_SIZE`
- `RAG_CHUNK_OVERLAP`

Defaults:
- `RAG_CHUNK_SIZE=2000`
- `RAG_CHUNK_OVERLAP=200`

### Retriever Contract

`backend/app/rag/retriever.py` defines:
- `RetrievedChunk`
- `Retriever` protocol
- `StubRetriever`

`RetrievedChunk` fields:
- `doc_id`
- `source_file`
- `chunk_id`
- `text`
- `source`
- `title`
- `url`
- `score`

### TF-IDF Retriever

Files:
- `backend/app/rag/tfidf_index.py`
- `backend/app/rag/tfidf_retriever.py`

Implementation details:
- `TfidfVectorizer`
- English stop words enabled
- configurable `max_features`
- configurable `ngram_range`
- similarity via `linear_kernel`

Settings:
- `TFIDF_MAX_FEATURES`
- `TFIDF_NGRAM_MIN`
- `TFIDF_NGRAM_MAX`

Defaults:
- `1000`
- `1`
- `2`

### Embedding Retriever

Files:
- `backend/app/rag/embedding_model.py`
- `backend/app/rag/faiss_store.py`
- `backend/app/rag/embedding_retriever.py`

Embedding model:
- `sentence-transformers/all-MiniLM-L6-v2`
- configured through `RAG_EMBED_MODEL`

Vector store:
- FAISS `IndexFlatIP`
- embeddings normalized before indexing
- query embeddings normalized before search
- inner product acts like cosine similarity in this setup

Cache behavior:
- lazy singleton model loader
- in-process cached retriever instance via `lru_cache`
- on-disk cache directory from `RAG_CACHE_DIR`
- persisted files:
  - `index.faiss`
  - `metadata.json`

Settings:
- `RAG_RETRIEVER`
- `RAG_DATA_DIR`
- `RAG_TOP_K`
- `RAG_EMBED_MODEL`
- `RAG_CACHE_DIR`
- `RAG_CHUNK_SIZE`
- `RAG_CHUNK_OVERLAP`
- `RAG_REBUILD_INDEX`

Retriever selection in `triage_service.py`:
- `stub` -> `StubRetriever`
- `tfidf` -> `TfidfRetriever`
- `embedding` -> `EmbeddingRetriever`
- missing data or init failure -> stub fallback

### RAG Evaluation

Files:
- `backend/app/rag/eval/eval_dataset.jsonl`
- `backend/app/rag/eval/evaluator.py`

CLI:

```bash
python -m app.rag.eval.evaluator --k 3 --retriever embedding
```

Optional:

```bash
python -m app.rag.eval.evaluator --k 3 --retriever embedding --llm_judge
```

Metrics:
- `recall@k`
- heuristic context relevance via token overlap
- optional Ollama LLM judge score

Report output:
- `backend/reports/rag_eval_report.json`

### RAG Limitations

- No hybrid retrieval
- No reranker
- No checksum-based cache invalidation
- No external vector database
- No source-specific weighting
- Evaluation dataset is small

## 5. Reasoning Engine

### Reasoner Implementations

File:
- `backend/app/model/reasoner.py`

Implementations:
- `StubReasoner`
- `OllamaReasoner`

### Reasoner Mode Selection

Configured in `backend/app/services/triage_service.py`:
- `REASONER_MODE=ollama|stub`
- `STRICT_REASONER=true|false`

Defaults:
- `REASONER_MODE=ollama`
- `STRICT_REASONER=false`

Selection behavior:
- `stub` returns `StubReasoner`
- `ollama` builds `OllamaReasoner`
- `OllamaReasoner.ping()` checks reachability with `/api/tags`
- if unreachable:
  - strict mode raises
  - non-strict mode logs fallback and returns `StubReasoner`

Expected logs:
- `reasoner_initialized mode=ollama model=...`
- `reasoner_initialized mode=stub model=none`
- `reasoner_fallback_to_stub reason=ollama_unreachable`

### Stub Reasoner

Purpose:
- deterministic local fallback for dev and tests

Behavior:
- if no contexts, returns a concise summary based on triage level only
- if contexts exist, cites up to two retrieved references by header
- if patient context exists, mentions that history context was included

### Ollama Reasoner

Purpose:
- generate the triage summary via a local LLM

Connection settings:
- `OLLAMA_HOST`
- `OLLAMA_MODEL`

Current default model:
- `llama3.2`

Inference endpoint:
- `POST /api/generate`

Request body shape:
- `model`
- `prompt`
- `stream: false`

Runtime behavior:
- no streaming
- 45-second default timeout
- falls back to stub if generation fails

### Prompt Composition

Inputs included in the prompt:
- heuristic triage level
- user query
- patient context block
- knowledge context block

Prompt intent:
- return one concise paragraph
- include risk rationale
- mention warning signs
- recommend next action
- avoid diagnosis certainty
- format as `Summary: <text>`

### Key Constraint

- The reasoner generates summary text only.
- It does not currently produce a structured explanation object.
- It does not currently override the heuristic triage level.

## 6. Backend Services

### App Factory

`backend/app/main.py`:
- creates the FastAPI app
- configures logging
- enables CORS
- installs request logging middleware
- registers exception handlers
- mounts versioned and legacy routers
- optionally auto-creates DB tables if `DB_AUTO_CREATE=true`
- optionally verifies reasoner availability at startup if `STRICT_REASONER=true`

### Core Configuration

`backend/app/core/config.py` centralizes environment settings:
- `APP_NAME`
- `API_V1_PREFIX`
- `CORS_ORIGINS`
- `DATABASE_URL`
- `DB_AUTO_CREATE`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`
- `RAG_DATA_DIR`
- `RAG_RETRIEVER`
- `RAG_TOP_K`
- `TFIDF_MAX_FEATURES`
- `TFIDF_NGRAM_MIN`
- `TFIDF_NGRAM_MAX`
- `RAG_EMBED_MODEL`
- `RAG_CACHE_DIR`
- `RAG_CHUNK_SIZE`
- `RAG_CHUNK_OVERLAP`
- `RAG_REBUILD_INDEX`
- `OLLAMA_HOST`
- `OLLAMA_MODEL`
- `REASONER_MODE`
- `STRICT_REASONER`
- `PATIENT_HISTORY_VISIT_LIMIT`
- `PATIENT_HISTORY_TOP_MATCHES`

### Middleware and Error Handling

`backend/app/core/middleware.py`:
- logs method, path, status code, and duration
- logs exceptions before re-raising

`backend/app/core/handlers.py`:
- validation error handler
- HTTPException handler
- catch-all exception handler
- consistent error schema via `backend/app/schemas/error.py`

### Security

`backend/app/core/security.py`:
- password hashing with passlib bcrypt
- password verification
- JWT creation
- JWT decoding

`backend/app/api/deps.py`:
- `OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")`
- extracts current authenticated user
- role-based dependency helper `require_roles(...)`

### Database Access

`backend/app/db/session.py`:
- builds SQLAlchemy engine
- supports SQLite and non-SQLite URLs
- exposes `SessionLocal`
- exposes `get_db()` dependency
- exposes `create_all()` helper

`backend/app/db/models.py`:
- SQLAlchemy ORM model definitions

### Triage Service

`backend/app/services/triage_service.py` is the main orchestration module.

Responsibilities:
- keyword-based triage classification
- retriever factory and cache
- reasoner factory and cache
- patient-history integration
- action selection
- final `TriageResponse` construction

Key functions:
- `_classify(query)`
- `_build_actions(triage_level)`
- `_build_retriever()`
- `get_retriever()`
- `_build_reasoner()`
- `get_reasoner()`
- `clear_runtime_state()`
- `triage(query, patient_id=None, db=None)`

### Patient History Provider

`backend/app/services/patient_context.py`:
- loads patient demographics from `PatientProfile`
- fetches recent visits
- ranks visits using simple token overlap similarity
- returns formatted history text and matched visit IDs

Relevant settings:
- `PATIENT_HISTORY_VISIT_LIMIT=10`
- `PATIENT_HISTORY_TOP_MATCHES=3`

## 7. API Layer

### Routing Structure

`backend/app/api/router.py`:
- mounts all versioned routes under `API_V1_PREFIX`, default `/api/v1`
- mounts legacy `/health` and `/triage` routes outside the OpenAPI schema

### Route Inventory

#### Health

- `GET /health`
- `GET /api/v1/health`
- purpose: health probe
- response: `{"status":"ok"}`

#### Triage

- `POST /triage`
- `POST /api/v1/triage`
- request body:
  - `query: string`
  - `patient_id?: integer`
- response:
  - `triage_level`
  - `summary`
  - `actions`
  - `disclaimer`
  - `history_used`

#### Auth

- `POST /api/v1/auth/register`
  - request: `email`, `password`, `role`
  - response: `id`, `email`, `role`, `created_at`
- `POST /api/v1/auth/login`
  - request: `email`, `password`
  - response: `access_token`, `token_type`, `user_id`, `role`
- `GET /api/v1/auth/me`
  - bearer auth required
  - returns current user

#### Patients

- `GET /api/v1/patients/`
  - roles: doctor, admin
  - lists patient profiles
- `POST /api/v1/patients/me`
  - roles: patient, admin
  - creates or updates own patient profile
- `GET /api/v1/patients/me`
  - any authenticated role
  - returns own patient profile or 404
- `GET /api/v1/patients/{patient_id}`
  - roles: doctor, admin
  - returns patient profile by ID

#### Doctors

- `GET /api/v1/doctors/`
  - roles: patient, doctor, admin
  - lists doctor profiles
- `POST /api/v1/doctors/me`
  - roles: doctor, admin
  - creates or updates own doctor profile
- `GET /api/v1/doctors/me`
  - any authenticated role
  - returns own doctor profile or 404
- `GET /api/v1/doctors/{doctor_id}`
  - roles: patient, doctor, admin
  - returns doctor profile by ID

#### Appointments

- `POST /api/v1/appointments/`
  - roles: patient, admin
  - creates appointment request
- `PATCH /api/v1/appointments/{appointment_id}/status`
  - roles: doctor, admin
  - approves or rejects appointment
- `GET /api/v1/appointments/`
  - roles: patient, doctor, admin
  - lists appointments

#### Visits

- `POST /api/v1/visits/`
  - roles: doctor, admin
  - creates visit
- `GET /api/v1/visits/patient/{patient_id}`
  - roles: patient, doctor, admin
  - lists visits for a patient ID

#### Records Import

- `POST /api/v1/records/import`
  - roles: doctor, admin
  - multipart endpoint
  - inputs: `patient_id`, `file`
  - imports structured JSON or CSV rows into visits

### API Contracts

Main schema files:
- `backend/app/schemas/triage.py`
- `backend/app/schemas/auth.py`
- `backend/app/schemas/patient.py`
- `backend/app/schemas/doctor.py`
- `backend/app/schemas/appointment.py`
- `backend/app/schemas/visit.py`
- `backend/app/schemas/records.py`
- `backend/app/schemas/error.py`

## 8. Frontend

### Stack

- React 19
- TypeScript 5
- Vite 7
- Axios
- ESLint
- Vitest

### Frontend Entry and Composition

- `frontend/src/main.tsx`: React entry point
- `frontend/src/App.tsx`: root component
- `frontend/src/pages/HomePage.tsx`: central dashboard orchestrator

### Frontend Architecture

- Single-page app
- No router library
- Tabbed dashboard after authentication
- LocalStorage-backed session
- Typed API layer

### Session Management

`frontend/src/lib/session.ts`:
- localStorage key: `ai-medical-triage-session`
- read session
- write session
- clear session
- extract access token

### API Layer

Files:
- `frontend/src/api/client.ts`
- `frontend/src/api/paths.ts`
- `frontend/src/api/dto.ts`
- `frontend/src/api/errors.ts`
- `frontend/src/api/auth.ts`
- `frontend/src/api/patients.ts`
- `frontend/src/api/doctors.ts`
- `frontend/src/api/appointments.ts`
- `frontend/src/api/visits.ts`
- `frontend/src/api/records.ts`
- `frontend/src/api/triage.ts`

Behavior:
- base URL comes from `VITE_API_BASE_URL`
- app throws early if env is missing
- axios interceptor attaches bearer token automatically
- DTOs mirror backend schemas

### Main Components

- `AuthPanel.tsx`: login and registration
- `DashboardNav.tsx`: tab navigation and logout
- `OverviewPanel.tsx`: summary cards
- `ProfilePanel.tsx`: patient and doctor profile forms
- `TriageForm.tsx`: complaint input form
- `TriagePanel.tsx`: triage workflow and result rendering
- `AppointmentsPanel.tsx`: appointment creation and approval
- `VisitsPanel.tsx`: visit creation and listing
- `RecordsImportPanel.tsx`: records upload
- `SectionPanel.tsx`: shared layout wrapper

### Frontend Limitations

- No route-based navigation
- No SSR
- No advanced validation library
- Very limited frontend test coverage
- No favicon file

## 9. Databases

### Relational Database

Supported runtime backends:
- SQLite for local backend-only development
- Postgres in Docker

Configured by:
- `DATABASE_URL`

Defaults:
- local backend example: `sqlite:///./triage.db`
- docker example: `postgresql+psycopg2://triage:triage@postgres:5432/triage`

### SQLAlchemy Models

Defined in `backend/app/db/models.py`:

`User`
- `id`
- `email`
- `hashed_password`
- `role`
- `created_at`

`PatientProfile`
- `id`
- `user_id`
- `full_name`
- `age`
- `sex`
- `smoker`
- `alcoholic`
- `chronic_conditions`
- `created_at`
- `updated_at`

`DoctorProfile`
- `id`
- `user_id`
- `full_name`
- `specialty`
- `clinic`
- `created_at`
- `updated_at`

`Visit`
- `id`
- `patient_id`
- `doctor_id`
- `symptoms`
- `vitals`
- `diagnosis`
- `notes`
- `prescriptions`
- `attachments`
- `created_at`

`Appointment`
- `id`
- `patient_id`
- `doctor_id`
- `status`
- `requested_at`
- `scheduled_for`
- `reason`
- `notes`

### Migrations and Storage

- Alembic config: `backend/alembic.ini`
- Alembic env: `backend/alembic/env.py`
- First migration: `backend/alembic/versions/0001_crm_initial.py`
- FAISS cache stores `index.faiss` and `metadata.json`
- Knowledge base lives in `backend/data/`
- Frontend session is stored in browser localStorage
- Reports are written to `backend/reports/`

### Data Not Persisted

- triage request history
- triage result history
- model prompts and outputs
- retrieved chunks per request
- conversation history

## 10. LLM Integration

### Provider

- Ollama only

No evidence of:
- OpenAI
- Anthropic
- Gemini
- hosted vector DB services
- LangChain or LlamaIndex orchestration

### Runtime Connection

Configured via:
- `OLLAMA_HOST`
- `OLLAMA_MODEL`

Current defaults:
- host: `http://localhost:11434`
- model: `llama3.2`

Docker backend uses:
- `OLLAMA_HOST=http://ollama:11434`

### Inference Style

- HTTP request to `POST /api/generate`
- non-streaming
- plain prompt text
- response body parsed for `response`

### Prompt Inputs

- triage level
- user complaint
- patient context
- RAG knowledge context

### Controls Not Yet Exposed

- temperature
- top_p
- max tokens
- stop sequences
- streaming UI
- structured JSON schema enforcement

## 11. Deployment

### Docker Compose Services

Defined in `docker-compose.yml`:

`backend`
- build: `./backend`
- port: `19001`
- mounts dataset directory
- mounts RAG cache volume
- connects to Ollama and Postgres through environment variables

`frontend`
- build: `./frontend`
- port: `5173`
- uses `VITE_API_BASE_URL`
- runs Vite dev server in the container

`ollama`
- image: `ollama/ollama`
- port: `11434`
- persistent model volume
- auto-pulls the configured model at startup

`postgres`
- image: `postgres:16-alpine`
- port: `5432`
- persistent data volume

Named volumes:
- `rag_cache`
- `ollama_models`
- `postgres_data`

### Dockerfiles and Env Files

- `backend/Dockerfile`: Python 3.11 backend container
- `frontend/Dockerfile`: Node 20 frontend container
- root `.env.example`: Docker-first defaults
- `backend/.env.example`: backend local defaults
- `frontend/.env.example`: frontend base URL env

### CI

`.github/workflows/ci.yml`:
- backend job: install, `ruff`, `black --check`, `pytest`
- frontend job: `npm ci`, `npm run lint`, `npm run test`, `npm run build`

### Deployment Gaps

- No production reverse proxy
- No production frontend serving strategy
- No health checks in Compose
- No migration job in Compose
- Frontend container is a dev server, not a production static build

## 12. Testing

### Backend Tests

- `backend/tests/conftest.py`: shared test setup
- `backend/tests/test_health.py`: health and docs behavior
- `backend/tests/test_auth.py`: register and login flow
- `backend/tests/test_triage.py`: low, medium, high triage, invalid input, legacy route, history flag
- `backend/tests/test_triage_integration.py`: stub and optional Ollama integration
- `backend/tests/test_rag_retriever.py`: TF-IDF retrieval and fallback behavior
- `backend/tests/test_embedding_retriever.py`: FAISS persistence, reload, and fallback behavior

### Frontend Tests

- `frontend/tests/api-paths.test.ts`: API path constant checks

### Evaluation Tooling

- `backend/app/rag/eval/evaluator.py`: retrieval evaluation CLI
- `backend/app/rag/eval/eval_dataset.jsonl`: small labeled retrieval benchmark set

### Coverage Summary

Covered reasonably for the current skeleton:
- health
- auth
- triage route
- retriever behavior
- reasoner integration path

Thin or missing coverage:
- appointments endpoint behavior
- visits permissions
- patient and doctor profile edge cases
- records import
- frontend component behavior
- end-to-end Docker workflows

## 13. Security

### Existing Controls

- JWT-based authentication
- password hashing with bcrypt
- role-based authorization helpers
- structured error responses
- CORS configuration
- triage disclaimer always present
- prompt instructs model to avoid diagnosis certainty

### Safety Controls in Triage

- high-risk symptom keyword escalation
- explicit emergency action guidance for high-risk output
- consistent disclaimer
- patient history is context-only, not blindly trusted as a decision engine

### Weaknesses and Gaps

- default JWT secret is placeholder-grade and unsafe for real deployment
- no rate limiting
- no refresh tokens
- no token revocation
- no password reset
- no email verification
- no audit trail for triage outputs or PHI access
- no encryption-at-rest design in repo

### Authorization Gaps

- `GET /api/v1/appointments/` returns all appointments to any authenticated role
- `GET /api/v1/visits/patient/{patient_id}` is accessible to any authenticated role
- `POST /api/v1/appointments/` lets patient or admin create appointments for arbitrary `patient_id`
- `GET /api/v1/patients/me` and `GET /api/v1/doctors/me` are not tightly role-scoped

### Auth Docs Mismatch

- `OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")` is configured for bearer extraction
- actual login endpoint accepts JSON body, not OAuth2 password form data
- Swagger security flow is therefore not a full OAuth2 password-form implementation

## 14. Missing Components

### Missing Persistence and Auditability

- No triage session table
- No persisted triage results
- No prompt and response audit log
- No clinician review queue
- No retrieved-context audit storage

### Missing Clinical Workflow Depth

- No dedicated medical records table
- Record import writes directly into visits
- No prescription entity
- No attachment storage backend
- No scheduling conflict logic
- No doctor-patient assignment model

### Missing AI and RAG Controls

- No structured LLM output parsing
- No confidence score
- No hallucination guard layer
- No refusal policy module
- No source citation enforcement in final summary
- No reranker
- No hybrid sparse plus dense retrieval
- No robust eval dataset
- No cache invalidation keyed to corpus changes

## 15. Suggested Improvements

1. Move direct ORM logic out of route handlers into service or repository modules.
2. Add readiness checks for Postgres and Ollama.
3. Add a migration container or automatic startup migration step.
4. Enforce per-user data ownership for visits and appointments.
5. Require a non-placeholder JWT secret outside dev.
6. Persist triage requests and outputs for auditability.
7. Return structured reasoning fields instead of only free text.
8. Expand the retrieval evaluation dataset substantially.
9. Replace token-overlap visit matching with embedding similarity.
10. Add route-level navigation and stronger frontend test coverage.

## Appendix A. File-by-File Responsibility Index

### Root and Tooling

- `.env.example`: Docker-first environment defaults for the integrated stack.
- `.gitignore`: ignores Python, Node, env, cache, and build artifacts.
- `.pre-commit-config.yaml`: linting and formatting hooks.
- `README.md`: setup, run, Docker, env, and troubleshooting documentation.
- `docker-compose.yml`: orchestrates backend, frontend, Ollama, and Postgres.
- `.github/workflows/ci.yml`: backend lint and tests, frontend lint, tests, and build.
- `scripts/dev-backend.ps1`, `scripts/dev-backend.sh`: backend local run helpers.
- `scripts/dev-frontend.ps1`, `scripts/dev-frontend.sh`: frontend local run helpers.
- `scripts/test-backend.ps1`, `scripts/test-backend.sh`: backend test helpers.
- `scripts/test-frontend.ps1`, `scripts/test-frontend.sh`: frontend test helpers.

### Backend Infrastructure

- `backend/.dockerignore`: excludes backend local artifacts from Docker context.
- `backend/.env.example`: backend local env template.
- `backend/Dockerfile`: backend container image definition.
- `backend/alembic.ini`: Alembic config shell.
- `backend/pyproject.toml`: black, ruff, and mypy config.
- `backend/requirements.txt`: backend dependency list.
- `backend/alembic/env.py`: Alembic runtime environment.
- `backend/alembic/script.py.mako`: Alembic revision template.
- `backend/alembic/versions/0001_crm_initial.py`: initial CRM schema migration.

### Backend Application Packages

- `backend/app/main.py`: FastAPI app factory and startup behavior.
- `backend/app/api/deps.py`: auth and role dependencies.
- `backend/app/api/router.py`: API router composition.
- `backend/app/api/routes/health.py`: health endpoint.
- `backend/app/api/routes/triage.py`: triage endpoint.
- `backend/app/api/routes/auth.py`: register, login, current user endpoints.
- `backend/app/api/routes/patients.py`: patient profile endpoints.
- `backend/app/api/routes/doctors.py`: doctor profile endpoints.
- `backend/app/api/routes/appointments.py`: appointment endpoints.
- `backend/app/api/routes/visits.py`: visit endpoints.
- `backend/app/api/routes/records_import.py`: structured record import endpoint.
- `backend/app/core/config.py`: centralized settings.
- `backend/app/core/handlers.py`: error handlers.
- `backend/app/core/logging.py`: logging setup.
- `backend/app/core/middleware.py`: request logging middleware.
- `backend/app/core/security.py`: password hashing and JWT helpers.
- `backend/app/db/models.py`: ORM models.
- `backend/app/db/session.py`: DB engine and session factory.
- `backend/app/model/reasoner.py`: stub and Ollama reasoners.
- `backend/app/services/triage_service.py`: triage orchestration.
- `backend/app/services/patient_context.py`: history-aware patient context builder.
- `backend/app/rag/retriever.py`: retriever protocol and stub retriever.
- `backend/app/rag/dataset_loader.py`: dataset normalization.
- `backend/app/rag/chunking.py`: chunking utility.
- `backend/app/rag/tfidf_index.py`: sparse retrieval indexing.
- `backend/app/rag/tfidf_retriever.py`: TF-IDF retriever.
- `backend/app/rag/embedding_model.py`: sentence-transformer loader.
- `backend/app/rag/faiss_store.py`: FAISS persistence and search helpers.
- `backend/app/rag/embedding_retriever.py`: dense retriever.
- `backend/app/rag/eval/eval_dataset.jsonl`: RAG benchmark set.
- `backend/app/rag/eval/evaluator.py`: RAG evaluation CLI.
- `backend/app/schemas/triage.py`: triage request and response schemas.
- `backend/app/schemas/auth.py`: auth schemas.
- `backend/app/schemas/patient.py`: patient profile schemas.
- `backend/app/schemas/doctor.py`: doctor profile schemas.
- `backend/app/schemas/appointment.py`: appointment schemas.
- `backend/app/schemas/visit.py`: visit schemas.
- `backend/app/schemas/records.py`: records import schema.
- `backend/app/schemas/error.py`: error schema.

### Backend Data and Tests

- `backend/data/mayo_dataset_part_1.json` through `backend/data/mayo_dataset_part_10.json`: production medical reference corpus shards.
- `backend/reports/.gitkeep`: keeps report directory tracked.
- `backend/tests/conftest.py`: shared test setup.
- `backend/tests/test_health.py`: health and docs tests.
- `backend/tests/test_auth.py`: auth tests.
- `backend/tests/test_triage.py`: triage tests.
- `backend/tests/test_triage_integration.py`: reasoner integration tests.
- `backend/tests/test_rag_retriever.py`: TF-IDF retrieval tests.
- `backend/tests/test_embedding_retriever.py`: embedding retrieval tests.
- `backend/tests/fixtures/mayo_conditions.json`: small test corpus.
- `backend/tests/fixtures/nhs_conditions.json`: small test corpus.

### Frontend Infrastructure and App

- `frontend/.dockerignore`: excludes frontend local artifacts from Docker context.
- `frontend/.env.example`: frontend env template.
- `frontend/Dockerfile`: frontend container image definition.
- `frontend/eslint.config.js`: ESLint configuration.
- `frontend/index.html`: Vite HTML shell.
- `frontend/package.json`: frontend scripts and dependencies.
- `frontend/package-lock.json`: pinned npm dependency graph.
- `frontend/tsconfig.json`, `frontend/tsconfig.app.json`, `frontend/tsconfig.node.json`: TypeScript config.
- `frontend/vite.config.ts`: Vite and Vitest config.
- `frontend/src/main.tsx`: app bootstrap.
- `frontend/src/App.tsx`: root component.
- `frontend/src/index.css`: global application styling.
- `frontend/src/lib/session.ts`: localStorage session helpers.
- `frontend/src/pages/HomePage.tsx`: main dashboard orchestrator.
- `frontend/src/api/client.ts`: axios client and token injection.
- `frontend/src/api/paths.ts`: versioned API path constants.
- `frontend/src/api/dto.ts`: shared TypeScript DTOs.
- `frontend/src/api/errors.ts`: API error normalization.
- `frontend/src/api/auth.ts`: auth API wrapper.
- `frontend/src/api/patients.ts`: patient profile API wrapper.
- `frontend/src/api/doctors.ts`: doctor profile API wrapper.
- `frontend/src/api/appointments.ts`: appointments API wrapper.
- `frontend/src/api/visits.ts`: visits API wrapper.
- `frontend/src/api/records.ts`: records import API wrapper.
- `frontend/src/api/triage.ts`: triage API wrapper.
- `frontend/src/components/AuthPanel.tsx`: auth UI.
- `frontend/src/components/DashboardNav.tsx`: navigation and logout.
- `frontend/src/components/OverviewPanel.tsx`: dashboard summary cards.
- `frontend/src/components/ProfilePanel.tsx`: profile editor.
- `frontend/src/components/TriageForm.tsx`: complaint form.
- `frontend/src/components/TriagePanel.tsx`: triage result workflow.
- `frontend/src/components/AppointmentsPanel.tsx`: appointment UI.
- `frontend/src/components/VisitsPanel.tsx`: visit UI.
- `frontend/src/components/RecordsImportPanel.tsx`: records upload UI.
- `frontend/src/components/SectionPanel.tsx`: shared section wrapper.
- `frontend/tests/api-paths.test.ts`: API path constant tests.

## Appendix B. Runtime Summary

### Local Development Without Docker

- Backend can run directly with Python 3.11.
- Frontend can run directly with Node 18+.
- Backend defaults to SQLite unless `DATABASE_URL` is overridden.
- Frontend requires `VITE_API_BASE_URL`.

### Local Development With Docker

- `docker compose up --build` starts:
  - backend
  - frontend
  - ollama
  - postgres
- Alembic migration still needs to be applied manually unless already done:

```bash
docker compose exec backend alembic upgrade head
```

### Important Runtime URLs

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:19001`
- Backend docs: `http://localhost:19001/docs`
- Ollama API: `http://localhost:11434`
- Postgres: `localhost:5432`
