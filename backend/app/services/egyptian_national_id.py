from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

NATIONAL_ID_PATTERN = re.compile(r"^\d{14}$")

GOVERNORATE_CODES: dict[str, str] = {
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
}

CENTURY_MAP = {
    "2": 1900,
    "3": 2000,
}


@dataclass(frozen=True)
class EgyptianNationalIdInfo:
    national_id: str
    date_of_birth: date
    inferred_governorate_code: str
    inferred_governorate: str


def parse_egyptian_national_id(raw_value: str) -> EgyptianNationalIdInfo:
    national_id = raw_value.strip()
    if not NATIONAL_ID_PATTERN.fullmatch(national_id):
        raise ValueError("National ID must contain exactly 14 digits.")

    century_digit = national_id[0]
    century = CENTURY_MAP.get(century_digit)
    if century is None:
        raise ValueError(
            "National ID century digit must correspond to a supported birth century."
        )

    year = century + int(national_id[1:3])
    month = int(national_id[3:5])
    day = int(national_id[5:7])
    try:
        date_of_birth = date(year, month, day)
    except ValueError as exc:
        raise ValueError("National ID contains an invalid birth date.") from exc

    governorate_code = national_id[7:9]
    governorate = GOVERNORATE_CODES.get(governorate_code)
    if governorate is None:
        raise ValueError(
            "National ID contains an unknown or unsupported governorate code."
        )

    return EgyptianNationalIdInfo(
        national_id=national_id,
        date_of_birth=date_of_birth,
        inferred_governorate_code=governorate_code,
        inferred_governorate=governorate,
    )


def calculate_age(date_of_birth: date, today: date | None = None) -> int:
    reference_day = today or date.today()
    years = reference_day.year - date_of_birth.year
    birthday_has_passed = (reference_day.month, reference_day.day) >= (
        date_of_birth.month,
        date_of_birth.day,
    )
    return years if birthday_has_passed else years - 1
