#!/usr/bin/env python3
from __future__ import annotations

import os
import random
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

project_root = Path(__file__).resolve().parent.parent
backend_dir = project_root / "backend"
os.chdir(backend_dir)
sys.path.insert(0, str(backend_dir))

from app.core.security import get_password_hash  # noqa: E402
from app.db.models import (  # noqa: E402
    Appointment,
    DoctorProfile,
    PatientProfile,
    User,
    Visit,
)
from app.db.session import create_all, engine  # noqa: E402
from app.services.doctor_seed_importer import (  # noqa: E402
    import_seed_records,
    load_seed_records,
)
from app.services.egyptian_national_id import (  # noqa: E402
    calculate_age,
    parse_egyptian_national_id,
)

SEED_PATH = backend_dir / "data" / "doctors" / "alexandria_public_directory_seed.json"
RNG = random.Random(20260421)
NOW = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

ADMIN_CREDENTIALS = ("admin.ops@aimts-eg.com", "AdminPass123!")
DOCTOR_PASSWORD = "DoctorPass123!"
PATIENT_PASSWORD = "PatientPass123!"


PATIENT_NAME_POOL: list[tuple[str, str]] = [
    ("Ahmed Abdelrahman", "Male"),
    ("Mariam Hassan", "Female"),
    ("Omar Salah", "Male"),
    ("Nourhan Mostafa", "Female"),
    ("Youssef Adel", "Male"),
    ("Salma Tarek", "Female"),
    ("Karim Samir", "Male"),
    ("Aya Mohamed", "Female"),
    ("Mahmoud Fathy", "Male"),
    ("Rehab Elsayed", "Female"),
    ("Mostafa Wael", "Male"),
    ("Fatma Hossam", "Female"),
    ("Amr Nabil", "Male"),
    ("Heba Ashraf", "Female"),
    ("Khaled Emad", "Male"),
    ("Mona Reda", "Female"),
    ("Sherif Gamal", "Male"),
    ("Rana Hany", "Female"),
    ("Wael Ibrahim", "Male"),
    ("Dina Magdy", "Female"),
    ("Tamer Yassin", "Male"),
    ("Nadine Fares", "Female"),
    ("Mohamed Saad", "Male"),
    ("Laila Ezz", "Female"),
    ("Hossam Anwar", "Male"),
    ("Yomna Atef", "Female"),
    ("Bassem Khalil", "Male"),
    ("Doaa Essam", "Female"),
    ("Islam Ragab", "Male"),
    ("Riham Nasser", "Female"),
    ("Sameh Fawzy", "Male"),
    ("Nour Ali", "Female"),
    ("Ali Mahmoud", "Male"),
    ("Passant Adel", "Female"),
    ("Hany Shaker", "Male"),
    ("Sahar Hamdy", "Female"),
]

GOVERNORATE_POOL = [
    ("02", "Alexandria"),
    ("01", "Cairo"),
    ("21", "Giza"),
    ("18", "Beheira"),
    ("12", "Dakahlia"),
    ("16", "Gharbia"),
    ("13", "Sharqia"),
]

CHRONIC_CONDITIONS = [
    [],
    ["Hypertension"],
    ["Type 2 diabetes"],
    ["Asthma"],
    ["Irritable bowel syndrome"],
    ["Migraine"],
    ["Hypothyroidism"],
    ["Hypertension", "Type 2 diabetes"],
]


