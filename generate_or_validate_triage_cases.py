from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.specialties import TRIAGE_SPECIALTIES  # noqa: E402

DATASET_PATH = ROOT / "triage_eval_all_specialties_cases.json"
DIFFICULTIES = ("easy", "medium", "hard", "common_language", "controversial")
URGENCY_VALUES = {"HIGH", "MEDIUM", "LOW"}
REQUIRED_KEYS = {
    "case_id",
    "specialty_group",
    "difficulty",
    "patient_age",
    "patient_gender",
    "input_text",
    "expected_specialty",
    "expected_urgency",
    "expected_condition_hint",
    "red_flags_present",
    "reason_for_label",
    "clarification_answers",
}

PREFIXES = {
    "Cardiology": "CARD",
    "Neurology": "NEUR",
    "Neurosurgery": "NSGY",
    "Internal Medicine": "IMED",
    "Gastroenterology": "GAST",
    "Dermatology": "DERM",
    "Psychiatry": "PSYC",
    "Ophthalmology": "OPHT",
    "Orthopedics": "ORTH",
    "ENT": "ENT",
    "Pediatrics": "PEDS",
    "Family Medicine": "FAM",
    "Pulmonology": "PULM",
}

GENDERS = ("female", "male")
ADULT_AGES = (24, 31, 42, 55, 68)
PEDIATRIC_AGES = (1, 3, 5, 8, 12)
TIMES = {
    "LOW": ("for three days", "منذ ثلاثة أيام", "بقاله تلات أيام", "For three days"),
    "MEDIUM": ("since yesterday", "منذ أمس", "من امبارح", "Since yesterday"),
    "HIGH": ("today", "اليوم", "النهارده", "Today"),
}

DIFFICULTY_NOTES = {
    "easy": (
        "The main symptom is clear and focused.",
        "العرض الرئيسي واضح ومحدد.",
        "العرض الأساسي واضح.",
        "Clear symptom pattern.",
    ),
    "medium": (
        "There are a few extra symptoms, but the main pattern is still present.",
        "توجد أعراض إضافية قليلة لكن النمط الأساسي واضح.",
        "فيه أعراض زيادة بس الصورة الأساسية لسه واضحة.",
        "Some overlap is present.",
    ),
    "hard": (
        "The wording is vague and the symptom could be confused with another cause.",
        "الوصف غير محدد وقد يختلط بسبب آخر.",
        "الكلام مش محدد وممكن يتلخبط مع سبب تاني.",
        "Vague presentation.",
    ),
    "common_language": (
        "I am describing it in everyday language, not medical terms.",
        "أصف ذلك بكلام بسيط وليس بمصطلحات طبية.",
        "بوصفها بكلام عادي مش مصطلحات طبية.",
        "Everyday language.",
    ),
    "controversial": (
        "It may sound like another problem, but the risk pattern still matters.",
        "قد يبدو الأمر كسبب آخر لكن نمط الخطورة مهم.",
        "ممكن تبان حاجة تانية بس نمط الخطر مهم.",
        "Overlapping presentation.",
    ),
}

