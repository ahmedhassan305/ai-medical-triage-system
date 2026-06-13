from __future__ import annotations

import re
from copy import deepcopy

from app.schemas.triage import ClarificationQuestion, TriageLevel, TriageResponse

Language = str

ARABIC_RE = re.compile(r"[\u0600-\u06ff]")

ARABIC_QUERY_HINTS: tuple[tuple[str, str], ...] = (
    ("كحة", "cough"),
    ("سعال", "cough"),
    ("بلغم", "productive cough"),
    ("نهجان", "breathing difficulty"),
    ("ضيق تنفس", "breathing difficulty"),
    ("صعوبة في التنفس", "breathing difficulty"),
    ("صفير", "wheezing"),
    ("صدر", "chest"),
    ("ألم صدر", "chest pain"),
    ("الم في الصدر", "chest pain"),
    ("ضغط في الصدر", "chest pressure"),
    ("خفقان", "palpitations"),
    ("حمى", "fever"),
    ("حرارة", "fever"),
    ("سخونية", "fever"),
    ("قيء", "vomiting"),
    ("ترجيع", "vomiting"),
    ("غثيان", "nausea"),
    ("إسهال", "diarrhea"),
    ("اسهال", "diarrhea"),
    ("إمساك", "constipation"),
    ("امساك", "constipation"),
    ("بطن", "abdominal pain"),
    ("مغص", "abdominal pain"),
    ("ألم في البطن", "abdominal pain"),
    ("وجع بطن", "abdominal pain"),
    ("معدة", "stomach pain"),
    ("صداع", "headache"),
    ("دوخة", "dizziness"),
    ("دوار", "vertigo"),
    ("تنميل", "numbness"),
    ("وخز", "tingling"),
    ("ضعف", "weakness"),
    ("ظهر", "back pain"),
    ("رقبة", "neck pain"),
    ("طفح", "rash"),
    ("حكة", "itching"),
    ("حساسية", "allergy"),
    ("مدخن", "smoker"),
    ("تدخين", "smoker"),
    ("من امبارح", "since yesterday"),
    ("منذ أمس", "since yesterday"),
    ("من يوم", "1 day"),
    ("من يومين", "2 days"),
    ("من أسبوع", "1 week"),
    ("من اسبوع", "1 week"),
    ("شديد", "severe"),
    ("خفيف", "mild"),
    ("متوسط", "moderate"),
)

CONDITION_AR: dict[str, str] = {
    "acute bronchitis": "التهاب الشعب الهوائية الحاد",
    "acute coronary syndrome": "متلازمة الشريان التاجي الحادة",
    "appendicitis": "التهاب الزائدة الدودية",
    "asthma": "الربو",
    "asthma exacerbation": "نوبة ربو",
    "bronchitis": "التهاب الشعب الهوائية",
    "common cold": "نزلة برد",
    "cholecystitis": "التهاب المرارة",
    "copd exacerbation": "تفاقم مرض الانسداد الرئوي المزمن",
    "dehydration": "الجفاف",
    "food poisoning": "تسمم غذائي",
    "gastroenteritis": "النزلة المعوية",
    "gastritis": "التهاب المعدة",
    "gerd": "ارتجاع المريء",
    "influenza": "الإنفلونزا",
    "inflammatory bowel disease": "مرض التهاب الأمعاء",
    "inflammatory bowel disease (ibd)": "مرض التهاب الأمعاء",
    "irritable bowel syndrome": "متلازمة القولون العصبي",
    "meningitis": "التهاب السحايا",
    "migraine": "الشقيقة",
    "muscle or ligament strain": "شد عضلي أو أربطة",
    "myocardial infarction": "احتشاء عضلة القلب",
    "peptic ulcer disease": "القرحة الهضمية",
    "pleurisy": "التهاب الغشاء البلوري",
    "pneumonia": "الالتهاب الرئوي",
    "sinusitis": "التهاب الجيوب الأنفية",
    "tension headache": "صداع التوتر",
    "urinary tract infection": "التهاب المسالك البولية",
    "viral upper respiratory infection": "عدوى فيروسية في الجهاز التنفسي العلوي",
}

