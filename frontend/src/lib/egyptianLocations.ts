export const EGYPTIAN_GOVERNORATES = [
  "Alexandria",
  "Aswan",
  "Asyut",
  "Beheira",
  "Beni Suef",
  "Cairo",
  "Dakahlia",
  "Damietta",
  "Faiyum",
  "Gharbia",
  "Giza",
  "Ismailia",
  "Kafr El Sheikh",
  "Luxor",
  "Matrouh",
  "Minya",
  "Monufia",
  "New Valley",
  "North Sinai",
  "Port Said",
  "Qalyubia",
  "Qena",
  "Red Sea",
  "Sharqia",
  "Sohag",
  "South Sinai",
  "Suez",
  "Outside Egypt",
];

export const ALEXANDRIA_AREAS = [
  "Abu Qir",
  "Agami",
  "Azarita",
  "Bacchus",
  "Bolkly",
  "Camp Caesar",
  "Cleopatra",
  "Downtown",
  "Fleming",
  "Gleem",
  "Ibrahimia",
  "Kafr Abdo",
  "Loran",
  "Mandara",
  "Miami",
  "Moharam Bek",
  "Raml Station",
  "Roushdy",
  "San Stefano",
  "Sidi Beshr",
  "Sidi Gaber",
  "Smouha",
  "Sporting",
  "Stanley",
  "Victoria",
];

export function splitResidenceLocation(value: string | null | undefined): {
  governorate: string;
  area: string;
} {
  const rawValue = (value ?? "").trim();
  if (!rawValue) {
    return { governorate: "", area: "" };
  }

  const [first, second] = rawValue
    .split(/\s+-\s+|,\s*/)
    .map((part) => part.trim())
    .filter(Boolean);

  if (first === "Alexandria" && second) {
    return { governorate: first, area: second };
  }
  if (second === "Alexandria" && first) {
    return { governorate: second, area: first };
  }
  return { governorate: rawValue, area: "" };
}

export function composeResidenceLocation(
  governorate: string,
  area: string,
): string {
  const normalizedGovernorate = governorate.trim();
  const normalizedArea = area.trim();
  if (normalizedGovernorate === "Alexandria" && normalizedArea) {
    return `${normalizedGovernorate} - ${normalizedArea}`;
  }
  return normalizedGovernorate;
}