CONCEPTS: dict[str, list[dict[str, Any]]] = {
    "Cardiology": [
        {
            "en": "chest pressure when walking upstairs that improves with rest",
            "ar": "ضغط في الصدر مع صعود السلم ويخف مع الراحة",
            "eg": "ضغط في صدري لما أطلع السلم وبيهدى مع الراحة",
            "urgency": "MEDIUM",
            "hint": "possible exertional angina",
            "reason": "Exertional chest pressure suggests a cardiac cause without collapse or severe ongoing pain.",
        },
        {
            "en": "fast irregular heartbeat with lightheadedness",
            "ar": "خفقان سريع وغير منتظم مع دوخة",
            "eg": "قلبي بيدق بسرعة ومش منتظم ومعاه دوخة",
            "urgency": "MEDIUM",
            "hint": "possible arrhythmia",
            "reason": "Palpitations with lightheadedness need prompt assessment.",
        },
        {
            "en": "crushing chest pain with sweating and nausea",
            "ar": "ألم ضاغط شديد في الصدر مع عرق وغثيان",
            "eg": "وجع جامد ضاغط في صدري مع عرق وغثيان",
            "urgency": "HIGH",
            "hint": "possible acute coronary syndrome",
            "reason": "Severe chest pain with sweating is a high-risk pattern.",
            "red_flag": True,
        },
        {
            "en": "ankle swelling and breathlessness when lying flat",
            "ar": "تورم في الكاحل وضيق نفس عند الاستلقاء",
            "eg": "رجلي وارمة وبنهج لما أنام على ضهري",
            "urgency": "MEDIUM",
            "hint": "possible heart failure symptoms",
            "reason": "Fluid symptoms with breathlessness suggest a cardiovascular cause.",
        },
    ],
    "Neurology": [
        {
            "en": "sudden face drooping with weakness in one arm",
            "ar": "ميل مفاجئ في الوجه مع ضعف في ذراع واحد",
            "eg": "وشي مال فجأة ودراعي ناحية واحدة ضعيف",
            "urgency": "HIGH",
            "hint": "possible stroke",
            "reason": "Sudden one-sided weakness is a neurologic emergency red flag.",
            "red_flag": True,
        },
        {
            "en": "the worst headache of my life with neck stiffness",
            "ar": "أسوأ صداع في حياتي مع تيبس في الرقبة",
            "eg": "أفظع صداع جالي في حياتي ورقبتي ناشفة",
            "urgency": "HIGH",
            "hint": "possible serious acute headache",
            "reason": "Thunderclap-type severe headache with neck stiffness is high risk.",
            "red_flag": True,
        },
        {
            "en": "spinning dizziness when turning in bed",
            "ar": "دوخة دوران عند التقلب في السرير",
            "eg": "الدنيا بتلف بيا لما أتقلب في السرير",
            "urgency": "LOW",
            "hint": "possible positional vertigo",
            "reason": "Brief positional spinning without neurologic deficits is usually lower urgency.",
        },
        {
            "en": "recurrent headache with flashing lights before it starts",
            "ar": "صداع متكرر يسبقه أضواء لامعة",
            "eg": "صداع بيرجع ومعاه لمعات في عيني قبل ما يبدأ",
            "urgency": "LOW",
            "hint": "possible migraine with aura",
            "reason": "Recurrent aura-like headache without red flags is lower urgency.",
        },
    ],
    "Neurosurgery": [
        {
            "en": "low back pain with new weakness down one leg",
            "ar": "ألم أسفل الظهر مع ضعف جديد نازل في ساق واحدة",
            "eg": "وجع أسفل ضهري ومعاه ضعف جديد نازل في رجل واحدة",
            "urgency": "HIGH",
            "hint": "possible nerve compression",
            "reason": "New limb weakness with back pain can indicate urgent nerve compression.",
            "red_flag": True,
        },
        {
            "en": "neck pain with numbness and weakness in one hand",
            "ar": "ألم في الرقبة مع تنميل وضعف في يد واحدة",
            "eg": "رقبتي واجعاني وإيدي بتنمل وضعفت",
            "urgency": "MEDIUM",
            "hint": "possible cervical nerve compression",
            "reason": "Neck pain with neurologic arm symptoms needs specialist assessment.",
        },
        {
            "en": "back pain with trouble controlling urine",
            "ar": "ألم في الظهر مع صعوبة في التحكم في البول",
            "eg": "ضهري واجعني ومش عارف أتحكم في البول كويس",
            "urgency": "HIGH",
            "hint": "possible cauda equina syndrome",
            "reason": "Bladder control symptoms with back pain are emergency red flags.",
            "red_flag": True,
        },
        {
            "en": "pain shooting from the back to the foot with numb toes",
            "ar": "ألم ممتد من الظهر إلى القدم مع تنميل الأصابع",
            "eg": "وجع نازل من ضهري لحد رجلي وصوابع رجلي بتنمل",
            "urgency": "MEDIUM",
            "hint": "possible lumbar radiculopathy",
            "reason": "Radiating back pain with sensory symptoms suggests nerve root involvement.",
        },
    ],
    "Internal Medicine": [
        {
            "en": "fever with chills, body aches, and marked fatigue",
            "ar": "حمى مع رعشة وتكسير في الجسم وإرهاق واضح",
            "eg": "سخونية ورعشة وتكسير في جسمي وتعب جامد",
            "urgency": "MEDIUM",
            "hint": "possible systemic infection",
            "reason": "Fever with systemic symptoms needs general medical assessment.",
        },
        {
            "en": "unexplained weight loss with night sweats",
            "ar": "نقصان وزن غير مفسر مع تعرق ليلي",
            "eg": "بخس من غير سبب وبعرق بالليل",
            "urgency": "MEDIUM",
            "hint": "possible systemic illness",
            "reason": "Constitutional symptoms need broad medical evaluation.",
        },
        {
            "en": "high fever with confusion and extreme weakness",
            "ar": "حرارة عالية مع تشوش شديد وضعف عام",
            "eg": "سخونية عالية ومتلخبط وتعبان جدا",
            "urgency": "HIGH",
            "hint": "possible severe infection",
            "reason": "Confusion with high fever is a high-risk systemic red flag.",
            "red_flag": True,
        },
        {
            "en": "very thirsty all the time with frequent urination and weight loss",
            "ar": "عطش شديد طوال الوقت مع تبول متكرر ونقصان وزن",
            "eg": "عطشان طول الوقت وبدخل الحمام كتير وبخس",
            "urgency": "MEDIUM",
            "hint": "possible diabetes symptoms",
            "reason": "Polyuria, thirst, and weight loss suggest a metabolic issue.",
        },
    ],
    "Gastroenterology": [
        {
            "en": "upper abdominal pain with repeated vomiting",
            "ar": "ألم أعلى البطن مع قيء متكرر",
            "eg": "وجع فوق بطني ومعاه ترجيع كتير",
            "urgency": "MEDIUM",
            "hint": "possible acute digestive inflammation",
            "reason": "Persistent abdominal pain with vomiting needs timely evaluation.",
        },
        {
            "en": "yellow eyes with dark urine and abdominal swelling",
            "ar": "اصفرار العين مع بول داكن وانتفاخ في البطن",
            "eg": "عيني صفرا والبول غامق وبطني منفوخة",
            "urgency": "HIGH",
            "hint": "possible serious liver or bile duct disease",
            "reason": "Jaundice with abdominal swelling and dark urine is high risk.",
            "red_flag": True,
        },
        {
            "en": "burning pain after meals with sour taste in my mouth",
            "ar": "حرقان بعد الأكل مع طعم حامض في الفم",
            "eg": "حرقان بعد الأكل وطعم حامض في بقي",
            "urgency": "LOW",
            "hint": "possible reflux",
            "reason": "Meal-related burning without red flags is usually lower urgency.",
        },
        {
            "en": "black stool with dizziness and stomach discomfort",
            "ar": "براز أسود مع دوخة وانزعاج في المعدة",
            "eg": "البراز أسود ومعاه دوخة ووجع في معدتي",
            "urgency": "HIGH",
            "hint": "possible gastrointestinal bleeding",
            "reason": "Black stool with dizziness suggests possible bleeding.",
            "red_flag": True,
        },
    ],
    "Dermatology": [
        {
            "en": "itchy red patches on both arms",
            "ar": "بقع حمراء مثيرة للحكة على الذراعين",
            "eg": "بقع حمرا بتاكلني على دراعاتي",
            "urgency": "LOW",
            "hint": "possible eczema or dermatitis",
            "reason": "Localized itchy rash without systemic symptoms is lower urgency.",
        },
        {
            "en": "red warm painful patch spreading on my leg with fever",
            "ar": "منطقة حمراء ساخنة ومؤلمة تنتشر في الساق مع حمى",
            "eg": "حتة حمرا وسخنة وبتوجع في رجلي وبتكبر ومعاها سخونية",
            "urgency": "MEDIUM",
            "hint": "possible skin infection",
            "reason": "Spreading painful redness with fever needs same-day assessment.",
        },
        {
            "en": "new blisters and peeling skin after a rash started",
            "ar": "فقاعات جديدة وتقشر في الجلد بعد ظهور طفح",
            "eg": "طلعلي فقاقيع والجلد بيقشر بعد طفح",
            "urgency": "HIGH",
            "hint": "possible severe blistering reaction",
            "reason": "Blistering and peeling skin can be a severe skin red flag.",
            "red_flag": True,
        },
        {
            "en": "a mole changed shape and sometimes bleeds",
            "ar": "شامة تغير شكلها وأحيانا تنزف",
            "eg": "حسنة شكلها اتغير وساعات بتنزل دم",
            "urgency": "MEDIUM",
            "hint": "possible concerning pigmented lesion",
            "reason": "Changing or bleeding lesion warrants prompt skin evaluation.",
        },
    ],
    "Psychiatry": [
        {
            "en": "sudden panic episodes with racing thoughts and chest tightness",
            "ar": "نوبات هلع مفاجئة مع أفكار متسارعة وضيق في الصدر",
            "eg": "نوبات فزع فجأة وأفكاري بتجري وصدري مقفول",
            "urgency": "MEDIUM",
            "hint": "possible panic attacks",
            "reason": "Panic symptoms need mental health assessment after considering safety.",
        },
        {
            "en": "low mood, poor sleep, and loss of interest for weeks",
            "ar": "مزاج منخفض وقلة نوم وفقدان اهتمام منذ أسابيع",
            "eg": "مزاجي وحش ومش بنام وفاقد الاهتمام من أسابيع",
            "urgency": "LOW",
            "hint": "possible depressive symptoms",
            "reason": "Persistent low mood without immediate self-harm is lower urgent but important.",
        },
        {
            "en": "thoughts of ending my life and I feel unsafe alone",
            "ar": "أفكار لإنهاء حياتي وأشعر أنني غير آمن وحدي",
            "eg": "عندي أفكار إني أنهي حياتي ومش آمن لوحدي",
            "urgency": "HIGH",
            "hint": "possible suicidal crisis",
            "reason": "Self-harm thoughts with feeling unsafe require emergency response.",
            "red_flag": True,
        },
        {
            "en": "hearing voices and feeling people are trying to harm me",
            "ar": "أسمع أصواتا وأشعر أن الناس تحاول إيذائي",
            "eg": "بسمع أصوات وحاسس إن الناس عايزة تأذيني",
            "urgency": "MEDIUM",
            "hint": "possible psychosis symptoms",
            "reason": "Hallucinations and paranoia need prompt mental health evaluation.",
        },
    ],
    "Ophthalmology": [
        {
            "en": "red painful eye with strong light sensitivity",
            "ar": "عين حمراء مؤلمة مع حساسية شديدة للضوء",
            "eg": "عيني حمرا وبتوجعني والنور مضايقني جدا",
            "urgency": "MEDIUM",
            "hint": "possible eye inflammation",
            "reason": "Painful red eye with light sensitivity needs urgent eye assessment.",
        },
        {
            "en": "sudden loss of vision in one eye",
            "ar": "فقدان مفاجئ للرؤية في عين واحدة",
            "eg": "نظري راح فجأة في عين واحدة",
            "urgency": "HIGH",
            "hint": "possible acute vision emergency",
            "reason": "Sudden vision loss is an emergency red flag.",
            "red_flag": True,
        },
        {
            "en": "flashes, new floaters, and a curtain over part of vision",
            "ar": "ومضات وأجسام عائمة جديدة وستارة على جزء من الرؤية",
            "eg": "بشوف ومضات وحاجات عايمة وستارة على جزء من نظري",
            "urgency": "HIGH",
            "hint": "possible retinal detachment",
            "reason": "Curtain-like visual loss with flashes and floaters is high risk.",
            "red_flag": True,
        },
        {
            "en": "itchy watery eyes after dust exposure",
            "ar": "حكة ودموع في العين بعد التعرض للغبار",
            "eg": "عيني بتاكلني وبتدمع بعد التراب",
            "urgency": "LOW",
            "hint": "possible allergic conjunctivitis",
            "reason": "Itchy watery eyes after irritant exposure are usually lower urgency.",
        },
    ],
    "Orthopedics": [
        {
            "en": "knee pain and swelling after twisting it while playing",
            "ar": "ألم وتورم في الركبة بعد التواء أثناء اللعب",
            "eg": "ركبتي وجعتني وورمت بعد ما اتلوت وأنا بلعب",
            "urgency": "MEDIUM",
            "hint": "possible knee ligament or meniscus injury",
            "reason": "Traumatic knee swelling suggests musculoskeletal injury needing assessment.",
        },
        {
            "en": "shoulder pain after lifting something heavy",
            "ar": "ألم في الكتف بعد رفع شيء ثقيل",
            "eg": "كتفي واجعني بعد ما شيلت حاجة تقيلة",
            "urgency": "LOW",
            "hint": "possible shoulder strain",
            "reason": "Localized pain after lifting without deformity is lower urgency.",
        },
        {
            "en": "severe wrist pain with swelling after falling on my hand",
            "ar": "ألم شديد في الرسغ مع تورم بعد السقوط على اليد",
            "eg": "رسغي واجعني جامد ووارم بعد ما وقعت على إيدي",
            "urgency": "MEDIUM",
            "hint": "possible fracture or sprain",
            "reason": "Fall with severe swelling may indicate fracture and needs prompt evaluation.",
        },
        {
            "en": "lower back pain after exercise without leg weakness",
            "ar": "ألم أسفل الظهر بعد التمرين دون ضعف في الساق",
            "eg": "وجع أسفل ضهري بعد التمرين ومفيش ضعف في رجلي",
            "urgency": "LOW",
            "hint": "possible lumbar muscle strain",
            "reason": "Back pain after strain without neurologic red flags is lower urgency.",
        },
    ],
    "ENT": [
        {
            "en": "ear pain with reduced hearing and fever",
            "ar": "ألم في الأذن مع ضعف السمع وحمى",
            "eg": "ودني واجعاني والسمع قل ومعايا سخونية",
            "urgency": "MEDIUM",
            "hint": "possible ear infection",
            "reason": "Ear pain with fever and hearing change needs focused assessment.",
        },
        {
            "en": "sore throat with painful swallowing",
            "ar": "التهاب في الحلق مع ألم عند البلع",
            "eg": "زوري واجعني والبلع بيوجع",
            "urgency": "LOW",
            "hint": "possible throat infection",
            "reason": "Sore throat without airway symptoms is usually lower urgency.",
        },
        {
            "en": "facial pressure with blocked nose and thick discharge",
            "ar": "ضغط في الوجه مع انسداد الأنف وإفرازات سميكة",
            "eg": "وشي ضاغط ومناخيري مسدودة وفيه إفرازات تقيلة",
            "urgency": "LOW",
            "hint": "possible sinusitis",
            "reason": "Sinus pressure with congestion is usually non-emergency.",
        },
        {
            "en": "nosebleed that keeps coming back and makes me dizzy",
            "ar": "نزيف أنف متكرر يسبب لي دوخة",
            "eg": "مناخيري بتنزل دم كتير وبتدوخني",
            "urgency": "MEDIUM",
            "hint": "possible significant nosebleed",
            "reason": "Recurrent bleeding with dizziness needs prompt evaluation.",
        },
    ],
    "Pediatrics": [
        {
            "en": "my baby has fever and is too sleepy to feed well",
            "ar": "طفلي لديه حمى ونعاس شديد ولا يرضع جيدا",
            "eg": "البيبي عنده سخونية ونايم كتير ومش بيرضع كويس",
            "urgency": "HIGH",
            "hint": "possible serious infant illness",
            "reason": "Fever with poor feeding in a young child is high risk.",
            "red_flag": True,
        },
        {
            "en": "my child has a barking cough and noisy breathing",
            "ar": "طفلي لديه كحة تشبه النباح وتنفس بصوت",
            "eg": "ابني عنده كحة زي النباح ونفسه بصوت",
            "urgency": "MEDIUM",
            "hint": "possible croup-like illness",
            "reason": "Noisy breathing in a child needs timely pediatric assessment.",
        },
        {
            "en": "my child is wheezing and breathing fast",
            "ar": "طفلي يصدر صفيرا ويتنفس بسرعة",
            "eg": "ابني بيزيق ونفسه سريع",
            "urgency": "HIGH",
            "hint": "possible acute breathing difficulty in a child",
            "reason": "Fast breathing and wheeze in a child can worsen quickly.",
            "red_flag": True,
        },
        {
            "en": "my child has vomiting and has not passed urine for many hours",
            "ar": "طفلي يتقيأ ولم يتبول لساعات طويلة",
            "eg": "ابني بيرجع ومادخلش الحمام من ساعات كتير",
            "urgency": "HIGH",
            "hint": "possible dehydration in a child",
            "reason": "Vomiting with prolonged no urination suggests dehydration risk.",
            "red_flag": True,
        },
    ],
    "Family Medicine": [
        {
            "en": "runny nose, mild sore throat, and low fever",
            "ar": "رشح والتهاب حلق خفيف وحرارة بسيطة",
            "eg": "رشح وزوري واجعني شوية وسخونية بسيطة",
            "urgency": "LOW",
            "hint": "possible common viral illness",
            "reason": "Mild upper respiratory symptoms fit primary care triage.",
        },
        {
            "en": "general tiredness with mild body aches and no severe symptom",
            "ar": "إرهاق عام مع آلام بسيطة في الجسم دون عرض شديد",
            "eg": "تعب عام وتكسير بسيط ومفيش حاجة شديدة",
            "urgency": "LOW",
            "hint": "possible nonspecific viral or fatigue syndrome",
            "reason": "Broad mild symptoms without red flags are suitable for primary care.",
        },
        {
            "en": "low-grade fever and cough after being around sick coworkers",
            "ar": "حرارة بسيطة وكحة بعد مخالطة زملاء مرضى",
            "eg": "سخونية بسيطة وكحة بعد ما قعدت مع ناس عيانة",
            "urgency": "LOW",
            "hint": "possible mild respiratory infection",
            "reason": "Mild contagious-illness symptoms without breathing distress are low urgency.",
        },
        {
            "en": "multiple mild symptoms and I am not sure which one matters most",
            "ar": "عدة أعراض خفيفة ولا أعرف أيها الأهم",
            "eg": "عندي كذا عرض خفيف ومش عارف أهم حاجة فيهم إيه",
            "urgency": "LOW",
            "hint": "general primary-care assessment",
            "reason": "Unfocused mild symptoms without red flags fit broad primary care.",
        },
    ],
    "Pulmonology": [
        {
            "en": "chest tightness with wheezing and shortness of breath",
            "ar": "ضيق في الصدر مع صفير وضيق نفس",
            "eg": "صدري مقفول وفيه تزييق وبنهج",
            "urgency": "MEDIUM",
            "hint": "possible bronchospasm",
            "reason": "Wheezing and breathlessness suggest lower airway involvement.",
        },
        {
            "en": "productive cough with fever and pain when breathing deeply",
            "ar": "كحة ببلغم مع حمى وألم عند النفس العميق",
            "eg": "كحة ببلغم وسخونية ووجع لما آخد نفس عميق",
            "urgency": "MEDIUM",
            "hint": "possible chest infection",
            "reason": "Fever with productive cough and pleuritic discomfort needs evaluation.",
        },
        {
            "en": "coughing blood with shortness of breath",
            "ar": "كحة مصحوبة بدم مع ضيق نفس",
            "eg": "بكح دم ومعاه نهجان",
            "urgency": "HIGH",
            "hint": "possible serious respiratory bleeding",
            "reason": "Coughing blood with breathlessness is a high-risk respiratory red flag.",
            "red_flag": True,
        },
        {
            "en": "longstanding cough and getting breathless walking short distances",
            "ar": "كحة مستمرة وضيق نفس عند المشي لمسافة قصيرة",
            "eg": "كحة بقالها فترة وبنهج من مشوار قصير",
            "urgency": "MEDIUM",
            "hint": "possible chronic airway disease",
            "reason": "Chronic cough with exertional breathlessness fits respiratory evaluation.",
        },
    ],
}


