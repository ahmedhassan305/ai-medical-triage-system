# AI Medical Triage System - Project Exploration Summary

**Date:** April 20, 2026  
**Project:** ai-medical-triage-system-friend-updates-2026-04-20  
**Framework:** FastAPI (Backend) + React/Vite/TypeScript (Frontend)

---

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Backend Triage Logic](#backend-triage-logic)
3. [Frontend Triage UI](#frontend-triage-ui)
4. [Patient Registration Flow](#patient-registration-flow)
5. [Dashboard/Overview Pages](#dashboardoverview-pages)
6. [Doctor Model & Schema](#doctor-model--schema)
7. [Appointment Booking Flow](#appointment-booking-flow)
8. [Test Files & Coverage](#test-files--coverage)

---

## Architecture Overview

### Project Structure
```
backend/
  ├── app/
  │   ├── api/           # Routes and endpoints
  │   ├── core/          # Configuration and middleware
  │   ├── db/            # Database models and session
  │   ├── model/         # AI reasoner implementations
  │   ├── rag/           # Retrieval-Augmented Generation
  │   ├── schemas/       # Pydantic request/response models
  │   ├── services/      # Business logic
  │   ├── main.py        # FastAPI app factory
  │   └── patient_symptoms.py  # Symptom keyword mappings
  ├── tests/             # Test suite
  ├── alembic/           # Database migrations
  ├── requirements.txt   # Python dependencies
  └── Dockerfile

frontend/
  ├── src/
  │   ├── api/           # API client & DTOs
  │   ├── components/    # React components
  │   ├── pages/         # Page containers
  │   ├── lib/           # Utilities (Egyptian ID parsing, etc.)
  │   ├── App.tsx        # Main app component
  │   └── main.tsx       # Entry point
  ├── package.json
  ├── vite.config.ts
  └── Dockerfile
```

### Key Dependencies
- **FastAPI**: Web framework for the API
- **SQLAlchemy**: ORM for database operations
- **Ollama**: LLM reasoning engine (optional; stub fallback available)
- **React 18**: Frontend UI library
- **TypeScript**: Type-safe frontend
- **Vite**: Fast frontend build tool

### Database
- **PostgreSQL** (Docker compose) or SQLite (local dev)
- Models: User, PatientProfile, DoctorProfile, Appointment, Visit

---

## Backend Triage Logic

### Location
**File:** [backend/app/services/triage_service.py](backend/app/services/triage_service.py)

### Triage Flow (High-Level)

The `triage()` function is the main entry point. It performs:

1. **Access Control Check** → Validates patient profile ownership (if authenticated)
2. **Patient Context Retrieval** → Loads patient history (chronic conditions, past visits) if available
3. **Red Flag Assessment** → Detects emergency keywords and patterns
4. **Heuristic Urgency Detection** → Quick keyword-based triage level classification
5. **RAG Retrieval** → Fetches relevant medical context from knowledge base
6. **Reasoner Invocation** → Calls Ollama LLM or stub fallback for detailed reasoning
7. **Doctor Suggestions** → Retrieves matching specialists from database
8. **Response Building** → Constructs comprehensive TriageResponse

### Urgency Levels & Scoring

**Three-tier system: `low`, `medium`, `high`**

#### HIGH Risk Keywords (Immediate Emergencies)
```python
HIGH_RISK_KEYWORDS = (
    "chest pain", "shortness of breath", "difficulty breathing",
    "stroke", "seizure", "unconscious", "severe bleeding",
    "overdose", "suicidal", "throat closing", "blue lips"
)
```

#### MEDIUM Risk Keywords (Urgent, Same-day)
```python
MEDIUM_RISK_KEYWORDS = (
    "fever", "vomiting", "dehydration", "fracture", "burn",
    "infection", "migraine", "dizziness"
)
```

#### Context-Aware Red Flag Assessment

Function: `_assess_red_flags()`

Implements sophisticated context-aware logic:

| Red Flag Pattern | Urgency | Specialty | Key Actions |
|---|---|---|---|
| **Head Trauma** + (Severe Headache OR Nausea OR Altered Mental Status) | HIGH | Neurology | Emergency ED assessment; don't drive if drowsy |
| **Chest Pain** + **Breathing Distress** | HIGH | Cardiology | Emergency care now; call 911 if crushing/worsening |
| **Stroke Symptoms** (slurred speech, face drooping, weakness) | HIGH | Neurology | Emergency care immediately |
| **Severe Breathing Distress** (not from chest pain) | HIGH | Pulmonology | Urgent care; 911 if blue lips |
| **Severe Bleeding** | HIGH | General | Apply pressure, call 911 |
| **Seizure-like Activity** | HIGH | Neurology | Emergency care; first seizure especially urgent |
| **Suicidal Ideation** | HIGH | Psychiatry | Psychiatric emergency; crisis line now |
| **Severe Allergic Reaction** (throat closing, tongue swelling) | HIGH | Pulmonology | Emergency allergy treatment + 911 |
| **Severe Abdominal Pain** + **Vomiting** | MEDIUM→HIGH | Gastroenterology | Same-day urgent assessment |

### Specialty Detection

Function: `_get_recommended_specialty()`

Maps symptoms to specialties using keyword rules:

```python
SPECIALTY_RULES = {
    "Cardiology": ("heart", "cardiac", "coronary", "chest pain", ...),
    "Pulmonology": ("asthma", "pneumonia", "lung", "breathing", "cough", ...),
    "Gastroenterology": ("stomach", "gastritis", "gerd", "abdominal", ...),
    "Neurology": ("migraine", "stroke", "seizure", "headache", "concussion", ...),
    "Orthopedics": ("fracture", "sprain", "joint", "back pain", "bone", ...),
    "Dermatology": ("rash", "eczema", "skin", "itching", ...),
    "Psychiatry": ("anxiety", "depression", "panic", "mental", ...),
    "Internal Medicine": ("fever", "infection", "flu", "fatigue", ...),
    # ... and more
}
```

### Doctor Suggestions

Function: `_get_suggested_doctors()`

- **Input:** Recommended specialty from triage
- **Query:** Database lookup for DoctorProfile records matching specialty (case-insensitive)
- **Limit:** Default 3 doctors
- **Output:** Returns `list[DoctorSuggestion]` with id, full_name, specialty, clinic, area, city, booking info

### Patient Context Integration

Function: `PatientContextProvider`

When a patient is authenticated and has a linked profile:

1. Retrieves patient chronic conditions
2. Fetches patient visit history (up to most recent)
3. Formats as structured context: `"Relevant history: ..."`
4. Passed to reasoner to consider in assessment

If context is used, `history_used: True` in response.

### Reasoner Implementation

Two modes available:

#### 1. **OllamaReasoner** (Primary)
- **Location:** [backend/app/model/reasoner.py](backend/app/model/reasoner.py)
- **Model:** Uses Ollama + specified LLM (default: `llama3.2`)
- **Process:**
  - Constructs structured prompt with symptom query, context, red flags
  - Sends to Ollama HTTP API
  - Parses JSON response into `StructuredReasoningOutput`
  - Falls back to `StubReasoner` if Ollama unavailable
- **Timeout:** 45 seconds default
- **Output Fields:**
  - `urgency_level`: Final urgency classification
  - `clinical_summary`: Medical explanation
  - `patient_friendly_explanation`: Layman's summary
  - `possible_conditions`: List of suspected conditions with likelihood
  - `recommended_specialty`: Medical specialty
  - `recommended_actions`: Patient-facing action items
  - `red_flags`: Warning signs to monitor

#### 2. **StubReasoner** (Fallback)
- **Mode:** When Ollama unavailable or in testing
- **Process:**
  - Uses heuristic pattern matching
  - Estimates urgency from HIGH/MEDIUM risk keywords
  - Generates condition guesses from symptom keywords
  - Provides generic explanations and actions
- **Deterministic:** No LLM calls, always responds

### Response Schema

**File:** [backend/app/schemas/triage.py](backend/app/schemas/triage.py)

```typescript
TriageResponse {
  triage_level: "low" | "medium" | "high"
  urgency_level: "low" | "medium" | "high"
  urgency_label: string  // e.g., "Emergency"
  urgency_reason: string | null
  summary: string
  clinical_summary: string  // Medical terminology
  simple_reasoning: string  // Simplified terms
  plain_language_explanation: string  // Patient-friendly
  patient_friendly_explanation: string
  actions: list[string]
  recommended_actions: list[string]
  red_flags: list[string]
  recommended_specialty: string | null
  specialty_reason: string | null
  suspected_condition: string | null
  suspected_conditions: list[{
    name: string
    likelihood: "more_likely" | "possible" | "less_likely"
    explanation: string
  }]
  suggested_doctors: list[DoctorSuggestion]
  supporting_references: list[{
    title: string
    source: string
    url: string | null
    snippet: string
  }]
  disclaimer: string
  history_used: boolean
}
```

### Example API Flow

**Request:**
```json
POST /api/v1/triage
{
  "query": "I have severe chest pain and shortness of breath",
  "patient_id": null
}
```

**Response:**
```json
{
  "triage_level": "high",
  "urgency_level": "high",
  "urgency_label": "Emergency - Seek care now",
  "clinical_summary": "Clinical assessment indicates possible acute coronary syndrome or pulmonary embolism requiring immediate evaluation.",
  "recommended_specialty": "Cardiology",
  "red_flags": ["Chest pain with shortness of breath"],
  "suggested_doctors": [
    {
      "id": 1,
      "full_name": "Dr. John Smith",
      "specialty": "Cardiology",
      "clinic": "Heart Care Center"
    }
  ],
  "recommended_actions": [
    "Seek urgent or emergency care now for chest pain with breathing trouble.",
    "Call emergency services if the pain is severe, crushing, or worsening."
  ],
  "history_used": false,
  "disclaimer": "This is not medical advice..."
}
```

---

## Frontend Triage UI

### Main Component: TriagePanel

**File:** [frontend/src/components/TriagePanel.tsx](frontend/src/components/TriagePanel.tsx)

#### Props Structure
```typescript
type TriagePanelProps = {
  loading: boolean
  error: string | null
  result: TriageResponseDto | null
  patientOptions: PatientProfileResponseDto[]
  patientId: number | null
  lockPatientSelection: boolean
  query: string
  onQueryChange: (value: string) => void
  onPatientChange: (value: number | null) => void
  onSubmit: () => void
}
```

#### UI Sections

1. **Input Form** (via TriageForm sub-component)
   - Free-text symptom query (multi-line textarea)
   - Patient selector dropdown (if multiple profiles available)
   - Submit button
   - Loading state

2. **Hero Result Card** (When result available)
   - **Urgency Badge:** Color-coded (low/medium/high)
   - **Urgency Label:** "Emergency" | "Urgent" | "Routine"
   - **Patient-Friendly Explanation:** Plain language summary
   - **Red Flags Section:** Expandable callout with warning signs

3. **Clinical Details Grid**
   - Clinical summary (medical terminology)
   - Recommended specialty

4. **Suspected Conditions Section**
   - Condition name + likelihood badge
   - Individual condition explanation cards
   - Empty state if no conditions detected

5. **Doctor Suggestions** (Right grid column)
   - List of recommended doctors by specialty
   - Shows: Name, Specialty, Clinic
   - Empty state guidance if none matched

6. **Recommended Next Steps** (Right grid column)
   - Bullet list of actions
   - Prioritized by urgency

7. **Supporting Medical References** (Expandable)
   - Source citation cards
   - Reference snippets
   - Links to external sources (if available)

8. **Safety Disclaimer Footer**
   - Medical advice disclaimer

#### CSS Classes & Layout
- `.result-layout`: Main container
- `.result-card`: Individual section cards
- `.result-grid`: 2-column grid for doctors + actions
- `.condition-list`: Container for condition cards
- `.condition-card`: Individual condition with header
- `.badge`: Color-coded urgency/likelihood badges
- `.callout`: Warning signs callout box
- `.list`: Bullet lists for actions/doctors

#### State Management
- Integrates with parent `App.tsx` for API calls
- Updates via callbacks: `onSubmit()`, `onQueryChange()`, `onPatientChange()`

### TriageForm Sub-component

**File:** (Referenced in TriagePanel, likely [frontend/src/components/TriageForm.tsx](frontend/src/components/TriageForm.tsx))

Input form with:
- Symptom textarea
- Patient selector (locked if already authenticated as patient)
- Submit button with loading state

---

## Patient Registration Flow

### Backend: Patient Registration Route

**File:** [backend/app/api/routes/patients.py](backend/app/api/routes/patients.py)

#### Registration Step 1: User Account Creation

**Endpoint:** `POST /api/v1/auth/register`

```json
{
  "email": "patient@example.com",
  "password": "MinimumEightChars",
  "role": "patient"
}
```

**Creates:** User record with role="patient"

---

#### Registration Step 2: Patient Profile Creation/Update

**Endpoint:** `POST /api/v1/patients/me`

**Authentication:** Required (Bearer token)

**Request Payload:** `PatientProfileUpsert`

```typescript
{
  full_name: string  // Required, 1-200 chars
  age: number        // Required, 0-130
  sex: string        // Required, "Male" or "Female"
  national_id?: string | null  // Optional, 14 digits (Egyptian)
  current_governorate?: string | null  // Optional, 120 chars max
  smoker: boolean    // Default: false
  alcoholic: boolean // Default: false
  chronic_conditions: list[string]  // Default: []
}
```

#### Special Processing: Egyptian National ID

If `national_id` provided:

**Function:** `parse_egyptian_national_id()` [backend/app/services/egyptian_national_id.py]

Extracts from 14-digit ID:
- **Date of Birth** (YYMMDD format in first 6 digits)
- **Gender** (7th digit)
- **Governorate Code** (9-10th digits)
- **Inferred Governorate Name** (lookup table)

Automatically populates:
- `date_of_birth` (derived)
- `age` (calculated from DOB)
- `inferred_governorate_code`
- `inferred_governorate`
- Auto-sets `current_governorate` if not provided

**Validation:** Function throws HTTPException (422) if ID format invalid

#### Database Behavior: Upsert

- **First time:** Creates new PatientProfile linked to current_user.id
- **Subsequent calls:** Updates existing profile
- **Uniqueness:** `national_id` is unique constraint (prevents duplicate IDs across profiles)

#### Response: PatientProfileResponse

```typescript
{
  id: number
  user_id: number | null
  full_name: string
  age: number
  sex: string
  national_id: string | null
  current_governorate: string | null
  smoker: boolean
  alcoholic: boolean
  chronic_conditions: list[string]
  date_of_birth: date | null  // Derived from national_id
  inferred_governorate_code: string | null
  inferred_governorate: string | null
  created_at: datetime
  updated_at: datetime
}
```

---

### Frontend: Patient Registration Flow

**File:** [frontend/src/components/ProfilePanel.tsx](frontend/src/components/ProfilePanel.tsx)

#### Registration Form Structure

1. **Form Mode:** Patient profile editing
2. **Fields:**
   - **Full Name** (text input)
   - **Sex** (text input; validated to "Male" or "Female")
   - **Age** (number input)
   - **Egyptian National ID** (14-digit numeric input; optional)
     - On change: Triggers client-side parsing
     - Displays inferred info: DOB, Governorate
     - Shows validation error if invalid format
   - **Current Governorate** (text input)
   - **Smoker** (checkbox)
   - **Alcoholic** (checkbox)
   - **Chronic Conditions** (comma-separated text input)
     - Converted to array on submission

#### Integration with Utility

**File:** [frontend/src/lib/egyptianNationalId.ts](frontend/src/lib/egyptianNationalId.ts)

Client-side parsing function: `parseEgyptianNationalId()`
- Parses national ID locally for UX feedback
- Shows derived DOB and governorate in real-time
- Server validates again on submission

#### Form Submission

```javascript
async submitPatientProfile(event) {
  // Parse chronic conditions from comma-separated string
  const conditions = chronicConditionsInput
    .split(",")
    .map(item => item.trim())
    .filter(Boolean)
  
  await onSavePatient({
    ...patientForm,
    chronic_conditions: conditions
  })
}
```

**Calls:** `POST /api/v1/patients/me`

---

## Dashboard/Overview Pages

### Backend: Overview Metrics

**File:** [backend/app/api/routes/health.py](backend/app/api/routes/health.py) (implied)

Endpoints for fetching dashboard data:
- `GET /api/v1/doctors/` → Count all doctors
- `GET /api/v1/patients/` → Count all patients (doctor/admin only)
- `GET /api/v1/appointments/` → List appointments (filtered by role)
- `GET /api/v1/visits/patient/{patient_id}` → List patient visits

---

### Frontend: OverviewPanel Component

**File:** [frontend/src/components/OverviewPanel.tsx](frontend/src/components/OverviewPanel.tsx)

#### Purpose
Displays system operational status and CRM metrics at a glance.

#### Props
```typescript
type OverviewPanelProps = {
  role: "patient" | "doctor" | "admin"
  patientProfile: PatientProfileResponseDto | null
  doctorProfile: DoctorProfileResponseDto | null
  doctorsCount: number
  patientsCount: number
  appointmentsCount: number
  visitsCount: number
}
```

#### Dashboard Metrics Grid (6 cards)

| Metric | Display | Purpose |
|---|---|---|
| **Role** | PATIENT / DOCTOR / ADMIN | Current user role |
| **Profile Status** | Ready / Needs Setup | Whether profile complete |
| **Appointments** | Count | Total appointments in system |
| **Visits Loaded** | Count | Total visit records |
| **Doctors Indexed** | Count | Registered doctors |
| **Patients Indexed** | Count | Registered patients |

#### Contextual Callout
Shows guidance based on profile readiness:
- ✅ **Ready:** "Profile data is available, so triage can attach patient context..."
- ⚠️ **Needs Setup:** "Create the relevant profile first. Triage still works, but..."

#### CSS Classes
- `.metric-grid`: 6-column grid layout
- `.metric-card`: Individual metric card
- `.callout`: Informational callout box

---

### Frontend: Main App Component (HomePage)

**File:** [frontend/src/pages/HomePage.tsx](frontend/src/pages/HomePage.tsx)

Orchestrates all panels:
- **OverviewPanel** → System status
- **AuthPanel** → Login/Register (conditional)
- **ProfilePanel** → Patient/Doctor profile editing
- **TriagePanel** → Symptom assessment
- **AppointmentsPanel** → Appointment coordination
- **VisitsPanel** → Visit records
- **RecordsImportPanel** → Bulk data import

---

## Doctor Model & Schema

### Database Model

**File:** [backend/app/db/models.py](backend/app/db/models.py)

```python
class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    id: int (primary key)
    user_id: int | None (foreign key → users.id, nullable, unique)
    
    # Core Profile
    full_name: str (1-200 chars)
    specialty: str (1-120 chars)  # e.g., "Cardiology", "Neurology"
    clinic: str (1-200 chars)     # Clinic/hospital name
    
    # Location Information (Optional)
    area: str | None (max 120)    # Neighborhood/area
    city: str | None (max 120)    # City
    
    # External Linking (Optional)
    source_name: str | None (max 120)   # Data source (e.g., "MoH database")
    source_url: str | None (max 500)    # Link to source
    booking_url: str | None (max 500)   # Direct booking link
    
    # Audit
    created_at: datetime (default: now)
    updated_at: datetime (default: now, on update: now)
    
    # Relationships
    user: User | None (back_populates="doctor_profile")
    visits: list[Visit] (back_populates="doctor")
    appointments: list[Appointment] (back_populates="doctor")
```

### Schema: Request/Response

**File:** [backend/app/schemas/doctor.py](backend/app/schemas/doctor.py)

#### DoctorProfileUpsert (Request)
```typescript
{
  full_name: string (1-200 chars)
  specialty: string (1-120 chars)
  clinic: string (1-200 chars)
  area?: string (120 chars max)
  city?: string (120 chars max)
}
```

#### DoctorProfileResponse (Response)
```typescript
{
  id: number
  user_id: number | null
  full_name: string
  specialty: string
  clinic: string
  area: string | null
  city: string | null
  source_name: string | null
  source_url: string | null
  booking_url: string | null
  created_at: datetime
  updated_at: datetime
}
```

#### DoctorSuggestion (Triage Response)
```typescript
{
  id: number
  full_name: string
  specialty: string
  clinic: string
  area: string | null
  city: string | null
  source_name: string | null
  source_url: string | null
  booking_url: string | null
}
```

### API Routes

**File:** [backend/app/api/routes/doctors.py](backend/app/api/routes/doctors.py)

| Endpoint | Method | Auth | Response | Purpose |
|---|---|---|---|---|
| `/api/v1/doctors/` | GET | patient/doctor/admin | list[DoctorProfileResponse] | List all doctors (sorted by name) |
| `/api/v1/doctors/specialty/{specialty}` | GET | patient/doctor/admin | list[DoctorProfileResponse] | Filter doctors by specialty (case-insensitive) |
| `/api/v1/doctors/me` | POST | doctor/admin | DoctorProfileResponse | Create/update own doctor profile (upsert) |
| `/api/v1/doctors/me` | GET | doctor/admin | DoctorProfileResponse | Retrieve own doctor profile |
| `/api/v1/doctors/{doctor_id}` | GET | patient/doctor/admin | DoctorProfileResponse | Get specific doctor by ID |

### Specialty Enumeration

No strict enum; specialty is free-form string. Common specialties (inferred from SPECIALTY_RULES):
- Cardiology
- Pulmonology
- Gastroenterology
- Neurology
- Orthopedics
- Dermatology
- Psychiatry
- Internal Medicine
- Nephrology (kidney)
- Gynecology (women's health)
- Pediatrics (children)

---

## Appointment Booking Flow

### Database Model

**File:** [backend/app/db/models.py](backend/app/db/models.py)

```python
class Appointment(Base):
    __tablename__ = "appointments"

    id: int (primary key)
    patient_id: int (foreign key → patient_profiles.id, cascade delete)
    doctor_id: int (foreign key → doctor_profiles.id, cascade delete)
    
    status: str (default: "requested")
    # Valid values: "requested", "approved", "rejected"
    
    requested_at: datetime (default: now)
    
    # Optional fields (implied from schema)
    reason: str (appointment reason)
    notes: str | null (additional context)
    scheduled_for: datetime | null (requested appointment time)
    
    # Relationships
    patient: PatientProfile (back_populates="appointments")
    doctor: DoctorProfile (back_populates="appointments")
```

### API Routes

**File:** [backend/app/api/routes/appointments.py](backend/app/api/routes/appointments.py)

#### 1. Create Appointment

**Endpoint:** `POST /api/v1/appointments/`

**Auth:** patient, admin

**Request:** `AppointmentCreate`
```typescript
{
  patient_id: number
  doctor_id: number
  reason: string (1+ chars)
  notes?: string | null
  scheduled_for?: datetime | null
}
```

**Business Logic:**
- Validates patient profile exists (404 if not)
- Validates doctor profile exists (404 if not)
- **Access Control (Patients):**
  - Can only book for their own patient profile
  - Admins can book for any patient
- Creates appointment with `status: "requested"`

**Response:** `AppointmentResponse` (201)

---

#### 2. Update Appointment Status

**Endpoint:** `PATCH /api/v1/appointments/{appointment_id}/status`

**Auth:** doctor, admin

**Request:** `AppointmentStatusUpdate`
```typescript
{
  status: "approved" | "rejected"
  notes?: string | null
}
```

**Business Logic:**
- Finds appointment by ID (404 if not found)
- **Access Control:**
  - Doctor can only update their own appointments
  - Admin can update any appointment
- Updates status and optional notes

**Response:** `AppointmentResponse` (200)

---

#### 3. List Appointments

**Endpoint:** `GET /api/v1/appointments/`

**Auth:** patient, doctor, admin

**Response:** `list[AppointmentResponse]`

**Filtering by Role:**
- **Patient:** Returns only appointments where `patient_id = own_patient_profile.id`
- **Doctor:** Returns only appointments where `doctor_id = own_doctor_profile.id`
- **Admin:** Returns all appointments

**Ordering:** By `requested_at DESC` (newest first)

---

### Frontend: AppointmentsPanel

**File:** [frontend/src/components/AppointmentsPanel.tsx](frontend/src/components/AppointmentsPanel.tsx)

#### Props
```typescript
type AppointmentsPanelProps = {
  role: "patient" | "doctor" | "admin"
  doctors: DoctorProfileResponseDto[]
  patients: PatientProfileResponseDto[]
  currentPatientId: number | null
  appointments: AppointmentResponseDto[]
  loading: boolean
  error: string | null
  onCreate: (payload: AppointmentCreatePayload) => Promise<void>
  onUpdateStatus: (id: number, payload: StatusUpdate) => Promise<void>
}
```

#### Features

1. **Appointment Creation Form** (Patients & Admins only)
   - **Doctor Selector** (dropdown)
   - **Patient Selector** (admin only; locked for regular patients to their own profile)
   - **Reason** (textarea)
   - **Requested Time** (datetime-local input, optional)
   - **Notes** (text input, optional)
   - **Submit Button** (disabled if missing required fields)

2. **Appointment List**
   - **Status Badge** (color-coded by status)
   - **Patient Name** (lookup from list)
   - **Doctor Name** (lookup from list)
   - **Reason** (displayed)
   - **Requested Time** (formatted as locale string)
   - **Scheduled Time** (if set)

3. **Doctor View: Status Update Cards**
   - Displays incoming appointment requests
   - **Approve** / **Reject** buttons
   - Optional notes field for response

4. **Empty State**
   - "No appointments yet." message when list is empty

#### CSS Classes
- `.entity-card`: Appointment card container
- `.entity-card__header`: Header section with title and metadata
- `.badge`: Status badge (color varies by status)
- `badge--status-{status}`: Status-specific styling

---

## Test Files & Coverage

### Test Suite Location

**Directory:** [backend/tests/](backend/tests/)

### Test Files

#### 1. **test_triage.py** (Triage Unit Tests)

**File:** [backend/tests/test_triage.py](backend/tests/test_triage.py)

**Test Cases:**

1. `test_triage_v1_happy_path()`
   - **Scenario:** Parametrized tests for three symptom queries
   - **Cases:**
     - Low: "I need guidance for mild headache after work." → `triage_level: "low"`
     - Medium: "I have fever and nausea since last night." → `triage_level: "medium"`
     - High: "I have chest pain and shortness of breath." → `triage_level: "high"`
   - **Assertions:** Response structure, urgency level correctness, presence of fields

2. `test_triage_invalid_body()`
   - **Scenario:** Empty query string
   - **Expected:** 422 validation error
   - **Validates:** Input validation works

3. `test_triage_legacy_route_compatibility()`
   - **Scenario:** POST to old `/triage` endpoint (non-versioned)
   - **Expected:** 200 response, functional triage
   - **Validates:** Backward compatibility

4. `test_triage_with_patient_history_flag()`
   - **Scenario:** 
     - Patient registers with chronic condition (hypertension)
     - Visit record added to database
     - Triage called with `patient_id` and query "chest pain"
   - **Validates:** 
     - `history_used: true` in response
     - Patient context considered in reasoning

---

#### 2. **test_triage_integration.py** (Integration Tests)

**File:** [backend/tests/test_triage_integration.py](backend/tests/test_triage_integration.py)

**Test Cases:**

1. `test_triage_reasoner_mode_stub()`
   - **Scenario:** Tests triage with stub reasoner (no LLM)
   - **Config:** 
     - `REASONER_MODE=stub`
     - `RAG_RETRIEVER=stub`
   - **Assertions:**
     - 200 response
     - Stub generates valid explanation
     - Urgency level matches heuristic
     - Conditions list is valid

2. `test_triage_reasoner_mode_ollama_when_available()`
   - **Scenario:** Tests triage with Ollama LLM (if available)
   - **Prerequisites:**
     - Ollama server reachable at `OLLAMA_HOST`
     - Model (default: `llama3.2`) available
   - **Config:**
     - `REASONER_MODE=ollama`
     - Ollama connection details
   - **Assertions:**
     - 200 response if Ollama available
     - Skips if Ollama unavailable (pytest.skip)
   - **Query:** "I have chest pain with cough"

---

### Related Test Files

#### 3. **test_auth.py**
- User registration and login
- Token generation and validation
- Role-based access control

#### 4. **test_patient_identity_and_security.py**
- Egyptian national ID parsing
- Patient profile access control
- Profile linkage validation

#### 5. **test_rag_retriever.py**
- Retrieval-Augmented Generation tests
- Document embedding and retrieval

#### 6. **test_health.py**
- Health check endpoints
- API availability validation

---

## Key Implementation Patterns

### 1. **Role-Based Access Control (RBAC)**

**Middleware:** `require_roles("patient", "doctor", "admin")`

Examples:
- Patients can only view/update their own profile
- Doctors can update their own appointments
- Admins can access all data

### 2. **Patient Context Awareness**

Triage leverages patient history when available:
- Chronic conditions
- Past visit notes
- Doctor recommendations

### 3. **Dual-Mode Reasoning**

Ollama (LLM) + Stub (heuristic) fallback ensures:
- Better quality with LLM when available
- Graceful degradation without LLM
- Deterministic behavior in testing

### 4. **Red Flag Routing**

Sophisticated pattern matching for emergencies:
- Detects multi-symptom combinations (e.g., head trauma + headache + vomiting)
- Routes to appropriate specialty
- Provides emergency-specific actions

### 5. **Frontend-Backend Type Alignment**

- Backend Pydantic schemas ↔ Frontend TypeScript DTOs
- Consistent request/response structures
- Type safety across layers

---

## Configuration & Environment

### Key Environment Variables

**Backend (.env):**
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/triage_db

# Ollama (AI Reasoning)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
REASONER_MODE=ollama  # or "stub"

# RAG (Knowledge Retrieval)
RAG_RETRIEVER=tfidf  # or "stub", "embedding"

# API
CORS_ORIGINS=["http://localhost:5173"]
LOG_LEVEL=info
```

**Frontend (.env):**
```bash
VITE_API_BASE_URL=http://localhost:19001
```

---

## Deployment Notes

- **Backend API:** Runs on port 19001
- **Frontend Dev:** Runs on port 5173 (Vite)
- **Frontend Production:** Built to static files (dist/)
- **Database:** PostgreSQL in Docker (docker-compose.yml)
- **Ollama:** Optional; tests skip if unavailable

---

## Summary Table: Key Files Reference

| Area | File | Purpose |
|---|---|---|
| **Triage Logic** | `app/services/triage_service.py` | Main triage algorithm |
| **Reasoner** | `app/model/reasoner.py` | AI reasoning (Ollama/Stub) |
| **Triage Schema** | `app/schemas/triage.py` | Request/response models |
| **Patient Routes** | `app/api/routes/patients.py` | Patient registration & profile |
| **Doctor Routes** | `app/api/routes/doctors.py` | Doctor profile & specialty lookup |
| **Appointment Routes** | `app/api/routes/appointments.py` | Booking & status management |
| **TriagePanel** | `frontend/src/components/TriagePanel.tsx` | Triage UI |
| **ProfilePanel** | `frontend/src/components/ProfilePanel.tsx` | Patient/doctor profiles |
| **OverviewPanel** | `frontend/src/components/OverviewPanel.tsx` | Dashboard metrics |
| **AppointmentsPanel** | `frontend/src/components/AppointmentsPanel.tsx` | Booking UI |
| **Triage Tests** | `backend/tests/test_triage.py` | Unit tests |
| **Integration Tests** | `backend/tests/test_triage_integration.py` | Integration & LLM tests |
| **DB Models** | `app/db/models.py` | SQLAlchemy ORM models |
| **Database** | `app/db/session.py` | DB session & initialization |

---

## Next Steps & Observations

1. **Doctor Seeding:** Database needs doctors to be populated for suggestions to work
2. **Appointment Status:** Currently supports "requested", "approved", "rejected" states
3. **Visit Records:** Separate entity for doctor-recorded visit notes and diagnoses
4. **RAG Integration:** Knowledge base for supporting references (embeds or TF-IDF)
5. **Frontend Completion:** RecordsImportPanel and VisitsPanel components present but unexplored
6. **Testing:** Good coverage of triage paths; appointment flow could use more tests