SPECIALTY_TEMPLATES = {
    "Cardiology": [
        {
            "reason": "Episodes of chest tightness after climbing stairs",
            "symptoms": (
                "Intermittent chest tightness, shortness of breath on exertion, "
                "light sweating."
            ),
            "diagnosis": "Stable angina workup",
            "notes": (
                "ECG reviewed. Risk-factor modification and stress testing were "
                "advised."
            ),
            "prescriptions": "Aspirin, beta blocker review, lipid profile follow-up.",
        },
        {
            "reason": "Blood pressure follow-up and dizziness review",
            "symptoms": "Elevated home blood pressure readings with brief dizziness.",
            "diagnosis": "Hypertension follow-up",
            "notes": "Medication adherence reviewed and low-salt diet reinforced.",
            "prescriptions": "Continue antihypertensive therapy and daily BP log.",
        },
    ],
    "Neurology": [
        {
            "reason": "Severe migraine review after repeated attacks",
            "symptoms": "Pulsating headache, light sensitivity, nausea during attacks.",
            "diagnosis": "Migraine without aura",
            "notes": "Trigger diary discussed with the patient.",
            "prescriptions": "Abortive migraine therapy and hydration guidance.",
        },
        {
            "reason": "Numbness and tingling in the left hand",
            "symptoms": "Intermittent tingling in the left hand with neck discomfort.",
            "diagnosis": "Cervical radiculopathy suspected",
            "notes": "Neurologic exam stable, MRI recommended if symptoms progress.",
            "prescriptions": "Short NSAID course and posture modification.",
        },
    ],
    "Neurosurgery": [
        {
            "reason": "Persistent lower back pain radiating to the leg",
            "symptoms": (
                "Lower back pain radiating to the right leg with prolonged sitting."
            ),
            "diagnosis": "Lumbar disc prolapse review",
            "notes": "No motor deficit on exam, conservative management reviewed.",
            "prescriptions": "Pain control and physiotherapy referral.",
        },
    ],
    "Internal Medicine": [
        {
            "reason": "Fatigue and recurrent low-grade fever",
            "symptoms": (
                "General fatigue, reduced appetite, intermittent low-grade fever."
            ),
            "diagnosis": "Viral syndrome follow-up",
            "notes": "CBC and inflammatory markers requested if symptoms persist.",
            "prescriptions": "Hydration, rest, and paracetamol as needed.",
        },
        {
            "reason": "Diabetes review with medication adjustment",
            "symptoms": "Polyuria improved, fasting sugar still above target.",
            "diagnosis": "Type 2 diabetes follow-up",
            "notes": "Diet and medication timing were reviewed.",
            "prescriptions": "Oral hypoglycemic adjustment and glucose log.",
        },
    ],
    "Gastroenterology": [
        {
            "reason": "Upper abdominal burning after meals",
            "symptoms": "Epigastric burning, bloating, sour taste after heavy meals.",
            "diagnosis": "Gastroesophageal reflux disease",
            "notes": "Meal timing and trigger foods discussed.",
            "prescriptions": "PPI trial and reflux precautions.",
        },
        {
            "reason": "Abdominal cramps and bowel pattern changes",
            "symptoms": (
                "Abdominal cramps with alternating constipation and loose stool."
            ),
            "diagnosis": "Irritable bowel syndrome",
            "notes": "Red-flag symptoms were screened and denied.",
            "prescriptions": "Dietary fiber plan and antispasmodic as needed.",
        },
    ],
    "Dermatology": [
        {
            "reason": "Itchy rash on forearms and neck",
            "symptoms": "Pruritic erythematous rash worsened by heat and sweating.",
            "diagnosis": "Eczema flare",
            "notes": "Skin hydration routine explained.",
            "prescriptions": "Topical steroid course and emollients.",
        },
    ],
    "Psychiatry": [
        {
            "reason": "Sleep disturbance with persistent anxiety",
            "symptoms": "Difficulty sleeping, racing thoughts, reduced concentration.",
            "diagnosis": "Generalized anxiety symptoms",
            "notes": "Sleep hygiene and therapy referral discussed.",
            "prescriptions": "Short-term anxiolytic plan pending psychotherapy review.",
        },
    ],
    "Ophthalmology": [
        {
            "reason": "Blurred vision and dry eyes after screen use",
            "symptoms": "Eye strain, dryness, intermittent blurred near vision.",
            "diagnosis": "Dry eye syndrome",
            "notes": "Screen breaks and lubricating drops advised.",
            "prescriptions": "Artificial tears and follow-up visual acuity testing.",
        },
    ],
    "Orthopedics": [
        {
            "reason": "Knee pain after twisting injury",
            "symptoms": (
                "Right knee pain, swelling after sports injury, painful stairs."
            ),
            "diagnosis": "Meniscal strain suspected",
            "notes": "Weight-bearing tolerated, MRI only if symptoms persist.",
            "prescriptions": "Brace, ice, and NSAID course.",
        },
    ],
    "ENT": [
        {
            "reason": "Sore throat and sinus pressure",
            "symptoms": "Blocked nose, facial pressure, sore throat, low fever.",
            "diagnosis": "Acute rhinosinusitis",
            "notes": "Hydration and saline irrigation advised.",
            "prescriptions": (
                "Analgesia, saline rinse, delayed antibiotic plan if worse."
            ),
        },
    ],
    "Pediatrics": [
        {
            "reason": "Fever and cough in a school-age child",
            "symptoms": "Two days of cough, low-grade fever, reduced appetite.",
            "diagnosis": "Upper respiratory tract infection",
            "notes": "Warning signs for breathing difficulty reviewed with family.",
            "prescriptions": "Supportive care and fluids.",
        },
    ],
    "Family Medicine": [
        {
            "reason": "General health review with fatigue and stress",
            "symptoms": "Fatigue, irregular meals, tension headaches during work days.",
            "diagnosis": "Lifestyle-related fatigue",
            "notes": "Sleep, hydration, and exercise plan reviewed.",
            "prescriptions": "Lifestyle plan and routine lab work.",
        },
    ],
}

