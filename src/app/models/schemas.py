"""Pydantic models for data integration API responses."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ─── Weather Response ─────────────────────────────────────────────────────
class WeatherResponse(BaseModel):
    """Response model for /weather/current endpoint."""
    temperature: float = Field(..., description="Temperature in Celsius")
    humidity: float = Field(..., description="Relative humidity (0-100%)")
    pressure: float = Field(..., description="Atmospheric pressure (hPa)")
    wind_speed: float = Field(..., description="Wind speed (m/s)")
    wind_direction: float = Field(..., description="Wind direction (0-360°)")
    precipitation: float = Field(..., description="Precipitation (mm)")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "temperature": 28.5,
                "humidity": 75,
                "pressure": 1013.25,
                "wind_speed": 12.3,
                "wind_direction": 180,
                "precipitation": 2.5,
                "timestamp": "2026-06-02T10:00:00Z"
            }
        }


# ─── Storm Detection Response ─────────────────────────────────────────────
class StormDetection(BaseModel):
    """Single storm detection record."""
    detection_id: str = Field(..., description="Unique detection ID")
    latitude: float = Field(..., description="Latitude of detection")
    longitude: float = Field(..., description="Longitude of detection")
    confidence: float = Field(..., description="Detection confidence (0-1)")
    timestamp: str = Field(..., description="ISO 8601 timestamp of detection")


class StormsResponse(BaseModel):
    """Response model for /storms/recent endpoint."""
    detections: List[StormDetection] = Field(default_factory=list)
    total_count: int = Field(...)
    
    class Config:
        schema_extra = {
            "example": {
                "detections": [
                    {
                        "detection_id": "det_001",
                        "latitude": -22.89,
                        "longitude": -43.18,
                        "confidence": 0.85,
                        "timestamp": "2026-06-02T10:00:00Z"
                    }
                ],
                "total_count": 1
            }
        }


# ─── Risk Forecast Response ──────────────────────────────────────────────
class RiskForecast(BaseModel):
    """Response model for /risk/forecast endpoint."""
    risk_score: float = Field(..., description="Risk score (0-1)")
    risk_category: str = Field(..., description="Risk category: LOW, MEDIUM, or HIGH")
    recommendation: str = Field(..., description="Actionable recommendation")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "risk_score": 0.65,
                "risk_category": "MEDIUM",
                "recommendation": "Monitor weather conditions closely. Prepare emergency response protocols.",
                "timestamp": "2026-06-02T10:00:00Z"
            }
        }


# ─── Map Overlay (GeoJSON) ──────────────────────────────────────────────
class GeoJSONProperties(BaseModel):
    """Properties for GeoJSON features."""
    type: str = Field(..., description="Feature type: storm, weather, risk")
    intensity: Optional[float] = Field(None, description="Intensity value")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


class GeoJSONGeometry(BaseModel):
    """GeoJSON geometry."""
    type: str = Field(..., description="Geometry type (Point, etc.)")
    coordinates: List[float] = Field(..., description="[longitude, latitude]")


class GeoJSONFeature(BaseModel):
    """Single GeoJSON feature."""
    type: str = Field(default="Feature")
    properties: GeoJSONProperties
    geometry: GeoJSONGeometry


class MapOverlayResponse(BaseModel):
    """Response model for /map/overlay endpoint."""
    type: str = Field(default="FeatureCollection")
    features: List[GeoJSONFeature] = Field(default_factory=list)
    
    class Config:
        schema_extra = {
            "example": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "type": "storm",
                            "intensity": 0.85,
                            "timestamp": "2026-06-02T10:00:00Z"
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": [-43.18, -22.89]
                        }
                    }
                ]
            }
        }


# ─── Error Response ──────────────────────────────────────────────────────
class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
