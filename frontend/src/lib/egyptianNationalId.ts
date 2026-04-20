const GOVERNORATE_CODES: Record<string, string> = {
  "01": "Cairo",
  "02": "Alexandria",
  "03": "Port Said",
  "04": "Suez",
  "11": "Damietta",
  "12": "Dakahlia",
  "13": "Sharqia",
  "14": "Qalyubia",
  "15": "Kafr El Sheikh",
  "16": "Gharbia",
  "17": "Monufia",
  "18": "Beheira",
  "19": "Ismailia",
  "21": "Giza",
  "22": "Beni Suef",
  "23": "Faiyum",
  "24": "Minya",
  "25": "Asyut",
  "26": "Sohag",
  "27": "Qena",
  "28": "Aswan",
  "29": "Luxor",
  "31": "Red Sea",
  "32": "New Valley",
  "33": "Matrouh",
  "34": "North Sinai",
  "35": "South Sinai",
  "88": "Outside Egypt",
};

const CENTURIES: Record<string, number> = {
  "2": 1900,
  "3": 2000,
};

export type ParsedEgyptianNationalId = {
  nationalId: string;
  dateOfBirth: string;
  age: number;
  governorateCode: string;
  governorate: string;
};

export function parseEgyptianNationalId(
  rawValue: string,
): ParsedEgyptianNationalId | null {
  const nationalId = rawValue.trim();
  if (!/^\d{14}$/.test(nationalId)) {
    return null;
  }

  const century = CENTURIES[nationalId[0]];
  if (!century) {
    return null;
  }

  const year = century + Number(nationalId.slice(1, 3));
  const month = Number(nationalId.slice(3, 5));
  const day = Number(nationalId.slice(5, 7));
  const date = new Date(Date.UTC(year, month - 1, day));
  if (
    Number.isNaN(date.getTime()) ||
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== month - 1 ||
    date.getUTCDate() !== day
  ) {
    return null;
  }

  const governorateCode = nationalId.slice(7, 9);
  const governorate = GOVERNORATE_CODES[governorateCode];
  if (!governorate) {
    return null;
  }

  return {
    nationalId,
    dateOfBirth: date.toISOString().slice(0, 10),
    age: calculateAge(date),
    governorateCode,
    governorate,
  };
}

function calculateAge(dateOfBirth: Date): number {
  const today = new Date();
  let years = today.getFullYear() - dateOfBirth.getUTCFullYear();
  const beforeBirthday =
    today.getMonth() < dateOfBirth.getUTCMonth() ||
    (today.getMonth() === dateOfBirth.getUTCMonth() &&
      today.getDate() < dateOfBirth.getUTCDate());
  if (beforeBirthday) {
    years -= 1;
  }
  return years;
}
