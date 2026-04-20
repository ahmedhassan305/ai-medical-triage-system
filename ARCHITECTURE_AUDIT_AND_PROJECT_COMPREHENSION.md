# ARCHITECTURE_AUDIT_AND_PROJECT_COMPREHENSION

Audit scope:
- Repository audited: `ai-medical-triage-system-friend-updates-2026-04-20`
- Branch under review: `review-friend-updates-2026-04-20` tracking `origin/friend-updates-2026-04-20`
- This report is evidence-based and describes what is actually present in code on this branch.
- No architectural rebuild was performed in this phase.

## 1. Executive Summary

This repository is a monorepo with a React frontend, a FastAPI backend, Docker-based local orchestration, Alembic migrations, and a local RAG + Ollama reasoning stack. The overall direction is clearly an AI-powered medical triage platform with CRM-style hospital workflows, but the audited friend branch is in a mixed state:

- The core monorepo structure is real and active.
- The backend CRM stack is real: auth, patients, doctors, appointments, visits, and record import all exist in code.
- The AI stack is real: retrievers, dataset loader, embedding model, FAISS persistence, evaluation script, and Ollama reasoner all exist.
- The frontend is real and connected: auth, profile management, triage, appointments, visits, and record import UI are implemented in one dashboard shell.
- The branch also contains prototype/experimental additions that are not fully integrated and currently introduce regressions.

High-level conclusion:
- Verified in code: versioned FastAPI API, JWT auth, patient/doctor/admin roles, Postgres or SQLite support, RAG retrieval, patient history injection into triage, frontend dashboard, Docker Compose stack.
- Partially implemented: doctor recommendation on triage, suspected-condition mapping, RAG-grounded reasoning, production-like deployment hardening.
- Mentioned in docs/context but not present in this branch: triage history/detail endpoints, readiness endpoint, persisted triage sessions/results, audit logs, retrieved chunk logs, structured triage output with confidence/sources/decision fields.
- Prototype-only or noisy artifacts: `backend/app/api/endpoints/`, `Untitled-1.ipynb`, root-level ad hoc scripts, SQL seed file, response demos, implementation note.

Branch health summary:
- Frontend: installs, lints, tests, and builds successfully.
- Backend: unit tests mostly pass, but this branch currently has 2 failing backend tests and style/lint failures.
- The main runtime regression is in `backend/app/services/triage_service.py`, where friend-added suspected-condition logic assumes retrieved objects with `.title` and `.body`, but the active retriever interface returns strings from `retrieve()`. This breaks triage whenever retrieval returns non-empty contexts.

## 2. Verified Tech Stack

### Verified in code

| Layer | Verified stack |
|---|---|
| Frontend | React 19, TypeScript 5.9, Vite 7, Axios, Vitest, ESLint |
| Backend | FastAPI, Uvicorn, SQLAlchemy 2, Alembic, Pydantic, Passlib bcrypt, python-jose |
| Database | SQLite by default for local backend, Postgres in Docker Compose |
| LLM | Ollama over HTTP (`/api/generate`) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store | FAISS (`faiss-cpu`) persisted to local disk |
| Sparse retrieval | Scikit-learn TF-IDF |
| Testing | Pytest (backend), Vitest (frontend) |
| CI | GitHub Actions (`.github/workflows/ci.yml`) |
| Containerization | Dockerfiles for backend/frontend and root `docker-compose.yml` |

### Mentioned in docs/context only, not verified on this branch
- Structured triage result with `confidence`, `sources`, and `decision`
- Triage history/detail API endpoints
- Readiness endpoint
- Persisted triage session tables
- Audit log tables
- Retrieved chunk logging tables
- Hybrid retrieval merge/rerank layer

## 3. Repository Structure Map

### Top-level repository shape
This is a single monorepo containing backend, frontend, scripts, CI, Docker, test fixtures, and some branch-local prototype artifacts.

Concise tree:

```text
/
├─ .github/workflows/ci.yml
├─ backend/
│  ├─ app/
│  │  ├─ api/
│  │  │  ├─ routes/
│  │  │  ├─ endpoints/           # deprecated/prototype
│  │  │  ├─ deps.py
│  │  │  └─ router.py
│  │  ├─ core/
│  │  ├─ db/
│  │  ├─ model/
│  │  ├─ rag/
│  │  ├─ schemas/
│  │  ├─ services/
│  │  ├─ main.py
│  │  └─ patient_symptoms.py
│  ├─ alembic/
│  ├─ data/
│  ├─ tests/
│  ├─ Dockerfile
│  ├─ requirements.txt
│  └─ pyproject.toml
├─ frontend/
│  ├─ src/
│  │  ├─ api/
│  │  ├─ components/
│  │  ├─ lib/
│  │  ├─ pages/
│  │  ├─ App.tsx
│  │  ├─ index.css
│  │  └─ main.tsx
│  ├─ tests/
│  ├─ Dockerfile
│  └─ package.json
├─ scripts/
├─ docker-compose.yml
├─ README.md
├─ IMPLEMENTATION_SUMMARY.md
├─ RESPONSE_FORMAT_DEMO.py
├─ response_output.json
├─ add_doctors.sql
├─ quick_test.py
├─ test_api.py
├─ test_conditions.py
├─ test_simple.py
├─ verify_api.py
└─ verify_symptoms.py
```