def render_input(concept: dict[str, Any], difficulty: str, variant: int) -> str:
    urgency = concept["urgency"]
    time_en, time_ar, time_eg, time_alt = TIMES[urgency]
    note_en, note_ar, note_eg, note_alt = DIFFICULTY_NOTES[difficulty]
    if variant == 0:
        return f"{concept['en']} {time_en}. {note_en}"
    if variant == 1:
        return f"أشعر بـ {concept['ar']} {time_ar}. {note_ar}"
    if variant == 2:
        return f"{concept['eg']} {time_eg}. {note_eg}"
    if variant == 3:
        return f"عندي {concept['ar']} with {concept['en']} {time_en}. {note_en}"
    return f"{time_alt}, I noticed {concept['en']}. {note_alt}"


def build_clarification_answers(
    concept: dict[str, Any], difficulty: str
) -> list[dict[str, str]]:
    urgency = concept["urgency"]
    duration = {
        "HIGH": "Started today or became severe today",
        "MEDIUM": "Started yesterday or has been worsening recently",
        "LOW": "Present for a few days and not rapidly worsening",
    }[urgency]
    severity = {"HIGH": "Severe", "MEDIUM": "Moderate", "LOW": "Mild"}[urgency]
    red_flags = (
        "Yes, the concerning feature is already described in the main message"
        if concept.get("red_flag")
        else "No major danger signs beyond the symptoms already described"
    )
    progression = {
        "easy": "The symptom pattern is stable and easy to describe",
        "medium": "The symptom is noticeable and needs timely review",
        "hard": "The symptom is unclear but still concerning for the expected body system",
        "common_language": "The symptom is described in everyday wording",
        "controversial": "There are overlapping symptoms but the expected pattern remains important",
    }[difficulty]
    return [
        {"question_id": "duration", "answer": duration},
        {"question_id": "severity", "answer": severity},
        {"question_id": "onset", "answer": duration},
        {"question_id": "progression", "answer": progression},
        {"question_id": "associated_symptoms", "answer": concept["en"]},
        {"question_id": "red_flags", "answer": red_flags},
    ]