# The tuple above existed with mojibake literals from an earlier bad encoding pass.
# Keep this clean UTF-8 override close to the map so Arabic symptom extraction works
# for runtime requests, not only mocked tests.
ARABIC_QUERY_HINTS = (
    ("كحة", "cough"),
    ("سعال", "cough"),
    ("بلغم", "productive cough"),
    ("نهجان", "breathing difficulty"),
    ("ضيق تنفس", "breathing difficulty"),
    ("صعوبة في التنفس", "breathing difficulty"),
    ("صفير", "wheezing"),
    ("صدر", "chest"),
    ("ألم صدر", "chest pain"),
    ("الم في الصدر", "chest pain"),
    ("ضغط في الصدر", "chest pressure"),
    ("خفقان", "palpitations"),
    ("حمى", "fever"),
    ("حرارة", "fever"),
    ("سخونية", "fever"),
    ("قيء", "vomiting"),
    ("ترجيع", "vomiting"),
    ("غثيان", "nausea"),
    ("إسهال", "diarrhea"),
    ("اسهال", "diarrhea"),
    ("إمساك", "constipation"),
    ("امساك", "constipation"),
    ("بطن", "abdominal pain"),
    ("بطني", "abdominal pain"),
    ("مغص", "abdominal pain"),
    ("ألم في البطن", "abdominal pain"),
    ("الم في البطن", "abdominal pain"),
    ("وجع بطن", "abdominal pain"),
    ("معدة", "stomach pain"),
    ("معدتي", "stomach pain"),
    ("وجع معدة", "stomach pain"),
    ("وجع شديد في معدتي", "severe stomach pain"),
    ("صداع", "headache"),
    ("دوخة", "dizziness"),
    ("دوار", "vertigo"),
    ("تنميل", "numbness"),
    ("وخز", "tingling"),
    ("ضعف", "weakness"),
    ("ظهر", "back pain"),
    ("رقبة", "neck pain"),
    ("طفح", "rash"),
    ("حكة", "itching"),
    ("حساسية", "allergy"),
    ("مدخن", "smoker"),
    ("تدخين", "smoker"),
    ("من امبارح", "since yesterday"),
    ("منذ أمس", "since yesterday"),
    ("من يوم", "1 day"),
    ("من يومين", "2 days"),
    ("من أسبوع", "1 week"),
    ("من اسبوع", "1 week"),
    ("شديد", "severe"),
    ("جامد", "severe"),
    ("خفيف", "mild"),
    ("متوسط", "moderate"),
)

SPECIALTY_AR: dict[str, str] = {
    "Cardiology": "أمراض القلب",
    "Neurology": "المخ والأعصاب",
    "Neurosurgery": "جراحة المخ والأعصاب",
    "Internal Medicine": "الباطنة",
    "Gastroenterology": "الجهاز الهضمي والكبد",
    "Dermatology": "الجلدية",
    "Psychiatry": "الطب النفسي",
    "Ophthalmology": "العيون",
    "Orthopedics": "العظام",
    "ENT": "الأنف والأذن والحنجرة",
    "Pediatrics": "الأطفال",
    "Family Medicine": "طب الأسرة",
    "Pulmonology": "أمراض الصدر والرئة",
}

RED_FLAG_AR: dict[str, str] = {
    "severe abdominal pain": "ألم شديد في البطن",
    "nausea and vomiting": "غثيان وقيء",
    "trouble breathing": "صعوبة في التنفس",
    "difficulty breathing": "صعوبة في التنفس",
    "shortness of breath": "ضيق في التنفس",
    "blue lips": "ازرقاق الشفاه",
    "coughing up blood": "كحة مصحوبة بدم",
    "chest pain": "ألم في الصدر",
    "fever": "حمى",
    "black stool": "براز أسود",
    "blood in stool": "دم في البراز",
    "blood in vomit": "قيء دموي",
}