### Directory responsibility map

#### Active and central
- `backend/app/api/routes/`: actual HTTP route handlers used by the running backend.
- `backend/app/services/`: core orchestration, especially triage and patient-context logic.
- `backend/app/rag/`: active retrieval implementations, embedding model loading, FAISS persistence, dataset loader, evaluation.
- `backend/app/model/`: reasoner interface + Ollama/stub implementations.
- `backend/app/db/`: SQLAlchemy session and ORM models.
- `backend/app/schemas/`: API contracts.
- `backend/alembic/`: active migration setup.
- `frontend/src/`: active client app.
- `scripts/`: lightweight local dev/test wrappers.

#### Active but supporting
- `backend/data/`: production knowledge corpus used by retrievers.
- `backend/tests/`: actual backend automated tests.
- `frontend/tests/`: minimal frontend automated tests.
- `.github/workflows/ci.yml`: actual CI definition.

#### Prototype/noisy/likely abandoned
- `backend/app/api/endpoints/`: not wired into router; one file explicitly says it is deprecated.
- `backend/app/api/endpoints/Untitled-1.ipynb`: empty notebook cell, not part of runtime.
- `IMPLEMENTATION_SUMMARY.md`: branch note summarizing friend changes, not a system spec.
- `RESPONSE_FORMAT_DEMO.py`: local demonstration script, not runtime code.
- `response_output.json`: captured sample response, not authoritative.
- `add_doctors.sql`: raw SQL seed duplicated by Alembic revision `0002_add_prototype_doctors.py`.
- `quick_test.py`, `test_api.py`, `test_conditions.py`, `test_simple.py`, `verify_api.py`, `verify_symptoms.py`: ad hoc local scripts, not integrated into CI or package scripts.

## 4. System Context Diagram

### Textual context diagram

```text
User
  -> React/Vite frontend
     -> Axios API client
        -> FastAPI backend
           -> Auth / CRM routes
           -> Triage service
              -> PatientContextProvider (DB visit history)
              -> Retriever (stub | tfidf | embedding)
                 -> local dataset JSON files
                 -> TF-IDF or SentenceTransformer + FAISS
              -> Reasoner (stub | Ollama)
                 -> Ollama HTTP API
           -> SQLAlchemy session
              -> SQLite or Postgres
```

### Critical triage execution dependency map

```text
frontend/src/components/TriageForm.tsx
  -> frontend/src/components/TriagePanel.tsx
    -> frontend/src/pages/HomePage.tsx::handleRunTriage
      -> frontend/src/api/triage.ts::triage
        -> POST /api/v1/triage
          -> backend/app/api/routes/triage.py::triage_route
            -> backend/app/services/triage_service.py::triage
              -> _classify(query)
              -> get_retriever().retrieve(query)
                -> TfidfRetriever or EmbeddingRetriever
                  -> backend/app/rag/*
              -> PatientContextProvider.build(db, patient_id, query)
              -> get_reasoner().reason(query, contexts, triage_level, patient_context)
                -> StubReasoner or OllamaReasoner
                  -> Ollama /api/generate
              -> TriageResponse
        -> frontend renders result in TriagePanel
```

## 5. Runtime Service Inventory

### Verified runtime services

| Service | Verified in code | Purpose | Notes |
|---|---|---|---|
| Frontend | Yes | React dashboard served by Vite | Container runs dev server, not production static build |
| Backend | Yes | FastAPI API and orchestration | Sync route handlers, sync DB access |
| Ollama | Yes | Local model inference over HTTP | Pulled in Compose, but model defaults are inconsistent |
| Postgres | Yes | Docker DB runtime | Used by Compose; local backend defaults to SQLite |
| SQLite | Yes | Local non-Docker DB | Backend default in `backend/.env.example` |
| FAISS local store | Yes | Local vector index persistence | Not a separate runtime service |
| SentenceTransformer model | Yes | Embedding generation | Loaded in backend process |

### Not present as runtime services
- Redis
- Celery/RQ/queue workers
- external vector DB
- message broker
- reverse proxy
- background job service
- dedicated EHR integration service

### Communication paths

#### Frontend -> Backend
- Axios client in `frontend/src/api/client.ts`
- Base URL comes from `VITE_API_BASE_URL`
- JWT token injected from `localStorage`
- HTTP JSON + multipart form data (records import)

#### Backend -> Database
- SQLAlchemy sync engine in `backend/app/db/session.py`
- `SessionLocal` injected via `Depends(get_db)`
- SQLite `check_same_thread=False` if SQLite URL used

#### Backend -> Ollama
- `httpx.Client` in `backend/app/model/reasoner.py`
- `GET /api/tags` for ping
- `POST /api/generate` for inference

#### Backend -> RAG storage
- Reads JSON corpus from `backend/data/*.json`
- Reads/writes FAISS index and metadata under configured cache directory

### Sync/async model
- FastAPI app is mixed only at framework boundary:
  - middleware is async
  - endpoints are mostly sync `def`
