from __future__ import annotations

import json
import logging
import re

import httpx

from app.core.config import get_settings
from app.schemas.triage import ClarificationQuestion

CONFIDENCE_THRESHOLD = 0.75
MAX_CLARIFICATION_QUESTIONS = 4
MIN_LLM_QUESTIONS = 2
LLM_TIMEOUT_SECONDS = 75.0

logger = logging.getLogger(__name__)

QUESTION_BANK: dict[str, list[ClarificationQuestion]] = {
    "pain": [
        ClarificationQuestion(
            id="pain_location",
            question="Where exactly is the pain?",
            options=["Chest", "Back", "Stomach/Abdomen", "Head", "Arm/Leg", "Neck", "Other"],
        ),
        ClarificationQuestion(
            id="pain_radiation",
            question="Does the pain spread anywhere else?",
            options=["Yes, to my arm", "Yes, to my leg", "Yes, to my chest", "Yes, to my back", "No"],
        ),
        ClarificationQuestion(
            id="pain_duration",
            question="How long have you had this pain?",
            options=["Just started", "Few hours", "Few days", "More than a week", "Months"],
        ),
        ClarificationQuestion(
            id="pain_nature",
            question="How would you describe the pain?",
            options=["Sharp/Stabbing", "Dull/Aching", "Burning", "Crushing/Pressure", "Throbbing"],
        ),
    ],
    "headache": [
        ClarificationQuestion(
            id="headache_severity",
            question="How severe is the headache on a scale of 1-10?",
            options=["1-3 (mild)", "4-6 (moderate)", "7-9 (severe)", "10 (worst ever)"],
        ),
        ClarificationQuestion(
            id="headache_onset",
            question="Did it come on suddenly or gradually?",
            options=["Suddenly (within seconds)", "Over minutes", "Gradually over hours/days"],
        ),
        ClarificationQuestion(
            id="headache_associated",
            question="Do you have any of these with it?",
            options=["Fever", "Stiff neck", "Vision changes", "Vomiting", "None of these"],
        ),
    ],
    "breathing": [
        ClarificationQuestion(
            id="breathing_severity",
            question="How severe is the breathing difficulty?",
            options=["Mild (can talk normally)", "Moderate (short sentences)", "Severe (can barely speak)"],
        ),
        ClarificationQuestion(
            id="breathing_onset",
            question="When did it start?",
            options=["Right now/sudden", "Past hour", "Past few hours", "Gradually over days"],
        ),
        ClarificationQuestion(
            id="breathing_associated",
            question="Do you also have?",
            options=["Chest pain", "Wheezing/whistling sound", "Blue lips or fingertips", "Fever", "None"],
        ),
    ],
    "fever": [
        ClarificationQuestion(
            id="fever_temp",
            question="What is the temperature?",
            options=["Below 38C", "38-39C", "39-40C", "Above 40C", "Not measured"],
        ),
        ClarificationQuestion(
            id="fever_duration",
            question="How long has the fever been present?",
            options=["Less than 24 hours", "1-3 days", "More than 3 days", "More than a week"],
        ),
        ClarificationQuestion(
            id="fever_associated",
            question="Are there any other symptoms?",
            options=["Stiff neck", "Rash", "Difficulty breathing", "Confusion", "None"],
        ),
    ],
    "cough": [
        ClarificationQuestion(
            id="cough_type",
            question="What type of cough?",
            options=["Dry cough", "Productive (with mucus)", "Barking/croup-like", "Whooping"],
        ),
        ClarificationQuestion(
            id="cough_duration",
            question="How long have you had it?",
            options=["Less than a week", "1-2 weeks", "More than 2 weeks", "Months"],
        ),
        ClarificationQuestion(
            id="cough_associated",
            question="Any of these with it?",
            options=["Blood in mucus", "Fever", "Breathing difficulty", "Night sweats", "None"],
        ),
    ],
    "dizziness": [
        ClarificationQuestion(
            id="dizziness_type",
            question="What does dizziness feel like?",
            options=["Room spinning (vertigo)", "Lightheaded/faint", "Unsteady/balance problem"],
        ),
        ClarificationQuestion(
            id="dizziness_trigger",
            question="When does it happen?",
            options=["All the time", "When standing up", "When moving head", "Comes and goes"],
        ),
        ClarificationQuestion(
            id="dizziness_associated",
            question="Any other symptoms?",
            options=["Hearing loss", "Ringing in ears", "Chest pain", "Vision changes", "None"],
        ),
    ],
    "rash": [
        ClarificationQuestion(
            id="rash_location",
            question="Where is the rash?",
            options=["Face", "Body/trunk", "Arms/legs", "Widespread", "Groin area"],
        ),
        ClarificationQuestion(
            id="rash_type",
            question="What does the rash look like?",
            options=["Red flat patches", "Raised bumps/hives", "Blisters", "Purple/dark spots"],
        ),
        ClarificationQuestion(
            id="rash_associated",
            question="Any of these with it?",
            options=["Fever", "Itching", "Throat swelling", "Recent medication", "None"],
        ),
    ],
    "default": [
        ClarificationQuestion(
            id="symptom_duration",
            question="How long have you had these symptoms?",
            options=["Just started today", "A few days", "About a week", "More than 2 weeks", "Months"],
        ),
        ClarificationQuestion(
            id="symptom_severity",
            question="How severe are your symptoms overall?",
            options=["Mild - barely noticeable", "Moderate - affecting daily life", "Severe - can barely function"],
        ),
        ClarificationQuestion(
            id="symptom_associated",
            question="Do you have any of these additional symptoms?",
            options=["Fever", "Pain", "Breathing difficulty", "Nausea/vomiting", "None of these"],
        ),
    ],
}

