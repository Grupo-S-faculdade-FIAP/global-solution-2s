"""Geolocalização de alertas SNS — região NASA → centro e filtro por raio."""

from __future__ import annotations

import math

from app.core.config import settings
from app.services.sns_region_cooldown import extract_region_from_s3_key
from app.services.storm_alerts_query import REGION_COORDS, _region_key

# Aliases curtos em chaves S3 (sem prefixo nasa_)
_REGION_ALIASES: dict[str, str] = {
    "brasil_sudeste": "nasa_brasil_sudeste",
    "centro_oeste": "nasa_centro_oeste",
    "leste_litoral": "nasa_leste_litoral",
    "nordeste": "nasa_nordeste",
    "norte": "nasa_norte",
    "sul": "nasa_sul",
    "oeste": "nasa_oeste",
    "brasil": "nasa_brasil",
    "americas": "nasa_americas",
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância em km entre dois pontos (WGS84)."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def is_within_radius(
    sub_lat: float,
    sub_lon: float,
    storm_lat: float,
    storm_lon: float,
    radius_km: float | None = None,
) -> bool:
    """True se o inscrito está dentro do raio de alerta."""
    limit = radius_km if radius_km is not None else settings.SNS_ALERT_RADIUS_KM
    return haversine_km(sub_lat, sub_lon, storm_lat, storm_lon) <= limit


def storm_location_from_s3_key(key: str) -> tuple[float, float] | None:
    """Centro lat/lon da região inferida pela chave S3, ou None se indeterminado."""
    if not key or not key.strip():
        return None

    if extract_region_from_s3_key(key):
        return coords_from_s3_key_safe(key)

    normalized = key.lower()
    for slug, coords in REGION_COORDS.items():
        if slug in normalized:
            return coords

    for alias, canonical in _REGION_ALIASES.items():
        if alias in normalized:
            return REGION_COORDS.get(canonical)

    return None


def coords_from_s3_key_safe(key: str) -> tuple[float, float] | None:
    """Coordenadas por heurística de nome, sem fallback genérico."""
    region = _region_key(key or "")
    coords = REGION_COORDS.get(region)
    if coords is None:
        return None
    # _region_key defaults unknown keys to nasa_brasil — only accept if key hints a region
    normalized = (key or "").lower()
    if region == "nasa_brasil" and not any(
        token in normalized
        for token in ("nasa_", "brasil", "sudeste", "nordeste", "centro", "litoral", "norte", "sul", "oeste")
    ):
        return None
    return coords