QUESTION_AR: dict[str, tuple[str, list[str] | None]] = {
    "abdomen_location": (
        "أين تشعر بألم البطن؟",
        ["أعلى البطن", "أسفل البطن", "كل البطن", "لا يوجد"],
    ),
    "gi_red_flags": (
        "هل لديك قيء دموي أو براز أسود أو اصفرار في العين/الجلد أو علامات جفاف شديد؟",
        [
            "قيء دموي",
            "براز أسود",
            "اصفرار العين أو الجلد",
            "جفاف شديد أو قلة التبول",
            "لا يوجد",
        ],
    ),
    "gi_associated_symptoms": (
        "هل لديك غثيان أو قيء أو إسهال أو حمى أو فقدان شهية؟",
        ["غثيان أو قيء", "إسهال", "حمى", "فقدان الشهية", "لا يوجد"],
    ),
    "symptom_duration": (
        "منذ متى لديك هذه الأعراض؟",
        ["بدأت اليوم", "عدة أيام", "حوالي أسبوع", "أكثر من أسبوعين", "أشهر"],
    ),
    "symptom_severity": (
        "ما مدى شدة الأعراض بشكل عام؟",
        ["خفيفة - بالكاد ملحوظة", "متوسطة - تؤثر على الحياة اليومية", "شديدة"],
    ),
    "symptom_associated": (
        "هل لديك أي من الأعراض الإضافية التالية؟",
        ["حمى", "ألم", "صعوبة في التنفس", "غثيان أو قيء", "لا شيء مما سبق"],
    ),
    "breathing_severity": (
        "ما مدى شدة صعوبة التنفس؟",
        ["خفيفة - أستطيع الكلام بشكل طبيعي", "متوسطة - جمل قصيرة", "شديدة"],
    ),
    "breathing_onset": (
        "متى بدأت صعوبة التنفس؟",
        ["الآن أو فجأة", "خلال آخر ساعة", "خلال عدة ساعات", "تدريجياً خلال أيام"],
    ),
    "breathing_associated": (
        "هل يوجد أي من التالي مع صعوبة التنفس؟",
        [
            "ألم في الصدر",
            "صفير مع التنفس",
            "ازرقاق الشفاه أو الأصابع",
            "حمى",
            "لا يوجد",
        ],
    ),
    "cough_type": (
        "ما نوع الكحة؟",
        ["كحة جافة", "كحة ببلغم", "كحة تشبه النباح", "كحة متقطعة شديدة"],
    ),
    "cough_duration": (
        "منذ متى لديك الكحة؟",
        ["أقل من أسبوع", "أسبوع إلى أسبوعين", "أكثر من أسبوعين", "أشهر"],
    ),
    "cough_associated": (
        "هل يوجد أي من التالي مع الكحة؟",
        ["دم في البلغم", "حمى", "صعوبة في التنفس", "تعرق ليلي", "لا يوجد"],
    ),
}

QUESTION_TEXT_AR: dict[str, str] = {
    "Where do you feel the abdominal pain?": "أين تشعر بألم البطن؟",
    "Where is the abdominal discomfort strongest?": "أين يتركز ألم أو انزعاج البطن؟",
    "How long have you had these symptoms?": "منذ متى لديك هذه الأعراض؟",
    (
        "Have you noticed any changes in your bowel movements or "
        "appetite since starting to smoke?"
    ): ("هل لاحظت أي تغير في التبرز أو الشهية منذ بدأت التدخين؟"),
    "Do you experience any of the following symptoms: nausea, vomiting, or diarrhea?": (
        "هل لديك أي من الأعراض التالية: غثيان أو قيء أو إسهال؟"
    ),
}

OPTION_AR: dict[str, str] = {
    "Upper abdomen": "أعلى البطن",
    "Lower abdomen": "أسفل البطن",
    "Whole abdomen": "كل البطن",
    "None": "لا يوجد",
    "Less than 24 hours": "أقل من 24 ساعة",
    "More than 24 hours": "أكثر من 24 ساعة",
    "Not sure": "لست متأكداً",
    "No fever": "لا توجد حمى",
    "Yes, I have noticed changes": "نعم، لاحظت تغيرات",
    "No, no changes": "لا، لا توجد تغيرات",
    "I don't smoke": "أنا لا أدخن",
    "Yes - nausea and/or vomiting": "نعم - غثيان و/أو قيء",
    "Yes - diarrhea": "نعم - إسهال",
    "No": "لا",
}