- DB usage is sync SQLAlchemy
- RAG retrieval is sync in-process
- Ollama calls are sync HTTP
- No async tasks or queue-based work

## 6. Frontend Architecture

### Framework/tooling
- React + TypeScript + Vite
- No route library detected
- No global state library detected
- No form library detected
- CSS is centralized in `frontend/src/index.css`

### Frontend structure

#### Entry points
- `frontend/src/main.tsx`: mounts React app
- `frontend/src/App.tsx`: renders `HomePage`
- `frontend/src/pages/HomePage.tsx`: the real frontend orchestrator

#### Shared modules
- `frontend/src/api/`: HTTP client, DTOs, path registry, endpoint wrappers
- `frontend/src/lib/session.ts`: localStorage-based session persistence
- `frontend/src/components/`: dashboard panels

### Routing structure
- No client-side router is present.
- The application is a single-page dashboard controlled by a tab state in `HomePage.tsx`.
- Tabs are managed by `DashboardNav.tsx`.

### Major UI modules
- `AuthPanel.tsx`: combined login/register screen
- `DashboardNav.tsx`: role-filtered tab switcher
- `OverviewPanel.tsx`: summary cards
- `ProfilePanel.tsx`: patient and/or doctor profile forms
- `TriagePanel.tsx`: triage input/result panel
- `AppointmentsPanel.tsx`: appointment request and approval panel
- `VisitsPanel.tsx`: visit creation and visit listing
- `RecordsImportPanel.tsx`: bulk import for visits

### API client structure
- `frontend/src/api/client.ts`: creates Axios client, injects bearer token
- `frontend/src/api/paths.ts`: central path constants under `/api/v1`
- `frontend/src/api/dto.ts`: DTO definitions aligned to backend schemas
- Per-domain wrappers in `frontend/src/api/*.ts`

### Auth state management
- Session is stored in `localStorage` under key `ai-medical-triage-session`
- `HomePage.tsx` hydrates the session by calling `/api/v1/auth/me`
- If missing/expired, UI returns to `AuthPanel`

### Triage UI flow
1. User types complaint in `TriageForm.tsx`
2. Optional patient selector is available
3. `HomePage.handleRunTriage()` calls `frontend/src/api/triage.ts`
4. Result is rendered in `TriagePanel.tsx`
5. Friend branch result UI currently shows:
   - triage level
   - history_used flag
   - simple reasoning
   - suspected condition
   - recommended specialty
   - suggested doctors
   - summary
   - actions
   - disclaimer

### Patient flow (verified)
- Register/login
- Create patient profile
- View own visits through the visits panel
- Request appointment
- Run triage with selected/linked patient profile

### Doctor flow (verified)
- Register/login
- Create doctor profile
- View all appointments
- Approve/reject appointments
- Create visits
- Import records

### Admin flow (verified)
- Register/login as admin
- Access both patient and doctor profile forms in one UI
- Access all tabs, including records import

### Frontend UX inconsistencies / technical debt

#### Verified problems
- `HomePage.tsx` always calls both `fetchMyPatientProfile()` and `fetchMyDoctorProfile()` regardless of role. This causes predictable 404 noise and is not role-clean.
- There is no route-based deep linking; all navigation is tab state.
- The app does not render `plain_language_explanation` even though the backend schema includes it.
- Frontend only has one lightweight test file covering API path constants.
- There is no specialty-filter UI even though backend exposes `/doctors/specialty/{specialty}`.
- Triage does not display sources or confidence because this branch’s API schema does not include them.
- Appointments and visits panels rely on backend to filter data, but the backend currently does not enforce ownership properly.

## 7. Backend Architecture

### Backend framework and entry point
- Framework: FastAPI
- Entry point: `backend/app/main.py`

`create_app()` responsibilities:
- load settings
- configure logging
- configure CORS
- install request logging middleware
- register exception handlers
- include API routers
- optionally create tables when `DB_AUTO_CREATE=true`
- optionally initialize strict reasoner

### Module structure
- `app/api/routes/`: active HTTP route handlers
- `app/core/`: config, logging, middleware, error handling, security helpers
- `app/db/`: ORM models and session
- `app/model/`: reasoner implementations
- `app/rag/`: retrieval/indexing/evaluation stack
- `app/services/`: triage orchestration + patient context
- `app/schemas/`: request/response models

### Route/module inventory

#### Health
- `GET /health`
- `GET /api/v1/health`
- Returns `{"status": "ok"}` only
- No readiness endpoint in this branch

#### Auth
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

#### Patients
- `GET /api/v1/patients/`
- `POST /api/v1/patients/me`
- `GET /api/v1/patients/me`
- `GET /api/v1/patients/{patient_id}`

#### Doctors
- `GET /api/v1/doctors/`
- `GET /api/v1/doctors/specialty/{specialty}`
- `POST /api/v1/doctors/me`
- `GET /api/v1/doctors/me`
- `GET /api/v1/doctors/{doctor_id}`

#### Appointments
- `POST /api/v1/appointments/`
- `PATCH /api/v1/appointments/{appointment_id}/status`
- `GET /api/v1/appointments/`

