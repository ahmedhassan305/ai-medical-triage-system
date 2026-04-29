export const MEDICAL_SPECIALTY_GROUPS = [
  {
    label: "Internal Medicine",
    scopes: [
      "General Internal Medicine",
      "Endocrinology",
      "Rheumatology",
      "Infectious Diseases",
      "Geriatric Medicine",
    ],
  },
  {
    label: "Cardiology",
    scopes: [
      "General Cardiology",
      "Interventional Cardiology",
      "Electrophysiology",
      "Heart Failure",
    ],
  },
  {
    label: "Neurology",
    scopes: [
      "General Neurology",
      "Stroke Medicine",
      "Epilepsy",
      "Headache Medicine",
    ],
  },
  {
    label: "Neurosurgery",
    scopes: [
      "General Neurosurgery",
      "Spine Surgery",
      "Brain Tumor Surgery",
      "Functional Neurosurgery",
    ],
  },
  {
    label: "Gastroenterology",
    scopes: [
      "General Gastroenterology",
      "Endoscopy",
      "Hepatology",
      "IBD Care",
    ],
  },
  {
    label: "Dermatology",
    scopes: ["General Dermatology", "Cosmetic Dermatology", "Dermatosurgery"],
  },
  {
    label: "Psychiatry",
    scopes: [
      "Adult Psychiatry",
      "Child Psychiatry",
      "Addiction Psychiatry",
      "Psychotherapy",
    ],
  },
  {
    label: "Ophthalmology",
    scopes: ["General Ophthalmology", "Retina", "Cornea", "Pediatric Ophthalmology"],
  },
  {
    label: "Orthopedics",
    scopes: ["General Orthopedics", "Sports Injury", "Joint Replacement", "Spine"],
  },
  {
    label: "ENT",
    scopes: ["General ENT", "Rhinology", "Otology", "Laryngology"],
  },
  {
    label: "Pediatrics",
    scopes: ["General Pediatrics", "Pediatric Chest", "Pediatric Neurology"],
  },
  {
    label: "Family Medicine",
    scopes: ["General Family Medicine", "Primary Care", "Chronic Disease Follow-up"],
  },
  {
    label: "Pulmonology",
    scopes: ["General Pulmonology", "Allergy", "Sleep Medicine"],
  },
] as const;

export function splitDoctorSpecialty(value: string): {
  primarySpecialty: string;
  specialtyScope: string;
} {
  const [primarySpecialty, specialtyScope] = value.split(" - ", 2);
  return {
    primarySpecialty: primarySpecialty || "",
    specialtyScope: specialtyScope || "",
  };
}

export function composeDoctorSpecialty(
  primarySpecialty: string,
  specialtyScope: string,
): string {
  const primary = primarySpecialty.trim();
  const scope = specialtyScope.trim();
  if (!primary) {
    return "";
  }
  return scope ? `${primary} - ${scope}` : primary;
}
