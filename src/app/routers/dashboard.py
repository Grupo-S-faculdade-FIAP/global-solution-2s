"""Dashboard router — status e clima da região (proxy para WeatherService)."""

from fastapi import APIRouter, Query, HTTPException

from app.services.external_api_rate_limit import ExternalApiRateLimitExceeded
from app.services.weather_service import WeatherService

router = APIRouter()
_weather = WeatherService()


@router.get("/status")
def dashboard_status() -> dict:
    return {"module": "dashboard", "status": "ready"}


@router.get("/climate/current")
def get_current_climate(
    lat: float = Query(-23.55, ge=-90, le=90, description="Latitude"),
    lon: float = Query(-46.63, ge=-180, le=180, description="Longitude"),
) -> dict:
    """Retorna clima atual da região selecionada (Open-Meteo)."""
    try:
        data = _weather.get_current(lat, lon)
        return {"data": data, "source": "open-meteo"}
    except ExternalApiRateLimitExceeded:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Erro ao buscar clima: {exc}") from exc
