"""Data integration endpoints for weather, storms, risk prediction and analytics."""

from typing import List
from fastapi import APIRouter, Query, HTTPException, Body
from pydantic import BaseModel, Field
from app.core.config import settings
from app.services.weather_service import WeatherService
from app.services.alerts_analytics import AlertAnalyticsService
from app.services.storm_alerts_query import StormAlertsQueryService
from app.services.storm_alerts_store import add_alert_from_coords, use_mock_store
from app.models.schemas import (
    WeatherResponse,
    RiskForecast,
    MapOverlayResponse,
    GeoJSONFeature,
)

router = APIRouter()
weather_service = WeatherService()
alert_analytics_service = AlertAnalyticsService()
storm_alerts_service = StormAlertsQueryService()


# ─── Helper Functions ────────────────────────────────────────────────────
def validate_coordinates(lat: float, lon: float) -> None:
    """Validate latitude and longitude ranges."""
    if not (-90 <= lat <= 90):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid latitude: {lat}. Must be between -90 and 90."
        )
    if not (-180 <= lon <= 180):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid longitude: {lon}. Must be between -180 and 180."
        )


def parse_bbox(bbox_str: str) -> tuple[float, float, float, float]:
    """Parse bbox string 'south,west,north,east' into tuple."""
    try:
        parts = [float(x) for x in bbox_str.split(",")]
        if len(parts) != 4:
            raise ValueError("bbox must have 4 values")
        south, west, north, east = parts
        return south, west, north, east
    except (ValueError, IndexError):
        raise HTTPException(
            status_code=400,
            detail="Invalid bbox format. Use: 'south,west,north,east' (e.g., '-25,-50,-20,-40')"
        )


# ─── Endpoints ──────────────────────────────────────────────────────────

@router.get(
    "/weather/current",
    response_model=WeatherResponse,
    tags=["Weather"],
    summary="Get current weather",
    description="Fetch current weather data from Open-Meteo API for a location"
)
def get_weather_current(
    lat: float = Query(..., description="Latitude (-90 to 90)"),
    lon: float = Query(..., description="Longitude (-180 to 180)")
) -> WeatherResponse:
    """
    Get current weather for a location.
    
    **Parameters:**
    - `lat`: Latitude (-90 to 90)
    - `lon`: Longitude (-180 to 180)
    
    **Returns:**
    - Temperature (°C)
    - Humidity (%)
    - Pressure (hPa)
    - Wind speed (m/s)
    - Wind direction (°)
    - Precipitation (mm)
    """
    validate_coordinates(lat, lon)
    
    try:
        weather_data = weather_service.get_current(lat, lon)
        
        return WeatherResponse(
            temperature=weather_data["temperature"],
            humidity=weather_data["humidity"],
            pressure=weather_data["pressure"],
            wind_speed=weather_data["wind_speed"],
            wind_direction=weather_data["wind_direction"],
            precipitation=weather_data["precipitation"],
            timestamp=weather_data["timestamp"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching weather data: {str(e)}"
        )


@router.get(
    "/storms/recent",
    response_model=List[dict],
    tags=["Storms"],
    summary="Get recent storm detections",
    description="Fetch recent storm detections from the database"
)
def get_storms_recent(
    hours: int = Query(24, ge=1, le=720, description="Hours to look back (1-720)")
) -> List[dict]:
    """
    Get recent storm detections.
    
    **Parameters:**
    - `hours`: Hours to look back (default: 24, max: 30 days)
    
    **Returns:**
    - Array of storm detection records with:
      - detection_id
      - latitude
      - longitude
      - confidence (0-1)
      - timestamp
    
    **Note:** This endpoint queries DynamoDB storm_detections table.
    Returns empty list if no detections found (feature not yet integrated).
    """
    if hours < 1 or hours > 720:
        raise HTTPException(
            status_code=400,
            detail="hours must be between 1 and 720"
        )
    
    try:
        return storm_alerts_service.recent_detections(hours=hours)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching storm detections: {str(e)}"
        )