#### Visits
- `POST /api/v1/visits/`
- `GET /api/v1/visits/patient/{patient_id}`

#### Records import
- `POST /api/v1/records/import`

#### Triage
- `POST /triage`
- `POST /api/v1/triage`

### Auth implementation
- JWT via `python-jose`
- bcrypt hashing via Passlib in `backend/app/core/security.py`
- token extraction via `OAuth2PasswordBearer` in `backend/app/api/deps.py`
- bearer auth stored client-side in localStorage

### Models/entities/schemas
Verified entities in ORM:
- `User`
- `PatientProfile`
- `DoctorProfile`
- `Appointment`
- `Visit`

No verified ORM entities for:
- triage sessions
- triage results
- audit logs
- retrieved chunk logs

### Service layer structure
- Only two real service files exist:
  - `backend/app/services/triage_service.py`
  - `backend/app/services/patient_context.py`
- Most CRM business logic is still inside route files rather than dedicated services.

### Where business logic really lives
- Triage orchestration and friend-added doctor suggestion logic live in `triage_service.py`
- Patient history ranking and formatting live in `patient_context.py`
- Auth logic is embedded directly in `auth.py`
- Appointment logic is embedded directly in `appointments.py`
- Visit logic is embedded directly in `visits.py`
- Record import parsing/creation is embedded directly in `records_import.py`

### Appointment workflow implementation
- Patients/admins can create appointment requests
- Doctors/admins can approve/reject status
- Listing returns all appointments regardless of owner role
- No scheduling conflict logic
- No doctor availability model

### Visits/history workflow implementation
- Doctors/admins can create visits
- Any authenticated role can query visits for any patient ID via API
- Patient history provider uses visit text similarity and demographics for triage context

### Records import workflow implementation
- Endpoint accepts `patient_id` form field and a `.json` or `.csv` file
- File content becomes `Visit` rows
- Only these fields are imported from record entries:
  - `doctor_id`
  - `symptoms`
  - `diagnosis`
  - `notes`
  - `prescriptions`
- `vitals` and `attachments` are ignored during import and set to `None`

### Role enforcement (verified)
- Route-level restrictions exist through `require_roles()`
- Enforcement is inconsistent and too broad in several places
- `GET /patients/me` and `GET /doctors/me` use only `get_current_user`, not role-specific checks

## 8. Data Model and Persistence

### Database technology
- Local default: SQLite (`sqlite:///./triage.db`)
- Docker default: Postgres (`postgresql+psycopg2://triage:triage@postgres:5432/triage`)
- ORM: SQLAlchemy 2 declarative mapping
- Migration tool: Alembic

### Migration inventory
- `0001_crm_initial.py`: creates users, doctor_profiles, patient_profiles, appointments, visits
- `0002_add_prototype_doctors.py`: seeds doctor_profiles with prototype doctors

### Table/model relationships

#### `users`
- 1-to-1 optional with `patient_profiles`
- 1-to-1 optional with `doctor_profiles`

#### `patient_profiles`
- optional `user_id`
- has many `visits`
- has many `appointments`

#### `doctor_profiles`
- optional `user_id`
- has many `visits`
- has many `appointments`
- can also exist without a linked user due to prototype seeding

#### `appointments`
- belongs to patient profile
- belongs to doctor profile
- has status, requested_at, scheduled_for, reason, notes

#### `visits`
- belongs to patient profile
- optional doctor profile
- stores symptoms, vitals JSON, diagnosis, notes, prescriptions, attachments JSON

### Patient entity shape
Verified patient profile fields:
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

### Doctor entity shape
Verified doctor profile fields:
- `id`
- `user_id`
- `full_name`
- `specialty`
- `clinic`
- `created_at`
- `updated_at`

### Appointment entity shape
Verified fields:
- `id`
- `patient_id`
- `doctor_id`
- `status`
- `requested_at`
- `scheduled_for`
- `reason`
- `notes`

### Visit entity shape
Verified fields:
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

### Diagnosis / triage history persistence

#### Verified in code
- Visit diagnosis is stored in `visits.diagnosis`
- Triage does not persist to dedicated triage tables on this branch

#### Missing in this branch
- `triage_sessions`
- `triage_results`
- `audit_logs`
- `retrieved_chunks_log`
- Triage history/detail persistence API

### Vector store / cache layer
Verified in code:
- FAISS local index file
- local metadata JSON file
- embedding model singleton cache in process

Not verified:
- external vector DB
- Redis cache

### Is medical history actually integrated into inference?
Yes, partially and directly.
- If `patient_id` is supplied to triage and a DB session exists, `PatientContextProvider.build()` loads demographics and recent visits.
- It creates a text block with demographics and top similarity-matched visit lines.
- That text is passed into the reasoner prompt as `patient_context`.

Important caveat:
- The triage route is unauthenticated, so any caller can provide a `patient_id` and cause patient context to be injected into the LLM prompt.
- This is a significant privacy risk even though the raw context is not directly returned by the API.

## 9. LLM / RAG / Triage Pipeline

