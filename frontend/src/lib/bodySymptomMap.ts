import type { BodyDiagramTriageRequestDto, BodyRegionDto } from "../api/dto";

export type BodyRegionOption = {
  id: BodyRegionDto;
  label: string;
  symptoms: string[];
};

export const BODY_REGION_OPTIONS: BodyRegionOption[] = [
  {
    id: "head",
    label: "Head",
    symptoms: [
      "headache",
      "dizziness",
      "fainting",
      "confusion",
      "vision changes",
      "scalp pain",
      "head injury",
    ],
  },
  {
    id: "face",
    label: "Face",
    symptoms: [
      "facial swelling",
      "facial pain",
      "jaw pain",
      "one-sided drooping",
      "tooth pain",
      "sinus pressure",
    ],
  },
  {
    id: "neck",
    label: "Neck",
    symptoms: [
      "neck pain",
      "stiff neck",
      "swollen glands",
      "trouble swallowing",
      "neck swelling",
      "pain after injury",
    ],
  },
  {
    id: "chest",
    label: "Chest",
    symptoms: [
      "chest pain",
      "chest pressure",
      "shortness of breath",
      "palpitations",
      "wheezing",
      "cough",
      "pain with breathing",
    ],
  },
  {
    id: "abdomen",
    label: "Abdomen",
    symptoms: [
      "abdominal pain",
      "nausea",
      "vomiting",
      "diarrhea",
      "constipation",
      "bloating",
      "yellow eyes or skin",
      "blood in stool",
    ],
  },
  {
    id: "pelvis_urinary",
    label: "Pelvis/Urinary",
    symptoms: [
      "painful urination",
      "frequent urination",
      "pelvic pain",
      "blood in urine",
      "testicular pain",
      "vaginal bleeding",
      "urinary retention",
    ],
  },
  {
    id: "back",
    label: "Back",
    symptoms: [
      "lower back pain",
      "upper back pain",
      "pain spreading to leg",
      "numbness or tingling",
      "weakness",
      "loss of bladder control",
      "pain after lifting",
    ],
  },
  {
    id: "shoulder",
    label: "Shoulder",
    symptoms: [
      "shoulder pain",
      "reduced movement",
      "swelling",
      "pain after injury",
      "numbness",
      "pain spreading from neck",
    ],
  },
  {
    id: "arm",
    label: "Arm",
    symptoms: [
      "arm pain",
      "weakness",
      "numbness or tingling",
      "swelling",
      "injury",
      "pain spreading from chest",
    ],
  },
  {
    id: "hand_wrist",
    label: "Hand/Wrist",
    symptoms: [
      "wrist pain",
      "hand pain",
      "numb fingers",
      "swelling",
      "reduced grip",
      "injury",
      "skin redness",
    ],
  },
  {
    id: "hip",
    label: "Hip",
    symptoms: [
      "hip pain",
      "pain when walking",
      "reduced movement",
      "pain after fall",
      "groin pain",
      "swelling",
    ],
  },
  {
    id: "leg",
    label: "Leg",
    symptoms: [
      "leg pain",
      "leg swelling",
      "calf pain",
      "numbness or tingling",
      "weakness",
      "redness or warmth",
      "injury",
    ],
  },
  {
    id: "knee",
    label: "Knee",
    symptoms: [
      "knee pain",
      "swelling",
      "locking or catching",
      "cannot bear weight",
      "pain after injury",
      "reduced movement",
    ],
  },
  {
    id: "foot_ankle",
    label: "Foot/Ankle",
    symptoms: [
      "ankle pain",
      "foot pain",
      "swelling",
      "cannot bear weight",
      "numbness",
      "wound",
      "pain after twisting",
    ],
  },
  {
    id: "skin",
    label: "Skin",
    symptoms: [
      "rash",
      "itching",
      "hives",
      "swelling",
      "blisters",
      "skin infection",
      "allergic reaction",
      "wound",
    ],
  },
];

export const COMMON_ASSOCIATED_SYMPTOMS = [
  "fever",
  "vomiting",
  "sweating",
  "shortness of breath",
  "pain spreading to left arm",
  "jaw pain",
  "confusion",
  "one-sided weakness",
  "vision loss",
  "blood in stool",
  "loss of bladder or bowel control",
  "breathing difficulty",
];

export function summarizeBodyDiagramInput(
  payload: BodyDiagramTriageRequestDto,
): string {
  const region =
    BODY_REGION_OPTIONS.find((option) => option.id === payload.selected_body_region)
      ?.label ?? payload.selected_body_region;
  const associated = payload.associated_symptoms.length
    ? ` Associated symptoms: ${payload.associated_symptoms.join(", ")}.`
    : "";
  const freeText = payload.patient_free_text.trim()
    ? ` ${payload.patient_free_text.trim()}`
    : "";
  return (
    `${region}: ${payload.main_symptoms.join(", ")}. ` +
    `Severity ${payload.severity}, onset ${payload.onset}, duration ${payload.duration}.` +
    associated +
    freeText
  ).trim();
}