SMART_QUESTION_BANK: dict[str, list[ClarificationQuestion]] = {
    "pain_red_flags": [
        ClarificationQuestion(
            id="pain_injury",
            question="Did this start after an injury, fall, heavy lifting, or exercise?",
            options=["Yes, clear injury", "After exercise/strain", "No injury", "Not sure"],
        ),
        ClarificationQuestion(
            id="pain_function",
            question="Can you move and use the painful area normally?",
            options=["Normal movement", "Painful but possible", "Very limited", "Cannot use it"],
        ),
        ClarificationQuestion(
            id="pain_neurovascular",
            question="Do you have numbness, weakness, swelling, or the area feels cold/blue?",
            options=["Numbness/tingling", "Weakness", "Swelling", "Cold or blue", "None"],
        ),
    ],
    "chest_cardiac": [
        ClarificationQuestion(
            id="chest_exertion",
            question="Is the chest discomfort worse with exertion or relieved by rest?",
            options=["Worse with exertion", "Relieved by rest", "Not related to activity", "Not sure"],
        ),
        ClarificationQuestion(
            id="chest_associated",
            question="Do you also have sweating, nausea, shortness of breath, or pain spreading to jaw/arm?",
            options=["Sweating", "Nausea", "Shortness of breath", "Jaw/arm pain", "None"],
        ),
    ],
    "orthopedics": [
        ClarificationQuestion(
            id="ortho_weight_bearing",
            question="Can you put weight on it or use the limb for normal activities?",
            options=["Yes normally", "Yes but painful", "Barely", "No"],
        ),
        ClarificationQuestion(
            id="ortho_deformity",
            question="Is there visible deformity, major swelling, bruising, or reduced range of motion?",
            options=["Visible deformity", "Major swelling", "Bruising", "Reduced motion", "None"],
        ),
    ],
    "neurology": [
        ClarificationQuestion(
            id="neuro_deficit",
            question="Do you have weakness, numbness, facial droop, confusion, or trouble speaking?",
            options=["Weakness", "Numbness", "Facial droop", "Confusion/trouble speaking", "None"],
        ),
        ClarificationQuestion(
            id="neuro_onset",
            question="Did the symptom start suddenly or build gradually?",
            options=["Suddenly", "Over minutes", "Gradually over hours/days", "Comes and goes"],
        ),
    ],
    "gastroenterology": [
        ClarificationQuestion(
            id="abdomen_location",
            question="Where is the abdominal discomfort strongest?",
            options=["Upper right", "Upper middle", "Lower right", "Lower left", "All over"],
        ),
        ClarificationQuestion(
            id="gi_red_flags",
            question="Do you have vomiting blood, black stools, yellow eyes/skin, or severe dehydration?",
            options=["Vomiting blood", "Black stools", "Yellow eyes/skin", "Severe dehydration", "None"],
        ),
    ],
    "ent": [
        ClarificationQuestion(
            id="ent_swallowing_breathing",
            question="Are you having trouble swallowing, breathing, hearing, or severe throat/ear pain?",
            options=["Trouble swallowing", "Trouble breathing", "Hearing change", "Severe throat/ear pain", "None"],
        ),
    ],
    "dermatology": [
        ClarificationQuestion(
            id="skin_blanching_spread",
            question="Is the rash spreading quickly, painful, blistering, or purple and non-fading?",
            options=["Spreading quickly", "Painful", "Blistering", "Purple/non-fading", "None"],
        ),
    ],
}