### Exact triage execution path
1. Frontend sends `POST /api/v1/triage` with `query` and optional `patient_id`
2. `backend/app/api/routes/triage.py` calls `triage_service.triage(query, patient_id, db)`
3. `triage_service._classify()` assigns `low`, `medium`, or `high` by keyword matching only
4. `get_retriever()` chooses stub, TF-IDF, or embedding retriever
5. Retriever returns list of formatted context strings from medical corpus
6. `PatientContextProvider` optionally builds demographics + similar visit context text
7. `get_reasoner()` chooses stub or Ollama reasoner
8. Reasoner receives:
   - raw query
   - retrieved contexts
   - heuristic triage level
   - patient context text
9. Reasoner returns a single summary string
10. Friend branch post-processes summary/query into:
    - `simple_reasoning`
    - `recommended_specialty`
    - `suspected_condition`
    - `suggested_doctors`
11. API returns `TriageResponse`

### Triage decision logic type
Verified in code:
- Heuristic / keyword-based severity classification
- Prompt-based summary generation
- Retrieval-assisted context injection if retriever enabled
- Rule-based specialty suggestion and suspected-condition mapping after reasoner output

Not verified in code:
- disease ranking model
- probabilistic differential diagnosis list
- structured confidence scoring
- multiple-candidate ranking
- cross-encoder reranking
- hybrid sparse+dense merge

### Retrieval strategy

#### Verified in code
- Stub retriever
- TF-IDF retriever over normalized `MedicalCondition.full_text`
- Embedding retriever using sentence-transformers + FAISS

#### Not present
- BM25 implementation
- query rewriting/transformation
- hybrid result fusion
- reranking stage

### Knowledge source
Verified production corpus in this branch:
- `backend/data/*.json`
- 10 Mayo Clinic JSON files
- 1161 total records detected by inspection script

Test-only corpus:
- `backend/tests/fixtures/mayo_conditions.json`
- `backend/tests/fixtures/nhs_conditions.json`

Conclusion:
- Production corpus is Mayo-only on this branch.
- NHS is present only as a test fixture.

### Chunking and indexing
- Chunking: `backend/app/rag/chunking.py`
- Chunking strategy: simple character slicing with overlap
- TF-IDF index: built lazily in `TfidfRetriever`
- Dense index: built lazily in `EmbeddingRetriever`
- FAISS persistence: `index.faiss` + `metadata.json`

### Where similarity search happens
- Sparse similarity: `backend/app/rag/tfidf_index.py::search()` via `linear_kernel`
- Dense similarity: `backend/app/rag/faiss_store.py::search_index()` via FAISS inner product on normalized embeddings

### Which model is used
- Embedding model default: `sentence-transformers/all-MiniLM-L6-v2`
- Reasoner model default in backend code: `llama3:8b-instruct-q4`
- Docker backend default: `llama3.2`
- Docker Ollama service default: `llama3:8b-instruct-q4_K_M`

This model configuration is inconsistent across files.

### Where prompts are defined
- Only in `backend/app/model/reasoner.py`
- Ollama prompt is a plain-language medical explanation prompt
- No centralized prompt template module exists

### How final response is formatted
Friend branch response model in `backend/app/schemas/triage.py` returns:
- `triage_level`
- `summary`
- `simple_reasoning`
- `plain_language_explanation`
- `actions`
- `recommended_specialty`
- `suspected_condition`
- `suggested_doctors`
- `disclaimer`
- `history_used`

### Are outputs grounded or cited?
- Retrieved contexts are passed into the reasoner prompt.
- Final API response does not include retrieved sources or citations.
- `suggested_doctors` are database lookups, not evidence citations.
- Therefore outputs are RAG-informed but not explicitly grounded/cited in the API contract.

### Why outputs may be vague/general on this branch
Verified contributing reasons:
- Severity is only low/medium/high heuristic, not condition-level reasoning.
- Ollama prompt explicitly asks for a short plain-language paragraph, which compresses detail.
- No structured JSON output from the reasoner.
- No response field for evidence sources.
- `get_suspected_condition()` is heuristic keyword matching, not disease ranking.
- `rag_context` argument exists in `get_suspected_condition()` but is not actually used in `combined_text`; comments overstate its grounding role.

### Is the system doing disease ranking?
No.
- It returns one heuristic `suspected_condition` string selected from rule-based keyword mappings.
- There is no ranked disease list or probability distribution.
- This is best described as broad urgency classification + summary generation + heuristic specialty/condition suggestion.

### Branch-specific regression in triage pipeline
This is the most important verified runtime issue:
- `triage_service.triage()` calls `get_retriever().retrieve(...)`, which returns `list[str]`
- Friend-added code later does:
  - `c.title`
  - `c.body[:200]`
- On strings, `.title` is a built-in method and `.body` does not exist
- Result: triage crashes when contexts are non-empty
- This was confirmed by failing backend test `test_api_v1_triage_with_tfidf_has_summary`

## 10. Auth / Roles / Security

### Verified auth/role system
- User roles: `patient`, `doctor`, `admin`
- JWT includes `sub`, `role`, `exp`
- Routes use `require_roles()` for coarse access control

### Verified role behavior

#### Patient
- can register/login
- can upsert patient profile
- can list doctors
- can create appointments
- can call triage
- can fetch visits endpoint if patient_id known

