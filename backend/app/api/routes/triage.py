import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_optional_current_user
from app.db.models import PatientLabResult, TriageAssessment, User
from app.db.session import get_db
from app.schemas.triage import (
    BodyDiagramTriageRequest,
    LabPdfExtractionResponse,
    LabValue,
    SuspectedCondition,
    TriageAssessmentResponse,
    TriageRequest,
    TriageResponse,
)
from app.services.access_control import ensure_patient_profile_access
from app.services.clinical_records import persist_triage_assessment
from app.services.exceptions import TriageSystemUnavailable
from app.services.lab_pdf_extraction import extract_lab_values_from_pdf
from app.services.triage_service import triage as run_triage

router = APIRouter(tags=["triage"])


BODY_REGION_LABELS = {
    "head": "Head",
    "face": "Face",
    "neck": "Neck",
    "chest": "Chest",
    "abdomen": "Abdomen",
    "pelvis_urinary": "Pelvis/Urinary",
    "back": "Back",
    "shoulder": "Shoulder",
    "arm": "Arm",
    "hand_wrist": "Hand/Wrist",
    "hip": "Hip",
    "leg": "Leg",
    "knee": "Knee",
    "foot_ankle": "Foot/Ankle",
    "skin": "Skin",
}

BODY_REGION_DEFAULT_SPECIALTY = {
    "head": "Neurology",
    "face": "ENT",
    "neck": "ENT",
    "chest": "Cardiology",
    "abdomen": "Gastroenterology",
    "pelvis_urinary": "Internal Medicine",
    "back": "Orthopedics",
    "shoulder": "Orthopedics",
    "arm": "Orthopedics",
    "hand_wrist": "Orthopedics",
    "hip": "Orthopedics",
    "leg": "Orthopedics",
    "knee": "Orthopedics",
    "foot_ankle": "Orthopedics",
    "skin": "Dermatology",
}

ORTHOPEDIC_BODY_REGIONS = {
    "back",
    "shoulder",
    "arm",
    "hand_wrist",
    "hip",
    "leg",
    "knee",
    "foot_ankle",
}

CARDIOPULMONARY_CONDITION_TERMS = {
    "heart",
    "angina",
    "myocard",
    "cardiac",
    "pulmonary",
    "pneumonia",
    "bronch",
    "asthma",
}

SKIN_CONDITION_TERMS = {
    "rash",
    "dermatitis",
    "eczema",
    "hives",
    "urticaria",
    "fungal",
    "acne",
    "psoriasis",
    "pityriasis",
    "seborrheic",
}

ORTHOPEDIC_CONDITION_TERMS = {
    "strain",
    "sprain",
    "fracture",
    "muscle",
    "ligament",
    "tendon",
    "joint",
    "bone",
    "disc",
    "nerve",
    "rotator",
    "arthritis",
    "bursitis",
    "meniscus",
    "sciatica",
    "injury",
}

ABDOMINAL_CONDITION_TERMS = {
    "abdominal",
    "abdomen",
    "belly",
    "gastr",
    "dyspepsia",
    "indigestion",
    "reflux",
    "bowel",
    "intestinal",
    "constipation",
    "diarrhea",
    "appendic",
    "gall",
    "chole",
    "pancre",
    "colic",
    "ureter",
    "renal",
    "kidney stone",
}