ARABIC_ACTIONS: dict[TriageLevel, list[str]] = {
    "high": [
        "اطلب رعاية طارئة الآن.",
        "اتصل بالإسعاف إذا كانت الأعراض شديدة أو تزداد سوءاً.",
    ],
    "medium": [
        "يفضل زيارة طبيب أو عيادة في نفس اليوم أو في أقرب وقت.",
        "اطلب رعاية أسرع إذا ساءت الأعراض أو ظهرت أعراض جديدة.",
    ],
    "low": [
        "راقب الأعراض واهتم بالراحة والسوائل إذا كان ذلك مناسباً.",
        "احجز مراجعة عادية إذا استمرت الأعراض أو زادت أو كنت قلقاً.",
    ],
}


CONDITION_AR.update(
    {
        "appendicitis": "التهاب الزائدة الدودية",
        "cholecystitis": "التهاب المرارة",
        "dehydration": "الجفاف",
        "diverticulitis": "التهاب الرتوج",
        "food poisoning": "تسمم غذائي",
        "gastroenteritis": "نزلة معوية",
        "gastritis": "التهاب المعدة",
        "gerd": "ارتجاع المريء",
        "inflammatory bowel disease": "مرض التهاب الأمعاء",
        "inflammatory bowel disease (ibd)": "مرض التهاب الأمعاء",
        "irritable bowel syndrome": "متلازمة القولون العصبي",
        "peptic ulcer disease": "قرحة هضمية",
        "pneumonia": "التهاب رئوي",
        "acute bronchitis": "التهاب الشعب الهوائية الحاد",
        "bronchitis": "التهاب الشعب الهوائية",
        "asthma exacerbation": "نوبة ربو",
        "myocardial infarction": "احتشاء عضلة القلب",
        "tension headache": "صداع توتري",
        "migraine": "الشقيقة",
    }
)

SPECIALTY_AR.update(
    {
        "Cardiology": "أمراض القلب",
        "Neurology": "المخ والأعصاب",
        "Neurosurgery": "جراحة المخ والأعصاب",
        "Internal Medicine": "الباطنة",
        "Gastroenterology": "الجهاز الهضمي والكبد",
        "Dermatology": "الجلدية",
        "Psychiatry": "الطب النفسي",
        "Ophthalmology": "العيون",
        "Orthopedics": "العظام",
        "ENT": "الأنف والأذن والحنجرة",
        "Pediatrics": "الأطفال",
        "Family Medicine": "طب الأسرة",
        "Pulmonology": "أمراض الصدر والرئة",
    }
)

RED_FLAG_AR.update(
    {
        "severe abdominal pain": "ألم شديد في البطن",
        "abdominal pain": "ألم في البطن",
        "nausea and vomiting": "غثيان وقيء",
        "vomiting": "قيء",
        "diarrhea": "إسهال",
        "fever": "حمى",
        "black stool": "براز أسود",
        "blood in stool": "دم في البراز",
        "blood in vomit": "قيء دموي",
        "trouble breathing": "صعوبة في التنفس",
        "difficulty breathing": "صعوبة في التنفس",
        "shortness of breath": "ضيق في التنفس",
        "blue lips": "ازرقاق الشفاه",
        "coughing up blood": "كحة مصحوبة بدم",
        "chest pain": "ألم في الصدر",
    }
)