def build_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for specialty in TRIAGE_SPECIALTIES:
        concepts = CONCEPTS[specialty]
        prefix = PREFIXES[specialty]
        ages = PEDIATRIC_AGES if specialty == "Pediatrics" else ADULT_AGES
        for difficulty in DIFFICULTIES:
            serial = 1
            for concept_index, concept in enumerate(concepts):
                for variant in range(5):
                    cases.append(
                        {
                            "case_id": f"{prefix}_{difficulty.upper()}_{serial:03d}",
                            "specialty_group": specialty,
                            "difficulty": difficulty,
                            "patient_age": ages[(concept_index + variant) % len(ages)],
                            "patient_gender": GENDERS[
                                (concept_index + variant) % len(GENDERS)
                            ],
                            "input_text": render_input(concept, difficulty, variant),
                            "expected_specialty": specialty,
                            "expected_urgency": concept["urgency"],
                            "expected_condition_hint": concept["hint"],
                            "red_flags_present": bool(concept.get("red_flag", False)),
                            "reason_for_label": concept["reason"],
                            "clarification_answers": build_clarification_answers(
                                concept, difficulty
                            ),
                        }
                    )
                    serial += 1
    return cases


def load_cases(path: Path = DATASET_PATH) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("Dataset root must be a JSON array.")
    return data