BODY_REGION_FALLBACK_CONDITIONS = {
    "head": (
        ("Headache or dizziness", "Head symptoms can fit headache or dizziness."),
        (
            "Migraine or tension-type headache",
            "Head pain without selected neurologic red flags can fit a common "
            "headache pattern.",
        ),
    ),
    "face": (
        ("Sinus or facial pain", "Facial pain or pressure can fit a sinus pattern."),
        (
            "Dental or jaw-related pain",
            "Jaw or facial pain can come from dental, jaw, or local facial causes.",
        ),
    ),
    "neck": (
        ("Neck strain", "Neck pain can fit muscle or ligament strain."),
        (
            "Throat or gland inflammation",
            "Swollen glands or trouble swallowing can fit an ENT-related cause.",
        ),
    ),
    "chest": (
        (
            "Chest wall pain or irritation",
            "Chest symptoms without selected emergency features can come from "
            "chest wall or airway irritation.",
        ),
        (
            "Airway irritation",
            "Cough, wheezing, or pain with breathing can fit an airway problem.",
        ),
    ),
    "pelvis_urinary": (
        (
            "Urinary tract irritation",
            "Painful or frequent urination can fit urinary tract irritation.",
        ),
        (
            "Pelvic pain syndrome",
            "Pelvic pain can have urinary, digestive, or musculoskeletal causes.",
        ),
    ),
    "back": (
        ("Back strain", "Back pain can fit muscle or ligament strain."),
        (
            "Disc or nerve irritation",
            "Back pain spreading to the leg or tingling can fit nerve irritation.",
        ),
    ),
    "shoulder": (
        ("Shoulder strain", "Shoulder pain can fit muscle or tendon strain."),
        (
            "Rotator cuff irritation",
            "Reduced shoulder movement can fit tendon or joint irritation.",
        ),
    ),
    "arm": (
        ("Arm strain", "Arm pain can fit muscle or tendon strain."),
        (
            "Nerve irritation",
            "Numbness, tingling, or weakness can fit nerve irritation.",
        ),
    ),
    "hand_wrist": (
        ("Wrist or hand strain", "Hand or wrist pain can fit strain or overuse."),
        (
            "Nerve compression",
            "Numb fingers or reduced grip can fit nerve compression.",
        ),
    ),
    "hip": (
        ("Hip strain", "Hip pain can fit muscle or tendon strain."),
        (
            "Hip joint irritation",
            "Groin pain or reduced movement can fit hip joint irritation.",
        ),
    ),
    "leg": (
        ("Leg strain", "Leg pain can fit muscle or tendon strain."),
        (
            "Localized soft tissue inflammation",
            "Swelling, redness, or warmth can fit local inflammation.",
        ),
    ),
    "knee": (
        ("Knee sprain or strain", "Knee pain can fit a sprain or strain."),
        (
            "Internal knee irritation",
            "Locking, catching, or reduced movement can fit internal knee irritation.",
        ),
    ),
    "foot_ankle": (
        ("Ankle or foot sprain", "Foot or ankle pain can fit a sprain."),
        (
            "Localized soft tissue injury",
            "Swelling or pain after twisting can fit a soft tissue injury.",
        ),
    ),
}


def _build_body_diagram_query(payload: BodyDiagramTriageRequest) -> str:
    region = BODY_REGION_LABELS.get(
        payload.selected_body_region,
        payload.selected_body_region.replace("_", " ").title(),
    )
    associated = (
        ", ".join(payload.associated_symptoms)
        if payload.associated_symptoms
        else "none selected"
    )
    free_text = payload.patient_free_text.strip() or "none"
    positive_findings = [f"{region} region", *payload.main_symptoms]
    if payload.associated_symptoms:
        positive_findings.extend(payload.associated_symptoms)
    route_hint = _body_region_specialty(payload)
    emergency_pattern = _has_body_diagram_emergency_red_flag(payload)
    structured_payload = {
        "input_method": payload.input_method,
        "selected_body_region": payload.selected_body_region,
        "selected_body_region_label": region,
        "chief_complaint": f"{region}: {', '.join(payload.main_symptoms)}",
        "positive_findings": positive_findings,
        "main_symptoms": payload.main_symptoms,
        "severity": payload.severity,
        "onset": payload.onset,
        "duration": payload.duration,
        "associated_symptoms": payload.associated_symptoms,
        "patient_free_text": payload.patient_free_text.strip(),
        "body_region_route_hint": route_hint,
        "structured_emergency_pattern_detected": emergency_pattern,
    }
    selected_parts = [
        "Body selector structured triage intake.",
        "Interpretation rules:",
        "- Treat the selected body region as the patient's strongest symptom location.",
        "- Treat main symptoms, associated symptoms, and free text as reported "
        "positives.",
        "- Do not invent symptoms that were not selected or written by the patient.",
        "- Unselected symptoms are not confirmed present; they are also not true "
        "denials.",
        "- Use severity, onset, and duration exactly as provided.",
        "- Use the body-region route hint only as a weak hint; red flags and "
        "symptom pattern win.",
        "",
        "Clinical intake summary:",
        f"Chief complaint: {region}: {', '.join(payload.main_symptoms)}.",
        f"Positive findings: {', '.join(positive_findings)}.",
        "Severity/onset/duration: "
        f"{payload.severity}; {payload.onset}; {payload.duration}.",
        f"Associated symptoms selected: {associated}.",
        f"Patient free text: {free_text}.",
        "Structured emergency pattern detected: "
        f"{'yes' if emergency_pattern else 'no'}.",
        f"Body-region route hint: {route_hint}.",
        "",
        "Machine-readable JSON:",
        json.dumps(structured_payload, ensure_ascii=False, sort_keys=True),
    ]
    return "\n".join(selected_parts)