#### Doctor
- can register/login
- can upsert doctor profile
- can approve/reject appointments
- can create visits
- can import records
- can call triage

#### Admin
- can do both profile types
- can list patients and doctors
- can create appointments and visits
- can import records

### Security weaknesses verified in code

#### 1. Public triage can consume patient history
- `POST /api/v1/triage` has no auth dependency
- caller may pass `patient_id`
- patient demographics and matched visit summaries are injected into the prompt
- this is a privacy leak vector

#### 2. Appointment listing is global
- `GET /api/v1/appointments/` returns all appointments for any authenticated role
- no filtering by current patient or doctor

#### 3. Appointment creation trusts arbitrary patient_id
- patients can create appointment requests for any `patient_id` via API
- route does not validate that `payload.patient_id` belongs to current patient user

#### 4. Visit listing trusts arbitrary patient_id
- any authenticated role can query visits for any patient ID
- no ownership restriction for patients

#### 5. `/patients/me` and `/doctors/me` are not role-scoped
- they depend on `get_current_user`, not role-specific access rules
- wrong-role access returns 404 if no profile exists instead of 403

#### 6. Weak secret defaults
- `JWT_SECRET_KEY` defaults to `change-me-in-production`
- docs and env examples keep placeholder values

#### 7. No rate limiting
- no limiter or throttling is present in this branch

#### 8. No triage/audit persistence
- no server-side audit trail of who ran triage with which patient history

## 11. Current User Flows

### Verified working or mostly working

#### Patient flow
- register/login
- create patient profile
- list doctors
- request appointment
- run triage
- view own visits in UI because selected patient is own profile

#### Doctor flow
- register/login
- create doctor profile
- see all appointments
- approve/reject appointment
- create visit
- import records

#### Admin flow
- register/login
- access both patient and doctor profile forms
- manage all CRM panels from one account

### Partially implemented
- Doctor selection by specialty is implemented as an API route but not wired into frontend UX.
- Triage suggests doctors, but there is no booking shortcut from suggested doctors to appointment creation.
- Patient history affects the reasoner prompt, but there is no UI transparency into what history was used beyond `history_used` boolean.

### Missing or not implemented in this branch
- Triage history page
- Triage detail page
- Persisted triage audit trail
- Readiness/ops dashboard
- True disease ranking or differential list
- EHR import beyond visit-centric JSON/CSV record import

## 12. Development and Deployment Workflow

### Local development workflow today

#### Backend local
- create venv
- install `backend/requirements.txt`
- copy `backend/.env.example` to `.env`
- run `uvicorn app.main:app --reload --port 19001`

#### Frontend local
- `npm install`
- copy `frontend/.env.example` to `.env`
- run `npm run dev`

#### Convenience scripts
- `scripts/dev-backend.ps1`
- `scripts/dev-frontend.ps1`
- `scripts/test-backend.ps1`
- `scripts/test-frontend.ps1`

### Docker workflow today
`docker-compose.yml` defines:
- `backend`
- `frontend`
- `ollama`
- `postgres`

Observations:
- Backend container runs `uvicorn` directly
- Frontend container runs Vite dev server directly
- No migration step in container command
- `depends_on` is service-order only, no health-based readiness
- No service health checks are defined

### Which parts benefit from containerization
Reasonable in Docker:
- Postgres
- Ollama
- backend if team wants consistency

Less necessary in Docker for local dev:
- frontend, because it is a Vite dev server and works well locally without a container

Current state:
- frontend is containerized anyway for convenience, not because it must be

### Env/secrets handling
- Root `.env.example` for Docker Compose
- `backend/.env.example` for backend local env
- `frontend/.env.example` for frontend local env
- Secrets are example placeholders, not managed securely

### Testing / lint / build commands
Verified from CI and local runs:
- Backend tests: `pytest`
- Backend lint: `ruff check app tests`
- Backend formatting: `black --check app tests`
- Frontend lint: `npm run lint`
- Frontend test: `npm run test`
- Frontend build: `npm run build`

### Migration workflow
- Alembic configured in backend
- `alembic upgrade head` is the documented workflow
- `alembic/env.py` overrides DB URL from runtime settings

### Indexing / rebuild workflow for RAG
- `RAG_REBUILD_INDEX=true|false` controls whether embedding index is rebuilt or loaded from cache
- Rebuild happens lazily on first retriever use
- RAG eval CLI exists: `python -m app.rag.eval.evaluator --k 3 --retriever embedding`

## 13. Gaps Between Documentation and Actual Code

### README vs code

#### Verified mismatch: Ollama model defaults
- README/root env/backend env/default config say `llama3:8b-instruct-q4`
- Docker backend default says `llama3.2`
- Docker Ollama service default says `llama3:8b-instruct-q4_K_M`
- This can make the backend request a model that the Ollama container did not pull.

#### Verified mismatch: friend branch triage shape vs prior integrated docs/context
- Friend branch `TriageResponse` contains `simple_reasoning`, `plain_language_explanation`, `recommended_specialty`, `suspected_condition`, `suggested_doctors`
- It does not contain `confidence`, `sources`, `decision`, or triage history/detail models that the broader project context described.