KEYWORD_TO_CATEGORY = {
    "pain": "pain",
    "ache": "pain",
    "hurts": "pain",
    "sore": "pain",
    "headache": "headache",
    "head": "headache",
    "breath": "breathing",
    "breathing": "breathing",
    "wheez": "breathing",
    "fever": "fever",
    "temperature": "fever",
    "cough": "cough",
    "coughing": "cough",
    "dizz": "dizziness",
    "vertigo": "dizziness",
    "spinning": "dizziness",
    "rash": "rash",
    "itch": "rash",
    "hives": "rash",
}


def _add_unique(
    questions: list[ClarificationQuestion],
    candidates: list[ClarificationQuestion],
) -> None:
    seen = {question.id for question in questions}
    for candidate in candidates:
        if candidate.id in seen:
            continue
        questions.append(candidate)
        seen.add(candidate.id)


def _condition_names(summary: object | None) -> str:
    conditions = getattr(summary, "possible_conditions", []) if summary else []
    return " ".join(str(getattr(condition, "name", "")) for condition in conditions).lower()


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _summarize_conditions(summary: object | None) -> list[dict[str, str]]:
    conditions = getattr(summary, "possible_conditions", []) if summary else []
    summarized = []
    for condition in conditions[:3]:
        name = str(getattr(condition, "name", "") or "").strip()
        explanation = str(getattr(condition, "explanation", "") or "").strip()
        likelihood = str(getattr(condition, "likelihood", "") or "").strip()
        if name:
            summarized.append(
                {
                    "name": name,
                    "likelihood": likelihood,
                    "explanation": explanation[:220],
                }
            )
    return summarized