def _body_diagram_text(payload: BodyDiagramTriageRequest) -> str:
    return " ".join(
        [
            payload.selected_body_region,
            *payload.main_symptoms,
            payload.severity,
            payload.onset,
            payload.duration,
            *payload.associated_symptoms,
            payload.patient_free_text,
        ]
    ).lower()


def _has_body_diagram_emergency_red_flag(
    payload: BodyDiagramTriageRequest,
) -> bool:
    text = _body_diagram_text(payload)
    has_chest_pain = "chest pain" in text or "chest pressure" in text
    has_cardiac_companion = any(
        term in text
        for term in (
            "shortness of breath",
            "sweating",
            "left arm",
            "jaw pain",
        )
    )
    if has_chest_pain and has_cardiac_companion:
        return True

    if any(
        term in text
        for term in (
            "one-sided weakness",
            "confusion",
            "vision loss",
            "face drooping",
            "one-sided drooping",
        )
    ):
        return True

    if (
        payload.selected_body_region == "head"
        and payload.severity == "severe"
        and payload.onset == "sudden"
        and ("headache" in text or "head injury" in text or "fainting" in text)
    ):
        return True

    if (
        payload.selected_body_region == "neck"
        and "stiff neck" in text
        and "fever" in text
    ):
        return True

    has_severe_abdominal_pain = (
        payload.selected_body_region == "abdomen"
        and payload.severity == "severe"
        and "abdominal pain" in text
    )
    if has_severe_abdominal_pain and any(
        term in text for term in ("fever", "vomiting", "blood in stool")
    ):
        return True

    if payload.selected_body_region == "back" and "loss of bladder" in text:
        return True

    if "allergic" in text and "swelling" in text and "breathing difficulty" in text:
        return True

    if payload.selected_body_region == "skin" and (
        ("swelling" in text and "breathing difficulty" in text)
        or "fever" in text
        or "dark purple" in text
        or "not fading when pressed" in text
        or "spreading quickly" in text
        or "blisters" in text
    ):
        return True

    return False


def _body_region_specialty(payload: BodyDiagramTriageRequest) -> str:
    text = _body_diagram_text(payload)
    if payload.selected_body_region == "chest":
        if any(term in text for term in ("wheezing", "cough", "pain with breathing")):
            return "Pulmonology"
        if (
            ("shortness of breath" in text or "breathing difficulty" in text)
            and "sweating" not in text
            and "left arm" not in text
            and "jaw pain" not in text
            and "palpitations" not in text
        ):
            return "Pulmonology"
        return "Cardiology"

    if payload.selected_body_region == "neck" and any(
        term in text for term in ("neck pain", "pain after injury")
    ):
        return "Orthopedics"

    if payload.selected_body_region == "arm" and "pain spreading from chest" in text:
        return "Cardiology"

    return BODY_REGION_DEFAULT_SPECIALTY[payload.selected_body_region]


def _body_region_has_time_sensitive_feature(payload: BodyDiagramTriageRequest) -> bool:
    text = _body_diagram_text(payload)
    return any(
        term in text
        for term in (
            "cannot bear weight",
            "urinary retention",
            "testicular pain",
            "vaginal bleeding",
            "blood in urine",
            "fainting",
            "head injury",
            "weakness",
            "numbness",
            "numbness or tingling",
            "reduced grip",
            "wound",
            "skin infection",
            "redness or warmth",
        )
    )