SPECIALTY_WEIGHTS = {
    "Internal Medicine": 13,
    "Cardiology": 8,
    "Neurology": 8,
    "Gastroenterology": 8,
    "Orthopedics": 8,
    "Dermatology": 6,
    "ENT": 6,
    "Pediatrics": 6,
    "Family Medicine": 6,
    "Ophthalmology": 5,
    "Psychiatry": 4,
    "Neurosurgery": 3,
}


@dataclass(frozen=True)
class SeededCredentials:
    role: str
    email: str
    password: str
    label: str


def build_national_id(birth_date: date, governorate_code: str, serial: int) -> str:
    century_digit = "3" if birth_date.year >= 2000 else "2"
    return (
        f"{century_digit}"
        f"{birth_date.year % 100:02d}"
        f"{birth_date.month:02d}"
        f"{birth_date.day:02d}"
        f"{governorate_code}"
        f"{serial:05d}"
    )


def create_user(db: Session, *, email: str, password: str, role: str) -> User:
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        role=role,
    )
    db.add(user)
    db.flush()
    return user


def build_patient_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    serial = 10001
    for full_name, sex in PATIENT_NAME_POOL:
        year = RNG.randint(1968, 2006)
        month = RNG.randint(1, 12)
        day = RNG.randint(1, 28)
        birth_date = date(year, month, day)
        governorate_code, governorate_name = RNG.choice(GOVERNORATE_POOL)
        national_id = build_national_id(birth_date, governorate_code, serial)
        serial += RNG.randint(7, 31)
        current_governorate = (
            governorate_name if RNG.random() < 0.78 else RNG.choice(GOVERNORATE_POOL)[1]
        )
        records.append(
            {
                "full_name": full_name,
                "sex": sex,
                "birth_date": birth_date,
                "national_id": national_id,
                "current_governorate": current_governorate,
                "smoker": sex == "Male" and RNG.random() < 0.28,
                "alcoholic": False,
                "chronic_conditions": RNG.choice(CHRONIC_CONDITIONS),
            }
        )
    return records


def delete_existing_data(db: Session) -> None:
    db.query(Appointment).delete(synchronize_session=False)
    db.query(Visit).delete(synchronize_session=False)
    db.query(DoctorProfile).delete(synchronize_session=False)
    db.query(PatientProfile).delete(synchronize_session=False)
    db.query(User).delete(synchronize_session=False)
    db.commit()