def _build_llm_prompt(
    *,
    query: str,
    summary: object | None,
    recommended_specialty: str | None,
    triage_level: str | None,
) -> str:
    payload = {
        "patient_query": query,
        "triage_level": triage_level,
        "recommended_specialty": recommended_specialty,
        "clinical_summary": str(getattr(summary, "clinical_summary", "") or "")[:600],
        "possible_conditions": _summarize_conditions(summary),
        "red_flags": list(getattr(summary, "red_flags", []) or [])[:4],
    }
    example = [
        {
            "id": "pain_trigger",
            "question": "Did the pain start after an injury, exertion, or at rest?",
            "options": ["After injury", "After exertion", "At rest", "Not sure"],
        },
        {
            "id": "associated_symptoms",
            "question": "Which associated symptom is present, if any?",
            "options": ["Fever", "Numbness or weakness", "Shortness of breath", "None"],
        },
    ]
    return (
        "You are helping a medical triage system ask targeted clarification questions. "
        "The system is uncertain because the patient did not provide enough detail. "
        "Generate questions that best differentiate between the listed possible conditions "
        "and identify urgent red flags. Do not diagnose. Do not give advice. Do not ask for "
        "name, phone, address, national ID, insurance, or other identifying details.\n\n"
        "Return ONLY valid JSON: an array of 2 to 4 objects with this exact shape:\n"
        '[{"id":"short_snake_case","question":"patient-facing question","options":["choice 1","choice 2","choice 3"]}]\n\n'
        "Rules:\n"
        "- Prefer multiple choice options with 3 to 5 choices.\n"
        "- Options must be self-contained; avoid plain 'Yes' or 'No' unless the option repeats what yes/no means.\n"
        "- Good: 'Yes - numbness or tingling is present'. Bad: 'Yes'.\n"
        "- Each question must target missing information that changes urgency, likely condition, or specialty.\n"
        "- Ask about onset, location, severity, triggers, spread, function, associated symptoms, and red flags only when relevant.\n"
        "- Keep wording simple and non-alarming.\n"
        "- Include a neutral option like 'None', 'Not sure', or 'No' when appropriate.\n"
        "- Avoid duplicate questions.\n\n"
        f"Example JSON:\n{json.dumps(example, indent=2)}\n\n"
        f"Case data:\n{json.dumps(payload, indent=2)}"
    )


def _extract_json_array(raw_text: str) -> object | None:
    candidate = raw_text.strip()
    if not candidate:
        return None
    if not candidate.startswith("["):
        start = candidate.find("[")
        end = candidate.rfind("]")
        if start == -1 or end == -1 or end <= start:
            return None
        candidate = candidate[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _normalize_question_id(value: str, index: int) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    if not normalized:
        normalized = f"clarification_{index + 1}"
    return normalized[:48]


def _validate_llm_questions(raw_questions: object) -> list[ClarificationQuestion]:
    if not isinstance(raw_questions, list):
        return []

    questions: list[ClarificationQuestion] = []
    seen_ids: set[str] = set()
    seen_text: set[str] = set()

    for index, item in enumerate(raw_questions[:MAX_CLARIFICATION_QUESTIONS]):
        if not isinstance(item, dict):
            continue

        question_text = str(item.get("question", "") or "").strip()
        if len(question_text) < 12 or len(question_text) > 180:
            continue
        text_key = question_text.lower()
        if text_key in seen_text:
            continue

        question_id = _normalize_question_id(str(item.get("id", "") or ""), index)
        if question_id in seen_ids:
            question_id = f"{question_id}_{index + 1}"

        options_value = item.get("options")
        options: list[str] | None = None
        if isinstance(options_value, list):
            options = []
            seen_options: set[str] = set()
            for option in options_value[:5]:
                option_text = str(option or "").strip()
                if not option_text or len(option_text) > 80:
                    continue
                option_key = option_text.lower()
                if option_key in seen_options:
                    continue
                options.append(option_text)
                seen_options.add(option_key)
            if len(options) < 2:
                options = None

        questions.append(
            ClarificationQuestion(
                id=question_id,
                question=question_text,
                options=options,
            )
        )
        seen_ids.add(question_id)
        seen_text.add(text_key)

    if len(questions) < MIN_LLM_QUESTIONS:
        return []
    return questions


def _generate_llm_questions(
    *,
    query: str,
    summary: object | None,
    recommended_specialty: str | None,
    triage_level: str | None,
) -> list[ClarificationQuestion]:
    settings = get_settings()
    if settings.reasoner_mode != "ollama":
        return []

    prompt = _build_llm_prompt(
        query=query,
        summary=summary,
        recommended_specialty=recommended_specialty,
        triage_level=triage_level,
    )
    try:
        with httpx.Client(timeout=LLM_TIMEOUT_SECONDS) as client:
            response = client.post(
                f"{settings.ollama_host}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1, "num_predict": 700},
                },
            )
            response.raise_for_status()
        generated = str(response.json().get("response", "") or "")
        questions = _validate_llm_questions(_extract_json_array(generated))
        if questions:
            logger.info("llm_clarification_questions_generated count=%s", len(questions))
        return questions
    except Exception as exc:
        logger.warning("llm_clarification_questions_failed error=%s", exc)
        return []