def specialty_name_in_text(text: str) -> str | None:
    lowered = text.lower()
    for specialty in TRIAGE_SPECIALTIES:
        pattern = rf"\b{re.escape(specialty.lower())}\b"
        if re.search(pattern, lowered):
            return specialty
    return None


def validate_cases(cases: list[dict[str, Any]]) -> None:
    errors: list[str] = []
    ids: set[str] = set()
    inputs: set[str] = set()
    by_specialty = Counter()
    by_difficulty = Counter()
    by_urgency = Counter()
    by_specialty_difficulty = Counter()

    forbidden_patterns = {
        "imaging": re.compile(
            r"\b(ct|mri|x-?ray|scan|image|imaging)\b|أشعة|رنين|تصوير", re.I
        ),
        "treatment_advice": re.compile(
            r"\b(take|use|dose|antibiotic|ibuprofen|paracetamol|treatment)\b|"
            r"خذ|استخدم|جرعة|مضاد حيوي|علاج",
            re.I,
        ),
    }

    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            errors.append(f"Case {index} is not an object.")
            continue
        missing = REQUIRED_KEYS - set(case)
        extra = set(case) - REQUIRED_KEYS
        if missing:
            errors.append(f"Case {index} is missing keys: {sorted(missing)}")
        if extra:
            errors.append(f"Case {index} has extra keys: {sorted(extra)}")

        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"Case {index} has an invalid case_id.")
        elif case_id in ids:
            errors.append(f"Duplicate case_id: {case_id}")
        else:
            ids.add(case_id)

        specialty = case.get("expected_specialty")
        group = case.get("specialty_group")
        if specialty not in TRIAGE_SPECIALTIES:
            errors.append(f"{case_id}: invalid expected_specialty {specialty!r}")
        if group != specialty:
            errors.append(f"{case_id}: specialty_group must equal expected_specialty.")

        difficulty = case.get("difficulty")
        if difficulty not in DIFFICULTIES:
            errors.append(f"{case_id}: invalid difficulty {difficulty!r}")

        urgency = case.get("expected_urgency")
        if urgency not in URGENCY_VALUES:
            errors.append(f"{case_id}: invalid expected_urgency {urgency!r}")

        age = case.get("patient_age")
        if not isinstance(age, int) or not 0 <= age <= 120:
            errors.append(f"{case_id}: patient_age must be an integer from 0 to 120.")
        if case.get("patient_gender") not in {"female", "male", "other"}:
            errors.append(f"{case_id}: patient_gender is invalid.")
        if not isinstance(case.get("red_flags_present"), bool):
            errors.append(f"{case_id}: red_flags_present must be boolean.")
        clarification_answers = case.get("clarification_answers")
        if not isinstance(clarification_answers, list) or not clarification_answers:
            errors.append(f"{case_id}: clarification_answers must be a non-empty list.")
        else:
            seen_answer_ids: set[str] = set()
            for answer_index, answer in enumerate(clarification_answers, start=1):
                if not isinstance(answer, dict):
                    errors.append(
                        f"{case_id}: clarification_answers[{answer_index}] "
                        "must be an object."
                    )
                    continue
                if set(answer) != {"question_id", "answer"}:
                    errors.append(
                        f"{case_id}: clarification_answers[{answer_index}] "
                        "must contain question_id and answer only."
                    )
                question_id = answer.get("question_id")
                answer_text = answer.get("answer")
                if not isinstance(question_id, str) or not question_id.strip():
                    errors.append(
                        f"{case_id}: clarification_answers[{answer_index}] "
                        "has an invalid question_id."
                    )
                elif question_id in seen_answer_ids:
                    errors.append(
                        f"{case_id}: duplicate clarification answer id {question_id!r}."
                    )
                else:
                    seen_answer_ids.add(question_id)
                if not isinstance(answer_text, str) or not answer_text.strip():
                    errors.append(
                        f"{case_id}: clarification_answers[{answer_index}] "
                        "has an invalid answer."
                    )

        for key in (
            "input_text",
            "expected_condition_hint",
            "reason_for_label",
        ):
            if not isinstance(case.get(key), str) or not case[key].strip():
                errors.append(f"{case_id}: {key} must be a non-empty string.")

        text = str(case.get("input_text", ""))
        normalized_input = re.sub(r"\s+", " ", text.strip().lower())
        if normalized_input in inputs:
            errors.append(f"{case_id}: duplicate input_text.")
        inputs.add(normalized_input)

        direct_specialty = specialty_name_in_text(text)
        if direct_specialty is not None:
            errors.append(
                f"{case_id}: input_text includes specialty name {direct_specialty!r}."
            )
        for label, pattern in forbidden_patterns.items():
            if pattern.search(text):
                errors.append(
                    f"{case_id}: input_text includes forbidden {label} reference."
                )

        by_specialty[specialty] += 1
        by_difficulty[difficulty] += 1
        by_urgency[urgency] += 1
        by_specialty_difficulty[(specialty, difficulty)] += 1

    for specialty in TRIAGE_SPECIALTIES:
        if by_specialty[specialty] != 100:
            errors.append(
                f"{specialty}: expected 100 cases, found {by_specialty[specialty]}."
            )
        for difficulty in DIFFICULTIES:
            count = by_specialty_difficulty[(specialty, difficulty)]
            if count != 20:
                errors.append(
                    f"{specialty}/{difficulty}: expected 20 cases, found {count}."
                )

    if errors:
        error_text = "\n".join(f"- {error}" for error in errors[:80])
        if len(errors) > 80:
            error_text += f"\n- ... {len(errors) - 80} more errors"
        raise ValueError(f"Validation failed with {len(errors)} errors:\n{error_text}")

    print("Discovered specialties:")
    for specialty in TRIAGE_SPECIALTIES:
        print(f"- {specialty}")
    print(f"\nTotal cases: {len(cases)}")
    print("\nCounts by specialty:")
    for specialty in TRIAGE_SPECIALTIES:
        print(f"- {specialty}: {by_specialty[specialty]}")
    print("\nCounts by difficulty:")
    for difficulty in DIFFICULTIES:
        print(f"- {difficulty}: {by_difficulty[difficulty]}")
    print("\nCounts by urgency:")
    for urgency in ("HIGH", "MEDIUM", "LOW"):
        print(f"- {urgency}: {by_urgency[urgency]}")


def write_dataset(path: Path = DATASET_PATH) -> None:
    cases = build_cases()
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(cases, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate or validate triage specialty/urgency evaluation cases."
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Regenerate triage_eval_all_specialties_cases.json before validating.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Fail if the dataset file does not already exist.",
    )
    args = parser.parse_args()

    if args.generate or (not args.validate_only and not DATASET_PATH.exists()):
        write_dataset(DATASET_PATH)
        print(f"Wrote {DATASET_PATH.name}")

    cases = load_cases(DATASET_PATH)
    validate_cases(cases)


if __name__ == "__main__":
    main()