def _body_region_fallback_conditions(
    payload: BodyDiagramTriageRequest,
) -> list[SuspectedCondition]:
    region = BODY_REGION_LABELS.get(
        payload.selected_body_region,
        payload.selected_body_region.replace("_", " ").title(),
    )
    configured = BODY_REGION_FALLBACK_CONDITIONS.get(payload.selected_body_region)
    if configured is None:
        configured = (
            (
                f"{region} pain or irritation",
                f"Selected symptoms fit a localized {region.lower()} problem.",
            ),
            (
                "Nonspecific localized symptoms",
                "The selected details are not enough to name one specific condition.",
            ),
        )
    return [
        SuspectedCondition(name=name, likelihood="possible", explanation=explanation)
        for name, explanation in configured
    ]


def _apply_general_body_region_guardrail(
    response: TriageResponse,
    payload: BodyDiagramTriageRequest,
) -> TriageResponse:
    if _has_body_diagram_emergency_red_flag(payload):
        return response

    region = BODY_REGION_LABELS.get(
        payload.selected_body_region,
        payload.selected_body_region.replace("_", " ").title(),
    )
    symptoms = ", ".join(payload.main_symptoms)
    specialty = _body_region_specialty(payload)
    response.recommended_specialty = specialty
    response.specialty_reason = (
        "Recommended after reviewing the selected body region and symptoms: "
        f"{specialty}."
    )

    if payload.severity == "mild" and not _body_region_has_time_sensitive_feature(
        payload
    ):
        response.triage_level = "low"
        response.urgency_level = "low"
        response.urgency_label = "Low"
        response.needs_clarification = False
        response.questions = []
        response.urgency_reason = (
            f"Mild {region.lower()} symptoms without selected emergency warning "
            "signs do not show a clear high-urgency pattern."
        )
        response.actions = [
            "Monitor symptoms and arrange routine medical review if symptoms "
            "persist, recur, or worsen.",
            "Seek urgent help if severe pain, breathing difficulty, fainting, "
            "confusion, bleeding, fever, or fast worsening appears.",
        ]
    elif response.triage_level == "high":
        response.triage_level = "medium"
        response.urgency_level = "medium"
        response.urgency_label = "Medium"
        response.needs_clarification = False
        response.questions = []
        response.urgency_reason = (
            f"The selected {region.lower()} symptoms may need timely review, but "
            "no selected emergency red flag supports high urgency."
        )
        response.actions = [
            "Consider urgent care or a same-day clinic visit if symptoms persist "
            "or worsen.",
            "Seek emergency care if severe pain, breathing difficulty, fainting, "
            "confusion, bleeding, fever, or fast worsening appears.",
        ]
    response.recommended_actions = response.actions

    response.patient_friendly_explanation = (
        f"Your {region.lower()} symptoms ({symptoms}) fit a {specialty.lower()} "
        "assessment path based on the details selected."
    )
    response.summary = response.patient_friendly_explanation
    response.clinical_summary = (
        f"Body selector indicates {region.lower()} symptoms: {symptoms}. Severity "
        f"is {payload.severity}, onset is {payload.onset}, and duration is "
        f"{payload.duration}. No body-selector emergency red flag was selected."
    )
    response.red_flags = []
    response.suspected_conditions = _body_region_fallback_conditions(payload)[:3]
    return response


def _is_irrelevant_cardiopulmonary_condition(condition: SuspectedCondition) -> bool:
    name = condition.name.lower()
    return any(term in name for term in CARDIOPULMONARY_CONDITION_TERMS)


def _is_skin_condition(condition: SuspectedCondition) -> bool:
    name = condition.name.lower()
    return any(term in name for term in SKIN_CONDITION_TERMS)


def _is_orthopedic_condition(condition: SuspectedCondition) -> bool:
    text = f"{condition.name} {condition.explanation}".lower()
    return any(term in text for term in ORTHOPEDIC_CONDITION_TERMS)


def _is_abdominal_condition(condition: SuspectedCondition) -> bool:
    name = condition.name.lower()
    return any(term in name for term in ABDOMINAL_CONDITION_TERMS)


def _is_urinary_condition(condition: SuspectedCondition) -> bool:
    name = condition.name.lower()
    return any(term in name for term in ("ureter", "urinary", "renal", "kidney"))


