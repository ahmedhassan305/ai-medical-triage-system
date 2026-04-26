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

## Recent Improvements (Phase 5+)

### 🏥 Enhanced Medical Triage Quality
- **Red-flag symptom detection**: Head trauma + severe headache + vomiting now correctly returns HIGH urgency with Neurology recommendation (was incorrectly LOW urgency with Gastroenterology)
- **Context-aware specialty mapping**: GI conditions are penalized (-4.2) when a Neurology red-flag is present, preventing mismatched recommendations
- **Evidence weighting**: Keyword evidence now provides +3.2 score boost; red-flag conditions weighted at 6.8 (increased from 5.2)
- **High urgency floor**: RED-FLAG conditions never downgrade from HIGH urgency; floor is non-negotiable

### 👤 Patient Registration & Profile
- **National ID requirement**: Patients must provide a 14-digit Egyptian national ID during registration
- **Automatic data extraction**: National ID automatically derives date of birth and governorate
- **Gender standardization**: Dropdown with only "Male" and "Female" options (enforced both frontend and backend)

### 🎯 Role-Specific Dashboards
- **Patient Overview**: Upcoming appointments, pending requests, last visit summary, recommended actions
- **Doctor Overview**: Confirmed appointments (next 3), pending patient requests table, patient load metrics
- **Admin Overview**: System metrics (total patients/doctors/appointments), appointment status breakdown by state, specialty coverage table

### 📅 Appointment Booking Flow
- **Direct Reserve from Triage**: Each recommended doctor card includes "Reserve Appointment" button
- **Pre-filled Booking**: Clicking Reserve pre-fills appointment form with doctor ID and triage reason
- **Status Workflow**: Appointments follow requested → approved/rejected → completed lifecycle
- **Admin Control**: Admins can approve/reject pending appointments and schedule confirmations
- **Detail Toggle**: "View details" button on admin appointments shows/hides request details and notes

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

## Doctor directory seed data

Canonical doctor seed file:
- `scripts/seed_doctors.py` - Contains 14 real Egyptian/Alexandrian doctors with full profiles

Import command:
```powershell
.\backend\.venv\Scripts\python scripts\seed_doctors.py
```

What it does:
- Imports a curated Egyptian doctor dataset with real names, specialties, and clinic information
- Current seed contains 14 Alexandria-based doctors across multiple specialties:
  - Cardiology (2), Neurology (2), Pulmonology (2), Gastroenterology (2), Orthopedics (2), Internal Medicine (2), Dermatology (1), Psychiatry (1)
- Stores provenance on each doctor:
  - `full_name`, `specialty`, `clinic`, `area`, `city`
  - Source information for verification
- Makes doctors immediately available for patient recommendations
- Enables "Reserve Appointment" button to suggest real doctors

Doctor data can be extended by adding more entries to `seed_doctors.py` with proper Egyptian/regional context.

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

## Testing

### Running tests

Backend tests use pytest:
```powershell
cd backend
.\.venv\Scripts\activate
pytest tests/ -v
```

Test coverage includes:
- `test_triage_prioritization.py`: Red-flag detection, context penalties, specialty mapping
  - Head trauma + severe headache + vomiting → HIGH urgency with Neurology (not LOW with Gastroenterology)
  - Chest pain + shortness of breath → HIGH urgency with Cardiology
  - Stroke symptoms → HIGH urgency with Neurology
  - Context penalty prevents GI conditions from dominating head injury scenarios
- `test_patient_registration.py`: National ID requirement, gender validation, profile auto-population
  - National ID is required for patient signup
  - Gender must be exactly "Male" or "Female" (dropdown enforced)
  - Date of birth and governorate auto-derived from national ID
- `test_overview.py`: Role-specific dashboard rendering
  - Patients see upcoming appointments and pending requests
  - Doctors see confirmed appointments and pending patient requests
  - Admins see system metrics and specialty coverage
  - Data properly scoped by user role
- `test_appointments.py`: Booking workflow, pre-fill, admin approval
  - Patients can reserve appointments with pre-filled doctor and reason from triage
  - Admins can approve, reject, and view appointment details
  - Appointment status follows requested → approved → completed workflow

Run specific test file:
```powershell
pytest tests/test_triage_prioritization.py -v
```

Run test with keyword match:
```powershell
pytest tests/ -k "head_trauma" -v
```

## Migration Guide: Phases 5+ Improvements

### For Existing Installations

If you have an existing installation from before these changes, follow these steps:

#### 1. Database Schema Update
The National ID and gender enhancements require schema updates:
```powershell
cd backend
.\.venv\Scripts\activate
alembic upgrade head
```

#### 2. Seed New Doctor Data
Replace the old doctor data with the new Egyptian doctors:
```powershell
cd ..
.\backend\.venv\Scripts\python scripts\seed_doctors.py
```

#### 3. Reset Patient Data (Optional but Recommended)
Clear out test data and recreate valid patient profiles:
```powershell
.\backend\.venv\Scripts\python scripts\reset_local_project_data.py
```

#### 4. Reinstall Frontend Dependencies
Frontend components have been updated for the new workflow:
```powershell
cd frontend
npm install
```

### Breaking Changes
- **Patient Registration API**: Now requires `full_name`, `national_id`, and `sex` fields for patient role
- **Gender Validation**: `sex` field only accepts "Male" or "Female" (was previously free-text)
- **Triage Response**: Includes new `red_flags`, `urgency_label`, and enhanced `recommended_specialty` logic
- **Appointment Workflow**: Appointments now start in "requested" status and require admin approval before scheduling

### Behavioral Changes
- **Red-flag Triage**: Head trauma + severe symptoms now correctly escalates to HIGH urgency with Neurology (was previously LOW with Gastroenterology)
- **Admin Appointments Tab**: "View details" button now toggles detail visibility (was always expanded)
- **Overview Pages**: Now show role-specific information instead of generic metrics
- **Doctor Recommendations**: Limited to 14 seeded Alexandria doctors (can be extended in `seed_doctors.py`)

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