#### Verified mismatch: readiness / history endpoints
- No `/api/v1/health/ready` route in this branch
- No `/api/v1/triage/history`
- No `/api/v1/triage/{id}`

#### Verified mismatch: doctors specialty endpoint
- `/api/v1/doctors/specialty/{specialty}` exists in code
- README does not list it
- Frontend does not use it

#### Verified mismatch: implementation summary vs runtime behavior
- `IMPLEMENTATION_SUMMARY.md` claims the doctor-suggestion enhancement is implemented cleanly
- In reality, friend-added triage code currently breaks when retriever contexts are non-empty

#### Verified mismatch: response demo vs runtime schemas
- `response_output.json` shows an older response shape without the new friend-added fields
- `RESPONSE_FORMAT_DEMO.py` shows sample payloads, but they are examples, not verified runtime contracts

### Project-context-only capabilities not verified on this branch
Compared with the broader project description supplied outside the repo:
- structured reasoning with confidence and decision fields: not present
- explicit grounded source output: not present
- persisted triage sessions and audit logs: not present
- readiness endpoint: not present
- hospital-grade workflow hardening: only partial

## 14. Risks / Weaknesses / Technical Debt

### Verified backend health issues
- `pytest backend/tests -q`: 2 failed, 16 passed, 1 skipped
- `ruff check backend/app backend/tests`: fails
- `black --check backend/app backend/tests`: fails

#### Test failures confirmed
1. `test_api_v1_triage_with_tfidf_has_summary`
   - fails because triage service assumes retrieved objects with `.title` and `.body`
2. `test_triage_reasoner_mode_stub`
   - fails because test expects old stub output format that no longer matches `StubReasoner`

### Verified frontend health
- `npm ci`: succeeded
- `npm run lint`: succeeded
- `npm run test -- --run`: succeeded
- `npm run build`: succeeded

### Architecture drift
- Friend branch appears to have been built on top of an older branch understanding and partially diverges from the more advanced `dev`-branch direction described externally.
- Triage response was simplified toward doctor suggestion, but prior advanced fields are absent.
- New branch logic was added without reconciling the retriever contract.

### Duplicate / stale / noisy files
- `backend/app/api/endpoints/` is deprecated and unused
- `add_doctors.sql` duplicates Alembic seed migration intent
- `RESPONSE_FORMAT_DEMO.py` duplicates response documentation outside schemas/tests
- `verify_*.py`, `quick_test.py`, `test_*.py` at repo root duplicate pytest/API coverage in ad hoc ways
- `response_output.json` is stale and not a reliable contract
- `Untitled-1.ipynb` is an empty notebook artifact

### Fragile integrations
- Model defaults are inconsistent across code, env examples, and Compose
- Triage route is unauthenticated while optionally consuming patient history
- Doctor suggestion depends on specialty substring matching
- Suspected-condition mapping claims to leverage RAG context but does not actually use `rag_context`
- RAG output is not exposed as citations in API responses
- Local and Docker database backends differ by default (SQLite vs Postgres)

### Prototype-only data seeding
- `0002_add_prototype_doctors.py` seeds doctor directory data directly into production migration flow
- This is useful for demos but is not a clean separation between schema migration and demo data seeding

### Environment / tooling fragility
- Tests create an untracked `triage.db` in repo root due SQLite defaults and `DB_AUTO_CREATE=true` in tests
- Frontend and backend local workflows require manual env setup; no unified bootstrap script exists

## 15. What Should Be Preserved in Future Refactor

These parts are worth preserving because they represent real project value rather than noise:

- Monorepo split between `backend/` and `frontend/`
- Versioned API router with legacy `/health` and `/triage` compatibility
- SQLAlchemy ORM + Alembic migration foundation
- Patient/doctor/admin role model
- Patient profile + doctor profile + appointment + visit domain model
- RAG module separation:
  - dataset loader
  - chunking
  - TF-IDF retriever
  - embedding retriever
  - FAISS persistence
  - evaluation CLI
- Patient history provider feeding inference context
- Frontend API client / DTO separation
- Single dashboard flow for graduation demo use
- Docker Compose orchestration of backend + frontend + Ollama + Postgres

## 16. What Requires Clarification Before Rebuild

These are product/architecture decisions that should be clarified before a second implementation prompt asks for deeper changes.

1. Which branch is the real baseline to preserve: this friend branch or the more advanced `dev` line described externally?
2. Should triage remain public, or must it require auth when `patient_id` is used?
3. Is `suggested_doctors` a real product requirement or a branch-local prototype feature?
4. Should triage return only simple language, or should it return structured evidence-rich fields such as confidence and sources?
5. Should seeded prototype doctors live in migrations, SQL scripts, or demo seed tooling?
6. Should records import evolve into true EHR import, or remain visit-only import?
7. Is SQLite still required for local backend, or should Postgres be the single supported backend?
8. Should frontend remain a single-page tab workspace or evolve into routed flows?
9. Is the intended AI output a triage urgency summary, a disease shortlist, a specialty recommendation, or all three?
10. Should the final architecture preserve Ollama-only local models, or support pluggable providers later?

## 17. Recommended Next Prompt Inputs