def _has_selected_urinary_feature(payload: BodyDiagramTriageRequest) -> bool:
    text = _body_diagram_text(payload)
    return any(
        term in text
        for term in (
            "urine",
            "urination",
            "urinary",
            "blood in urine",
            "flank",
            "side pain",
        )
    )


def _apply_body_diagram_guardrails(
    response: TriageResponse,
    payload: BodyDiagramTriageRequest,
) -> TriageResponse:
    if (
        payload.selected_body_region == "abdomen"
        and not _has_body_diagram_emergency_red_flag(payload)
    ):
        symptoms = ", ".join(payload.main_symptoms)
        response.recommended_specialty = "Gastroenterology"
        response.specialty_reason = (
            "Recommended after reviewing the selected body region and symptoms: "
            "Gastroenterology."
        )
        if payload.severity == "mild":
            response.triage_level = "low"
            response.urgency_level = "low"
            response.urgency_label = "Low"
            response.needs_clarification = False
            response.questions = []
            response.urgency_reason = (
                "Mild abdominal pain without selected fever, repeated vomiting, "
                "blood in stool, severe pain, fainting, or worsening illness does "
                "not show a clear emergency warning sign."
            )
            response.actions = [
                "Monitor symptoms and arrange routine medical review if pain "
                "persists, recurs, or becomes more intense.",
                "Seek urgent help if severe pain, fever, repeated vomiting, blood "
                "in stool, fainting, abdominal swelling, or yellow eyes appears.",
            ]
            response.recommended_actions = response.actions
            response.red_flags = []
        elif response.triage_level == "high":
            response.triage_level = "medium"
            response.urgency_level = "medium"
            response.urgency_label = "Medium"
            response.urgency_reason = (
                "Abdominal pain can need timely review, but no emergency red flags "
                "were selected in the body-diagram form."
            )
            response.actions = [
                "Consider urgent care or a same-day clinic visit if pain persists "
                "or worsens.",
                "Seek emergency care if severe pain, fever, repeated vomiting, "
                "blood in stool, fainting, abdominal swelling, or yellow eyes appears.",
            ]
            response.recommended_actions = response.actions
            response.red_flags = []

        response.patient_friendly_explanation = (
            f"Your abdomen symptoms ({symptoms}) fit an abdominal or digestive "
            "problem based on the details selected."
        )
        response.summary = response.patient_friendly_explanation
        response.clinical_summary = (
            f"Body selector indicates abdominal symptoms: {symptoms}. Severity is "
            f"{payload.severity}, onset is {payload.onset}, and duration is "
            f"{payload.duration}. No fever, repeated vomiting, blood in stool, "
            "severe pain, fainting, abdominal swelling, or yellow eyes were selected."
        )
        abdominal_conditions = [
            condition
            for condition in response.suspected_conditions
            if _is_abdominal_condition(condition)
            and not _is_irrelevant_cardiopulmonary_condition(condition)
            and (
                not _is_urinary_condition(condition)
                or _has_selected_urinary_feature(payload)
            )
        ]
        if not abdominal_conditions:
            abdominal_conditions = [
                SuspectedCondition(
                    name="Nonspecific abdominal pain",
                    likelihood="possible",
                    explanation=(
                        "Mild abdominal pain without selected red flags can be "
                        "nonspecific early abdominal discomfort."
                    ),
                ),
                SuspectedCondition(
                    name="Indigestion or stomach irritation",
                    likelihood="possible",
                    explanation=(
                        "Mild short-duration abdominal pain can fit digestive "
                        "irritation or indigestion."
                    ),
                ),
            ]
        response.suspected_conditions = abdominal_conditions[:3]
        return response

    if (
        payload.selected_body_region == "skin"
        and not _has_body_diagram_emergency_red_flag(payload)
    ):
        symptoms = ", ".join(payload.main_symptoms)
        response.recommended_specialty = "Dermatology"
        response.specialty_reason = (
            "Recommended after reviewing the selected body region and symptoms: "
            "Dermatology."
        )
        if payload.severity == "mild":
            response.triage_level = "low"
            response.urgency_level = "low"
            response.urgency_label = "Low"
            response.needs_clarification = False
            response.questions = []
            response.urgency_reason = (
                "Mild itching and rash without selected breathing difficulty, "
                "fever, rapid spreading, blistering, or swelling usually does not "
                "show an emergency warning sign."
            )
            response.actions = [
                "Arrange a routine dermatology or primary care review if it persists "
                "or spreads.",
                "Seek urgent help if breathing difficulty, face/lip swelling, fever, "
                "rapid spreading, severe pain, or blistering appears.",
            ]
            response.recommended_actions = response.actions
            response.red_flags = []

        response.patient_friendly_explanation = (
            f"Your skin symptoms ({symptoms}) fit a mild skin irritation or rash "
            "pattern based on the details selected."
        )
        response.summary = response.patient_friendly_explanation
        response.clinical_summary = (
            f"Body selector indicates skin symptoms: {symptoms}. Severity is "
            f"{payload.severity}, onset is {payload.onset}, and duration is "
            f"{payload.duration}. No breathing difficulty, swelling, fever, "
            "rapid spreading, or blistering was selected."
        )
        skin_conditions = [
            condition
            for condition in response.suspected_conditions
            if _is_skin_condition(condition)
            and not _is_irrelevant_cardiopulmonary_condition(condition)
        ]
        if not skin_conditions:
            skin_conditions = [
                SuspectedCondition(
                    name="Mild dermatitis or skin irritation",
                    likelihood="possible",
                    explanation=(
                        "Itching with rash can fit a mild dermatitis or irritation "
                        "pattern."
                    ),
                ),
                SuspectedCondition(
                    name="Allergic or contact rash",
                    likelihood="possible",
                    explanation=(
                        "A new itchy rash can occur after contact with an irritant "
                        "or allergen."
                    ),
                ),
            ]
        response.suspected_conditions = skin_conditions[:3]
        return response

    if payload.selected_body_region not in ORTHOPEDIC_BODY_REGIONS:
        return _apply_general_body_region_guardrail(response, payload)

    if (
        payload.selected_body_region not in ORTHOPEDIC_BODY_REGIONS
        or _has_body_diagram_emergency_red_flag(payload)
    ):
        return response

    region = BODY_REGION_LABELS.get(
        payload.selected_body_region,
        payload.selected_body_region.replace("_", " ").title(),
    )
    symptoms = ", ".join(payload.main_symptoms)
    response.recommended_specialty = "Orthopedics"
    response.specialty_reason = (
        "Recommended after reviewing the selected body region and symptoms: "
        "Orthopedics."
    )

    text = _body_diagram_text(payload)
    if payload.severity == "mild" and not _body_region_has_time_sensitive_feature(
        payload
    ):
        response.triage_level = "low"
        response.urgency_level = "low"
        response.urgency_label = "Low"
        response.needs_clarification = False
        response.questions = []
        response.urgency_reason = (
            "Mild localized musculoskeletal symptoms without selected emergency "
            "red flags usually do not need emergency care."
        )
        response.actions = [
            "Monitor symptoms and arrange routine medical review if pain persists "
            "or worsens.",
            "Seek urgent help sooner if severe swelling, deformity, numbness, fever, "
            "or worsening pain appears.",
        ]
        response.recommended_actions = response.actions
        response.red_flags = []
    elif response.triage_level == "high" or (
        response.triage_level == "low" and "cannot bear weight" in text
    ):
        response.triage_level = "medium"
        response.urgency_level = "medium"
        response.urgency_label = "Medium"
        response.urgency_reason = (
            "Inability to bear weight can need same-day clinical review, but no "
            "emergency red flags were selected."
        )
        response.actions = [
            "Arrange a same-day medical review or urgent clinic assessment.",
            "Seek urgent help sooner if severe swelling, deformity, numbness, fever, "
            "or worsening pain appears.",
        ]
        response.recommended_actions = response.actions
        response.red_flags = [
            flag
            for flag in response.red_flags
            if "chest" not in flag.lower()
            and "breath" not in flag.lower()
            and "heart" not in flag.lower()
        ]

    response.patient_friendly_explanation = (
        f"Your {region.lower()} symptoms ({symptoms}) fit an orthopedic or "
        "musculoskeletal problem more than a heart or lung problem based on the "
        "details selected."
    )
    response.summary = response.patient_friendly_explanation
    response.clinical_summary = (
        f"Body selector indicates {region.lower()} symptoms: {symptoms}. "
        f"Severity is {payload.severity}, onset is {payload.onset}, and duration "
        f"is {payload.duration}. No chest or breathing symptoms were selected."
    )

    filtered_conditions = [
        condition
        for condition in response.suspected_conditions
        if not _is_irrelevant_cardiopulmonary_condition(condition)
        and _is_orthopedic_condition(condition)
    ]
    if not filtered_conditions:
        filtered_conditions.extend(
            [
                SuspectedCondition(
                    name=f"{region} sprain or strain",
                    likelihood="possible",
                    explanation=(
                        "Localized pain with limited weight bearing can fit a "
                        "musculoskeletal sprain or strain."
                    ),
                ),
                SuspectedCondition(
                    name="Occult fracture or internal joint injury",
                    likelihood="possible",
                    explanation=(
                        "Inability to bear weight can sometimes occur with a "
                        "fracture or internal joint injury even without a clear "
                        "deformity."
                    ),
                ),
            ]
        )
    response.suspected_conditions = filtered_conditions[:3]
    return response


