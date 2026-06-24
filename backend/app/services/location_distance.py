from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

ALEXANDRIA_AREA_COORDS: dict[str, tuple[float, float]] = {
    "abu qir": (31.3190, 30.0606),
    "agami": (31.0950, 29.7600),
    "azarita": (31.2001, 29.9187),
    "bolkly": (31.2317, 29.9555),
    "cleopatra": (31.2198, 29.9427),
    "fleming": (31.2350, 29.9620),
    "gleem": (31.2325, 29.9587),
    "ibrahimia": (31.2106, 29.9278),
    "kafr abdo": (31.2245, 29.9510),
    "loran": (31.2456, 29.9703),
    "mandara": (31.2880, 30.0160),
    "miami": (31.2704, 29.9955),
    "moharam bek": (31.1816, 29.9080),
    "raml station": (31.2000, 29.9010),
    "roushdy": (31.2298, 29.9498),
    "san stefano": (31.2450, 29.9660),
    "sidi beshr": (31.2613, 29.9843),
    "sidi gaber": (31.2187, 29.9425),
    "smouha": (31.2072, 29.9637),
    "sporting": (31.2156, 29.9370),
    "stanley": (31.2388, 29.9579),
    "victoria": (31.2780, 30.0000),
}


def normalize_location(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().split())


def canonical_alexandria_area(value: str | None) -> str:
    normalized = normalize_location(value)
    if not normalized:
        return ""
    aliases = {
        "smouha": ("smoha",),
        "loran": ("laurent",),
        "sidi gaber": ("sidy gaber",),
        "sidi beshr": ("sidy beshr",),
        "roushdy": ("rushdy", "roshdy"),
        "azarita": ("azareeta", "el azarita", "el-azarita"),
        "bolkly": ("bulkly", "bokly"),
    }
    for canonical, variants in aliases.items():
        if normalized == canonical or normalized in variants:
            return canonical
    for area in ALEXANDRIA_AREA_COORDS:
        if area in normalized:
            return area
    return normalized


def split_location(value: str | None) -> tuple[str, str]:
    normalized = normalize_location(value)
    if not normalized:
        return "", ""
    parts = [
        normalize_location(part) for part in normalized.replace(",", "-").split("-")
    ]
    parts = [part for part in parts if part]
    if len(parts) >= 2:
        first, second = parts[0], parts[1]
        if first == "alexandria":
            return first, canonical_alexandria_area(second)
        if second == "alexandria":
            return second, canonical_alexandria_area(first)
    if normalized == "alexandria":
        return "alexandria", ""
    return normalized, ""


def coordinates_for_location(
    *,
    city: str | None = None,
    area: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> tuple[float, float] | None:
    if latitude is not None and longitude is not None:
        return latitude, longitude
    if normalize_location(city) != "alexandria":
        return None
    area_key = canonical_alexandria_area(area)
    return ALEXANDRIA_AREA_COORDS.get(area_key)


def distance_km(
    first: tuple[float, float] | None,
    second: tuple[float, float] | None,
) -> float | None:
    if first is None or second is None:
        return None
    lat1, lon1 = first
    lat2, lon2 = second
    radius_km = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    return round(2 * radius_km * asin(sqrt(a)), 1)