When writing the second implementation prompt, include the following verified constraints and branch realities:

1. State that the codebase is a monorepo with active FastAPI + React/Vite + SQLAlchemy + Alembic + Ollama + FAISS.
2. State that this friend branch currently includes doctor suggestion and suspected-condition heuristics inside `backend/app/services/triage_service.py`.
3. State that the active retriever interface returns `list[str]` from `retrieve()` and `RetrievedChunk` from `retrieve_chunks()`.
4. Require any triage enhancement to reconcile around that contract instead of inventing a new one silently.
5. State that patient history is actually injected into reasoning today via `PatientContextProvider`.
6. State that triage persistence/history endpoints are absent on this branch and should not be assumed to exist.
7. State that the backend route business logic is still route-heavy outside triage and should only be refactored deliberately.
8. Require preservation of working frontend flows: auth, profiles, appointments, visits, records import, triage.
9. Require cleanup of prototype/deprecated files only with explicit intent, because they may still be useful as migration clues.
10. Require explicit handling of model-name mismatch across Compose/env/backend if deployment logic is touched.
11. Require security review of public triage with patient history, appointment ownership, and visit ownership before feature expansion.
12. Require tests to be updated with any response-shape changes, because current failures show the branch is already drifting from test expectations.

## Important File Map

### Backend entry and routing
- `backend/app/main.py`: FastAPI app factory
- `backend/app/api/router.py`: router composition
- `backend/app/api/routes/triage.py`: triage entrypoint
- `backend/app/api/routes/auth.py`: register/login/me
- `backend/app/api/routes/patients.py`: patient profile endpoints
- `backend/app/api/routes/doctors.py`: doctor profile endpoints + specialty filter
- `backend/app/api/routes/appointments.py`: appointment create/list/status
- `backend/app/api/routes/visits.py`: visit create/list
- `backend/app/api/routes/records_import.py`: import visits from file

### Backend AI path
- `backend/app/services/triage_service.py`: triage orchestration, heuristics, friend-added specialty/doctor logic
- `backend/app/services/patient_context.py`: DB-backed patient history context
- `backend/app/model/reasoner.py`: stub + Ollama reasoning
- `backend/app/patient_symptoms.py`: large manual symptom-to-condition keyword table
- `backend/app/rag/retriever.py`: retriever protocol
- `backend/app/rag/tfidf_retriever.py`: sparse retrieval
- `backend/app/rag/embedding_retriever.py`: dense retrieval
- `backend/app/rag/dataset_loader.py`: corpus normalization
- `backend/app/rag/faiss_store.py`: local vector persistence
- `backend/app/rag/eval/evaluator.py`: offline retrieval evaluation

### Backend persistence
- `backend/app/db/models.py`: ORM entities
- `backend/app/db/session.py`: engine/session
- `backend/alembic/versions/0001_crm_initial.py`: schema baseline
- `backend/alembic/versions/0002_add_prototype_doctors.py`: prototype doctor seed migration

### Frontend execution path
- `frontend/src/pages/HomePage.tsx`: app orchestration
- `frontend/src/api/client.ts`: Axios + token injection
- `frontend/src/api/dto.ts`: contracts
- `frontend/src/components/TriagePanel.tsx`: triage UI result rendering
- `frontend/src/components/AppointmentsPanel.tsx`: appointment UI
- `frontend/src/components/VisitsPanel.tsx`: visit UI
- `frontend/src/components/RecordsImportPanel.tsx`: records import UI

### Prototype / noisy files
- `backend/app/api/endpoints/doctors.py`
- `backend/app/api/endpoints/Untitled-1.ipynb`
- `IMPLEMENTATION_SUMMARY.md`
- `RESPONSE_FORMAT_DEMO.py`
- `response_output.json`
- `add_doctors.sql`
- `quick_test.py`
- `test_api.py`
- `test_conditions.py`
- `test_simple.py`
- `verify_api.py`
- `verify_symptoms.py`

## Unknowns

These are genuine ambiguities that cannot be resolved from code alone on this branch.

- Whether this friend branch is intended to replace the more advanced `dev` branch features or only prototype on top of them.
- Whether prototype doctor seeding is meant for demo data only or intended as a permanent migration.
- Whether triage is intentionally public or simply not yet secured.
- Whether patient and doctor `phone/address` fields from external project documents are postponed or intentionally dropped.
- Whether `suggested_doctors` should be considered part of the long-term API contract.
- Whether `suspected_condition` is expected to be medically meaningful or just a UX hint.
- Whether the future target is CPU-local-only inference or pluggable model providers.

## Assumptions Explicitly Refused

I did not assume the following without code evidence:

- I did not assume triage history/detail endpoints exist on this branch.
- I did not assume a readiness endpoint exists on this branch.
- I did not assume structured triage confidence/source fields exist on this branch.
- I did not assume the frontend uses React Router; it does not.
- I did not assume a background queue or async worker system exists; none was found.
- I did not assume NHS is part of the production knowledge corpus; only Mayo production data was verified.
- I did not assume RAG outputs are cited in responses; they are not.
- I did not assume doctor suggestions are wired end-to-end cleanly; the feature is only partially integrated and currently contributes to a runtime regression.