@router.post("/triage", response_model=TriageResponse)
def triage_route(
    payload: TriageRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> TriageResponse:
    patient = None
    if payload.patient_id is not None:
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication is required to use patient context.",
            )
        patient = ensure_patient_profile_access(db, current_user, payload.patient_id)

    try:
        response = run_triage(
            payload.query,
            patient_id=patient.id if patient else None,
            db=db,
            age=payload.patient_age,
            lab_values=payload.lab_values,
            language=payload.language,
        )
    except TriageSystemUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    if patient is not None:
        persist_triage_assessment(
            db,
            patient=patient,
            query_text=payload.query,
            response=response,
        )
        db.commit()
    return response


@router.post("/triage/body-diagram", response_model=TriageResponse)
def body_diagram_triage_route(
    payload: BodyDiagramTriageRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> TriageResponse:
    patient = None
    if payload.patient_id is not None:
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication is required to use patient context.",
            )
        patient = ensure_patient_profile_access(db, current_user, payload.patient_id)

    query = _build_body_diagram_query(payload)
    try:
        response = run_triage(
            query,
            patient_id=patient.id if patient else None,
            db=db,
            language=payload.language,
        )
    except TriageSystemUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    response = _apply_body_diagram_guardrails(response, payload)
    if patient is not None:
        persist_triage_assessment(
            db,
            patient=patient,
            query_text=query,
            response=response,
        )
        db.commit()
    return response