@router.get(
    "/risk/forecast",
    response_model=RiskForecast,
    tags=["Risk"],
    summary="Get risk forecast",
    description="Fetch risk forecast for a location"
)
def get_risk_forecast(
    lat: float = Query(..., description="Latitude (-90 to 90)"),
    lon: float = Query(..., description="Longitude (-180 to 180)")
) -> RiskForecast:
    """
    Get risk forecast for a location.
    
    **Parameters:**
    - `lat`: Latitude (-90 to 90)
    - `lon`: Longitude (-180 to 180)
    
    **Returns:**
    - risk_score: 0-1 scale
    - risk_category: LOW, MEDIUM, or HIGH
    - recommendation: Actionable advice
    """
    validate_coordinates(lat, lon)

    try:
        from app.services.risk_assessment import RiskAssessmentService
        service = RiskAssessmentService()
        resultado = service.calculate_risk(lat, lon)
        return RiskForecast(
            risk_score=resultado.score,
            risk_category=resultado.category,
            recommendation=resultado.recommendation,
            timestamp=resultado.timestamp,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating risk forecast: {str(e)}"
        )


@router.get(
    "/map/overlay",
    response_model=MapOverlayResponse,
    tags=["Map"],
    summary="Get map overlay data",
    description="Fetch GeoJSON features for map overlay (storms, weather, risk)"
)
def get_map_overlay(
    bbox: str = Query(..., description="Bounding box: 'south,west,north,east'")
) -> MapOverlayResponse:
    """
    Get GeoJSON features for map overlay.
    
    **Parameters:**
    - `bbox`: Bounding box as 'south,west,north,east'
      - Example: '-25,-50,-20,-40' for São Paulo region
    
    **Returns:**
    - FeatureCollection with GeoJSON features
    - Features include storms, weather stations, risk zones
    """
    south, west, north, east = parse_bbox(bbox)
    
    # Validate bbox
    if south > north or west > east:
        raise HTTPException(
            status_code=400,
            detail="Invalid bbox: south must be <= north, west must be <= east"
        )
    
    try:
        hours = 24 * 7
        features = storm_alerts_service.map_overlay_features(
            south, west, north, east, hours=hours
        )
        return MapOverlayResponse(
            type="FeatureCollection",
            features=features,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating map overlay: {str(e)}"
        )


class SimulateAlertRequest(BaseModel):
    """Corpo para simular alerta local (sem DynamoDB AWS)."""
    confidence: float = Field(0.85, ge=0.0, le=1.0)
    lat: float = Field(-23.55, ge=-90, le=90)
    lon: float = Field(-46.63, ge=-180, le=180)


@router.post(
    "/alerts/simulate",
    tags=["Analytics"],
    summary="Simulate storm alert (local store)",
    description="Grava alerta simulado em data/demo/storm_alerts.json quando DynamoDB mock está ativo",
)
def post_simulate_alert(body: SimulateAlertRequest = Body(...)) -> dict:
    item = add_alert_from_coords(body.lat, body.lon, body.confidence)
    return {
        "success": True,
        "mock_mode": use_mock_store(),
        "alert": item,
        "message": "Alerta simulado registrado",
    }


@router.get(
    "/alerts/status",
    tags=["Analytics"],
    summary="Alert storage mode",
)
def get_alerts_storage_status() -> dict:
    return {
        "mock_mode": use_mock_store(),
        "store": "local_json" if use_mock_store() else "dynamodb",
        "table": settings.DYNAMODB_TABLE_ALERTS if not use_mock_store() else "data/demo/storm_alerts.json",
    }


@router.get(
    "/alerts/weekly",
    response_model=dict[str, int],
    tags=["Analytics"],
    summary="Get weekly alerts distribution",
    description="Aggregates storm alerts by day of week from DynamoDB"
)
def get_alerts_weekly(
    days: int = Query(30, ge=1, le=365, description="Days to look back")
) -> dict[str, int]:
    try:
        return alert_analytics_service.weekly_alerts(days=days)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error aggregating weekly alerts: {str(e)}"
        )


@router.get(
    "/alerts/hourly",
    response_model=dict[str, int],
    tags=["Analytics"],
    summary="Get hourly alerts distribution",
    description="Aggregates storm alerts by hour from DynamoDB"
)
def get_alerts_hourly(
    days: int = Query(30, ge=1, le=365, description="Days to look back")
) -> dict[str, int]:
    try:
        return alert_analytics_service.hourly_alerts(days=days)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error aggregating hourly alerts: {str(e)}"
        )