def choose_doctor_by_specialty(
    db: Session, specialty: str, *, exclude_ids: set[int] | None = None
) -> DoctorProfile:
    query = db.query(DoctorProfile).filter(DoctorProfile.specialty == specialty)
    doctors = query.order_by(DoctorProfile.full_name.asc()).all()
    filtered = [
        doctor
        for doctor in doctors
        if exclude_ids is None or doctor.id not in exclude_ids
    ]
    if not filtered:
        raise RuntimeError(f"No seeded doctor available for specialty: {specialty}")
    return RNG.choice(filtered)


def seed_users_and_linked_profiles(db: Session) -> list[SeededCredentials]:
    credentials: list[SeededCredentials] = []

    admin_user = create_user(
        db,
        email=ADMIN_CREDENTIALS[0],
        password=ADMIN_CREDENTIALS[1],
        role="admin",
    )
    credentials.append(
        SeededCredentials(
            role="admin",
            email=admin_user.email,
            password=ADMIN_CREDENTIALS[1],
            label="Primary admin workspace",
        )
    )

    linked_specialties = [
        "Internal Medicine",
        "Cardiology",
        "Neurology",
        "Pediatrics",
        "Orthopedics",
        "Dermatology",
    ]
    taken_doctor_ids: set[int] = set()
    for specialty in linked_specialties:
        doctor_profile = choose_doctor_by_specialty(
            db, specialty, exclude_ids=taken_doctor_ids
        )
        taken_doctor_ids.add(doctor_profile.id)
        slug = specialty.lower().replace(" ", ".")
        doctor_user = create_user(
            db,
            email=f"doctor.{slug}@aimts-eg.com",
            password=DOCTOR_PASSWORD,
            role="doctor",
        )
        doctor_profile.user_id = doctor_user.id
        credentials.append(
            SeededCredentials(
                role="doctor",
                email=doctor_user.email,
                password=DOCTOR_PASSWORD,
                label=f"{doctor_profile.full_name} · {doctor_profile.specialty}",
            )
        )

    patient_records = build_patient_records()
    for index, patient_record in enumerate(patient_records):
        national_id_info = parse_egyptian_national_id(
            str(patient_record["national_id"])
        )
        profile = PatientProfile(
            user_id=None,
            full_name=str(patient_record["full_name"]),
            age=calculate_age(national_id_info.date_of_birth),
            sex=str(patient_record["sex"]),
            national_id=national_id_info.national_id,
            date_of_birth=national_id_info.date_of_birth,
            inferred_governorate_code=national_id_info.inferred_governorate_code,
            inferred_governorate=national_id_info.inferred_governorate,
            current_governorate=str(patient_record["current_governorate"]),
            smoker=bool(patient_record["smoker"]),
            alcoholic=bool(patient_record["alcoholic"]),
            chronic_conditions=list(patient_record["chronic_conditions"]),
        )
        db.add(profile)
        db.flush()

        if index < 6:
            slug = str(patient_record["full_name"]).lower().replace(" ", ".")
            patient_user = create_user(
                db,
                email=f"patient.{slug}@aimts-eg.com",
                password=PATIENT_PASSWORD,
                role="patient",
            )
            profile.user_id = patient_user.id
            credentials.append(
                SeededCredentials(
                    role="patient",
                    email=patient_user.email,
                    password=PATIENT_PASSWORD,
                    label=profile.full_name,
                )
            )

    db.commit()
    return credentials