@router.post("/triage/lab-pdf/extract", response_model=LabPdfExtractionResponse)
async def extract_lab_pdf_route(
    patient_id: int | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> LabPdfExtractionResponse:
    if file.content_type != "application/pdf" and not file.filename.lower().endswith(
        ".pdf"
    ):
        raise HTTPException(status_code=422, detail="Only PDF files are accepted.")

    patient = None
    if patient_id is not None:
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication is required to attach lab values.",
            )
        patient = ensure_patient_profile_access(db, current_user, patient_id)

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="PDF file is too large.")

    try:
        values = extract_lab_values_from_pdf(content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if patient is not None:
        for value in values:
            db.add(
                PatientLabResult(
                    patient_id=patient.id,
                    lab_name=value.lab_name,
                    value=value.value,
                    unit=value.unit,
                    reference_range=value.reference_range,
                    source_filename=file.filename,
                )
            )
        db.commit()

    return LabPdfExtractionResponse(
        filename=file.filename,
        values=[LabValue(**value.__dict__) for value in values],
    )


@router.get(
    "/triage/history/{patient_id}", response_model=list[TriageAssessmentResponse]
)
def triage_history_route(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TriageAssessmentResponse]:
    ensure_patient_profile_access(db, current_user, patient_id)
    return (
        db.query(TriageAssessment)
        .filter(TriageAssessment.patient_id == patient_id)
        .order_by(TriageAssessment.created_at.desc())
        .all()
    )