QUESTION_AR.update(
    {
        "abdomen_location": (
            "أين تشعر بألم البطن؟",
            ["أعلى البطن", "أسفل البطن", "كل البطن", "لا يوجد"],
        ),
        "gi_red_flags": (
            "هل لديك قيء دموي أو براز أسود أو اصفرار في العين/الجلد "
            "أو علامات جفاف شديد؟",
            [
                "قيء دموي",
                "براز أسود",
                "اصفرار العين أو الجلد",
                "جفاف شديد أو قلة التبول",
                "لا يوجد",
            ],
        ),
        "gi_associated_symptoms": (
            "هل لديك غثيان أو قيء أو إسهال أو حمى أو فقدان شهية؟",
            ["غثيان أو قيء", "إسهال", "حمى", "فقدان الشهية", "لا يوجد"],
        ),
        "symptom_duration": (
            "منذ متى لديك هذه الأعراض؟",
            ["بدأت اليوم", "عدة أيام", "حوالي أسبوع", "أكثر من أسبوعين", "أشهر"],
        ),
        "symptom_severity": (
            "ما مدى شدة الأعراض بشكل عام؟",
            ["خفيفة", "متوسطة", "شديدة"],
        ),
        "symptom_associated": (
            "هل لديك أي أعراض إضافية من التالية؟",
            ["حمى", "ألم", "صعوبة في التنفس", "غثيان أو قيء", "لا شيء مما سبق"],
        ),
        "breathing_severity": (
            "ما مدى شدة صعوبة التنفس؟",
            ["خفيفة", "متوسطة", "شديدة"],
        ),
        "breathing_onset": (
            "متى بدأت صعوبة التنفس؟",
            ["الآن أو فجأة", "خلال آخر ساعة", "خلال عدة ساعات", "تدريجيا خلال أيام"],
        ),
        "breathing_associated": (
            "هل يوجد أي من التالي مع صعوبة التنفس؟",
            [
                "ألم في الصدر",
                "صفير مع التنفس",
                "ازرقاق الشفاه أو الأصابع",
                "حمى",
                "لا يوجد",
            ],
        ),
        "cough_type": (
            "ما نوع الكحة؟",
            ["كحة جافة", "كحة ببلغم", "كحة تشبه النباح", "كحة متقطعة شديدة"],
        ),
        "cough_duration": (
            "منذ متى لديك الكحة؟",
            ["أقل من أسبوع", "أسبوع إلى أسبوعين", "أكثر من أسبوعين", "أشهر"],
        ),
        "cough_associated": (
            "هل يوجد أي من التالي مع الكحة؟",
            ["دم في البلغم", "حمى", "صعوبة في التنفس", "تعرق ليلي", "لا يوجد"],
        ),
    }
)

OPTION_AR.update(
    {
        "Upper abdomen": "أعلى البطن",
        "Lower abdomen": "أسفل البطن",
        "Whole abdomen": "كل البطن",
        "None": "لا يوجد",
        "Less than 24 hours": "أقل من 24 ساعة",
        "More than 24 hours": "أكثر من 24 ساعة",
        "Not sure": "لست متأكدا",
        "No fever": "لا توجد حمى",
        "Yes, I have noticed changes": "نعم، لاحظت تغيرات",
        "No, no changes": "لا، لا توجد تغيرات",
        "I don't smoke": "أنا لا أدخن",
        "Yes - nausea and/or vomiting": "نعم - غثيان و/أو قيء",
        "Yes - diarrhea": "نعم - إسهال",
        "No": "لا",
    }
)

ARABIC_ACTIONS.update(
    {
        "high": [
            "اطلب رعاية طارئة الآن.",
            "اتصل بالإسعاف إذا كانت الأعراض شديدة أو تزداد سوءا.",
        ],
        "medium": [
            "يفضل زيارة طبيب أو عيادة في نفس اليوم أو في أقرب وقت.",
            "اطلب رعاية أسرع إذا ساءت الأعراض أو ظهرت أعراض جديدة.",
        ],
        "low": [
            "راقب الأعراض واهتم بالراحة والسوائل إذا كان ذلك مناسبا.",
            "احجز مراجعة عادية إذا استمرت الأعراض أو زادت أو كنت قلقا.",
        ],
    }
)


def detect_language(query: str, requested_language: Language = "en") -> Language:
    if requested_language == "ar" or ARABIC_RE.search(query):
        return "ar"
    return "en"


def add_arabic_query_hints(query: str) -> str:
    if not ARABIC_RE.search(query):
        return query
    lowered = query.lower()
    hints = [english for arabic, english in ARABIC_QUERY_HINTS if arabic in lowered]
    if not hints:
        return query
    unique_hints = list(dict.fromkeys(hints))
    return (
        f"{query}\n\n"
        f"English clinical hints for system extraction: {', '.join(unique_hints)}"
    )


def localize_condition_name(name: str, language: Language) -> str:
    if language != "ar":
        return name
    normalized = re.sub(r"\s+", " ", name.strip().lower())
    if normalized in CONDITION_AR:
        return CONDITION_AR[normalized]
    for english, arabic in CONDITION_AR.items():
        if english in normalized:
            return arabic
    return name


def localize_specialty_name(name: str | None, language: Language) -> str:
    if not name:
        return "طب عام" if language == "ar" else "General Practice"
    if language != "ar":
        return name
    return SPECIALTY_AR.get(name, name)