def _fallback_clarification_questions(
    query: str,
    summary: object | None = None,
    recommended_specialty: str | None = None,
    triage_level: str | None = None,
) -> list[ClarificationQuestion]:
    lowered = query.lower()
    specialty = (recommended_specialty or "").lower()
    conditions = _condition_names(summary)
    combined = f"{lowered} {specialty} {conditions}"
    questions: list[ClarificationQuestion] = []

    if "chest pain" in combined or "cardiology" in combined:
        _add_unique(questions, SMART_QUESTION_BANK["chest_cardiac"])

    if _has_any(combined, ("fracture", "sprain", "tendin", "orthopedic", "orthopedics", "arm", "leg", "back", "neck")):
        _add_unique(questions, SMART_QUESTION_BANK["pain_red_flags"])
        _add_unique(questions, SMART_QUESTION_BANK["orthopedics"])

    if _has_any(combined, ("headache", "migraine", "stroke", "meningitis", "neurology", "dizziness", "vertigo")):
        _add_unique(questions, SMART_QUESTION_BANK["neurology"])

    if _has_any(combined, ("abdominal", "stomach", "gastro", "appendicitis", "gastritis", "bowel", "liver")):
        _add_unique(questions, SMART_QUESTION_BANK["gastroenterology"])

    if _has_any(combined, ("ent", "ear", "throat", "sinus", "tonsil", "hearing")):
        _add_unique(questions, SMART_QUESTION_BANK["ent"])

    if _has_any(combined, ("rash", "skin", "dermat", "hives", "urticaria")):
        _add_unique(questions, SMART_QUESTION_BANK["dermatology"])

    for keyword, category in KEYWORD_TO_CATEGORY.items():
        if keyword in lowered:
            _add_unique(questions, QUESTION_BANK.get(category, QUESTION_BANK["default"]))
            break

    if not questions:
        _add_unique(questions, QUESTION_BANK["default"])

    if triage_level == "high":
        return questions[:MAX_CLARIFICATION_QUESTIONS]
    return questions[:3]


def get_clarification_questions(
    query: str,
    summary: object | None = None,
    recommended_specialty: str | None = None,
    triage_level: str | None = None,
) -> list[ClarificationQuestion]:
    llm_questions = _generate_llm_questions(
        query=query,
        summary=summary,
        recommended_specialty=recommended_specialty,
        triage_level=triage_level,
    )
    if llm_questions:
        return llm_questions

    return _fallback_clarification_questions(
        query,
        summary=summary,
        recommended_specialty=recommended_specialty,
        triage_level=triage_level,
    )


def build_enriched_query(original_query: str, answers: list) -> str:
    question_text_by_id = {
        question.id: question.question
        for bank in (QUESTION_BANK, SMART_QUESTION_BANK)
        for questions in bank.values()
        for question in questions
    }
    additions = []
    for answer in answers:
        if not answer.answer or answer.answer in ("None", "None of these"):
            continue
        label = question_text_by_id.get(answer.question_id, answer.question_id)
        additions.append(f"Question: {label} Answer: {answer.answer}")
    if additions:
        return f"{original_query}. Additional details: {', '.join(additions)}"
    return original_query


def needs_clarification(confidence: float, triage_level: str | None = None) -> bool:
    if triage_level == "high":
        return False
    return confidence < CONFIDENCE_THRESHOLD
