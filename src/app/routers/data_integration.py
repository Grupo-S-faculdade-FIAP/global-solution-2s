"""Data integration endpoints for weather, storms, and risk prediction."""

from datetime import datetime
from typing import List
from fastapi import APIRouter, Query, HTTPException
from app.services.weather_service import WeatherService
from app.models.schemas import (
    WeatherResponse,
    StormsResponse,
    StormDetection,
    RiskForecast,
    MapOverlayResponse,
    GeoJSONFeature,
    GeoJSONGeometry,
    GeoJSONProperties,
)

router = APIRouter()
weather_service = WeatherService()


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
        # TODO: Query DynamoDB storm_detections table
        # For now, return empty list (T-04 not yet implemented)
        detections: List[dict] = []
        
        return detections
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
        # TODO: Query DynamoDB and build GeoJSON
        # For now, return empty feature collection
        features: List[GeoJSONFeature] = []
        
        return MapOverlayResponse(
            type="FeatureCollection",
            features=features
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating map overlay: {str(e)}"
        )