def localize_red_flag(flag: str, language: Language) -> str:
    if language != "ar":
        return flag
    normalized = re.sub(r"\s+", " ", flag.strip().lower())
    if normalized in RED_FLAG_AR:
        return RED_FLAG_AR[normalized]
    for english, arabic in RED_FLAG_AR.items():
        if english in normalized:
            return arabic
    return flag


def _arabic_condition_names(response: TriageResponse) -> list[str]:
    names = [
        localize_condition_name(condition.name, "ar")
        for condition in response.suspected_conditions
        if condition.name
    ]
    return list(dict.fromkeys(names))


def _arabic_patient_explanation(response: TriageResponse) -> str:
    specialty = localize_specialty_name(response.recommended_specialty, "ar")
    conditions = _arabic_condition_names(response)
    condition_text = (
        " أو ".join(conditions[:2]) if conditions else "سبب متعلق بالأعراض المذكورة"
    )
    action = ARABIC_ACTIONS[response.urgency_level][0]
    return (
        f"الأعراض التي وصفتها قد تكون مرتبطة بـ {condition_text}. "
        f"درجة الخطورة الحالية {response.urgency_label}. "
        f"التخصص الأنسب غالباً هو {specialty}. {action}"
    )


def _arabic_clinical_summary(response: TriageResponse) -> str:
    specialty = localize_specialty_name(response.recommended_specialty, "ar")
    conditions = _arabic_condition_names(response)
    if conditions:
        return (
            f"توجد أعراض تشير إلى مشكلة ضمن تخصص {specialty}. "
            f"الاحتمالات الطبية الأبرز: {', '.join(conditions[:3])}."
        )
    return f"توجد أعراض تحتاج إلى تقييم ضمن تخصص {specialty}."


def localize_questions(
    questions: list[ClarificationQuestion],
    language: Language,
) -> list[ClarificationQuestion]:
    if language != "ar":
        return questions

    localized: list[ClarificationQuestion] = []
    for question in questions:
        mapped = QUESTION_AR.get(question.id)
        if mapped:
            localized.append(
                ClarificationQuestion(
                    id=question.id,
                    question=mapped[0],
                    options=mapped[1] if mapped[1] is not None else question.options,
                )
            )
            continue

        localized.append(
            ClarificationQuestion(
                id=question.id,
                question=QUESTION_TEXT_AR.get(question.question, question.question),
                options=(
                    [OPTION_AR.get(option, option) for option in question.options]
                    if question.options
                    else None
                ),
            )
        )
    return localized


def localize_triage_response(
    response: TriageResponse, language: Language
) -> TriageResponse:
    if language != "ar":
        return response

    localized = response.model_copy(deep=True)
    localized.urgency_label = {
        "low": "منخفضة",
        "medium": "متوسطة",
        "high": "عالية",
    }[localized.urgency_level]
    localized.actions = ARABIC_ACTIONS[localized.urgency_level]
    localized.recommended_actions = ARABIC_ACTIONS[localized.urgency_level]
    localized.disclaimer = (
        "هذا ليس بديلاً عن الاستشارة الطبية. إذا كنت تعتقد أن لديك حالة طارئة، "
        "اطلب الرعاية الطبية فوراً."
    )
    localized.questions = localize_questions(localized.questions, language)
    localized.red_flags = [
        localize_red_flag(flag, language) for flag in localized.red_flags
    ]

    localized.suspected_condition = (
        localize_condition_name(localized.suspected_condition, language)
        if localized.suspected_condition
        else localized.suspected_condition
    )

    localized.suspected_conditions = deepcopy(localized.suspected_conditions)
    for condition in localized.suspected_conditions:
        condition.name = localize_condition_name(condition.name, language)
        condition.explanation = ""

    localized.patient_friendly_explanation = _arabic_patient_explanation(localized)
    localized.plain_language_explanation = localized.patient_friendly_explanation
    localized.simple_reasoning = localized.patient_friendly_explanation
    localized.clinical_summary = _arabic_clinical_summary(localized)
    localized.summary = localized.clinical_summary
    localized.urgency_reason = localized.clinical_summary
    specialty_name = localize_specialty_name(localized.recommended_specialty, language)
    localized.specialty_reason = (
        f"تم اختيار تخصص {specialty_name} "
        "لأنه الأنسب للأعراض والاحتمالات الطبية الظاهرة."
    )
    localized.supporting_references = []

    return localized