def seed_appointments_and_visits(db: Session) -> tuple[int, int]:
    doctors = db.query(DoctorProfile).order_by(DoctorProfile.id.asc()).all()
    patients = db.query(PatientProfile).order_by(PatientProfile.id.asc()).all()
    specialty_doctors: dict[str, list[DoctorProfile]] = {}
    for doctor in doctors:
        specialty_doctors.setdefault(doctor.specialty, []).append(doctor)

    specialty_population = [
        specialty
        for specialty, weight in SPECIALTY_WEIGHTS.items()
        for _ in range(weight)
        if specialty in specialty_doctors
    ]

    completed_count = 0
    appointment_count = 0
    visit_count = 0

    total_past_appointments = 58
    total_future_appointments = 18

    for _ in range(total_past_appointments):
        specialty = RNG.choice(specialty_population)
        template = RNG.choice(SPECIALTY_TEMPLATES[specialty])
        doctor = RNG.choice(specialty_doctors[specialty])
        patient = RNG.choice(patients)
        scheduled_at = NOW - timedelta(
            days=RNG.randint(4, 210),
            hours=RNG.randint(0, 7),
        )

        status = RNG.choices(
            ["completed", "approved", "rejected"],
            weights=[74, 16, 10],
            k=1,
        )[0]
        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            status=status,
            requested_at=scheduled_at - timedelta(days=RNG.randint(1, 12)),
            scheduled_for=scheduled_at,
            reason=template["reason"],
            notes=RNG.choice(
                [
                    "Previous records reviewed before the visit.",
                    "Family asked for a follow-up plan and home monitoring advice.",
                    "Appointment created after symptoms persisted for several days.",
                    "Booked after triage suggested specialty follow-up.",
                ]
            ),
        )
        db.add(appointment)
        db.flush()
        appointment_count += 1

        if status == "completed":
            completed_count += 1
            visit = Visit(
                patient_id=patient.id,
                doctor_id=doctor.id,
                symptoms=template["symptoms"],
                diagnosis=template["diagnosis"],
                notes=template["notes"],
                prescriptions=template["prescriptions"],
                vitals={
                    "temperature": f"{RNG.uniform(36.7, 38.4):.1f}",
                    "pulse": str(RNG.randint(72, 108)),
                    "spo2": str(RNG.randint(95, 99)),
                },
                created_at=scheduled_at + timedelta(minutes=RNG.randint(25, 110)),
            )
            db.add(visit)
            visit_count += 1

    future_statuses = ["requested", "approved", "approved", "requested", "approved"]
    for _ in range(total_future_appointments):
        specialty = RNG.choice(specialty_population)
        template = RNG.choice(SPECIALTY_TEMPLATES[specialty])
        doctor = RNG.choice(specialty_doctors[specialty])
        patient = RNG.choice(patients)
        scheduled_at = NOW + timedelta(
            days=RNG.randint(1, 40),
            hours=RNG.randint(1, 6),
        )
        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            status=RNG.choice(future_statuses),
            requested_at=scheduled_at - timedelta(days=RNG.randint(1, 9)),
            scheduled_for=scheduled_at,
            reason=template["reason"],
            notes=RNG.choice(
                [
                    "Follow-up requested after triage recommendation.",
                    "Patient asked for earlier review if any slot becomes available.",
                    "Booked by admin after reviewing prior visit history.",
                    "Requested to confirm ongoing treatment response.",
                ]
            ),
        )
        db.add(appointment)
        appointment_count += 1

    db.commit()
    return appointment_count, visit_count


def main() -> int:
    if not SEED_PATH.exists():
        raise SystemExit(f"Doctor seed file not found: {SEED_PATH}")

    records = load_seed_records(SEED_PATH)
    create_all()
    with Session(engine) as db:
        delete_existing_data(db)
        import_seed_records(db, records, clean_legacy=False)
        credentials = seed_users_and_linked_profiles(db)
        appointment_count, visit_count = seed_appointments_and_visits(db)
        doctor_count = db.query(func.count(DoctorProfile.id)).scalar() or 0
        patient_count = db.query(func.count(PatientProfile.id)).scalar() or 0

    print("Local project data reset complete.")
    print(f"Doctors available: {doctor_count}")
    print(f"Patients available: {patient_count}")
    print(f"Appointments available: {appointment_count}")
    print(f"Visits available: {visit_count}")
    print("")
    print("Seeded local credentials:")
    for item in credentials:
        print(f"- [{item.role}] {item.email} / {item.password} ({item.label})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
