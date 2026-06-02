"""Lambda function: Ingest weather data from Open-Meteo API into DynamoDB.

Trigger: CloudWatch Events (every 30 minutes)
Upstream: Open-Meteo API
Downstream: DynamoDB table (weather_metrics)

Flow:
1. Get list of target locations
2. For each location, call Open-Meteo API via WeatherService
3. Format each response as weather metric
4. Store in DynamoDB
5. Return summary (success count, error count)
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any

import boto3

from src.app.services.weather_service import WeatherService

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration
WEATHER_TABLE_NAME = os.getenv("WEATHER_TABLE_NAME", "weather_metrics")
TTL_DAYS = 90  # Retention period for DynamoDB records

# Default locations to monitor (lat, lon, name)
DEFAULT_LOCATIONS = [
    (-23.5505, -46.6333, "São Paulo"),
    (-22.9068, -43.1729, "Rio de Janeiro"),
    (-15.8267, -47.8711, "Brasília"),
    (-30.0346, -51.2177, "Porto Alegre"),
    (-9.9794, -49.8623, "Palmas"),
]


class WeatherMetricsRepository:
    """Repository for weather metrics in DynamoDB."""
    
    def __init__(self, table_name: str = WEATHER_TABLE_NAME):
        """Initialize repository.
        
        Args:
            table_name: DynamoDB table name
        """
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)
        
    def put_item(self, item: Dict[str, Any]) -> None:
        """Store weather metric in DynamoDB.
        
        Args:
            item: Weather metric dict (must include pk, sk, timestamp, ttl)
        """
        try:
            self.table.put_item(Item=item)
            logger.info(f"Stored metric: {item['pk']}")
        except Exception as e:
            logger.error(f"Failed to store metric: {str(e)}")
            raise


def format_weather_metric(
    weather: Dict[str, Any],
    lat: float,
    lon: float
) -> Dict[str, Any]:
    """Format weather data as DynamoDB metric item.
    
    Args:
        weather: Weather data from WeatherService.get_current()
        lat: Latitude
        lon: Longitude
        
    Returns:
        Formatted DynamoDB item with pk, sk, TTL, etc.
    """
    timestamp = weather.get("timestamp", datetime.now().isoformat())
    
    # Parse timestamp to compute TTL (Unix timestamp)
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    ttl_timestamp = int((dt + timedelta(days=TTL_DAYS)).timestamp())
    
    # Partition key: timestamp#location
    pk = f"{timestamp}#lat-{lat}_lon-{lon}"
    
    # Sort key: metric type (for querying all metrics for a location/time)
    sk = "weather"
    
    return {
        "pk": pk,
        "sk": sk,
        "timestamp": timestamp,
        "latitude": lat,
        "longitude": lon,
        "temperature": weather["temperature"],
        "humidity": weather["humidity"],
        "pressure": weather["pressure"],
        "wind_speed": weather["wind_speed"],
        "wind_direction": weather["wind_direction"],
        "precipitation": weather["precipitation"],
        "source": "open_meteo",
        "ttl": ttl_timestamp
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler: Ingest weather data from Open-Meteo.
    
    Args:
        event: CloudWatch Events trigger (not used, scheduled)
        context: Lambda context
        
    Returns:
        AWS Lambda response with statusCode and body
    """
    logger.info("Starting weather ingestion Lambda")
    
    service = WeatherService()
    repository = WeatherMetricsRepository()
    
    success_count = 0
    error_count = 0
    errors = []
    
    # Fetch weather for each location
    for lat, lon, location_name in DEFAULT_LOCATIONS:
        try:
            logger.info(f"Fetching weather for {location_name} ({lat}, {lon})")
            
            # Get weather from Open-Meteo
            weather = service.get_current(lat=lat, lon=lon)
            
            # Format for DynamoDB
            metric = format_weather_metric(weather, lat, lon)
            
            # Store in DynamoDB
            repository.put_item(metric)
            
            success_count += 1
            logger.info(f"✓ Stored weather for {location_name}")
            
        except Exception as e:
            error_count += 1
            error_msg = f"{location_name}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"✗ Failed to ingest weather for {location_name}: {str(e)}")
    
    # Prepare response
    body = {
        "timestamp": datetime.now().isoformat(),
        "locations_processed": len(DEFAULT_LOCATIONS),
        "records_stored": success_count,
        "errors": error_count,
        "error_details": errors if errors else None
    }
    
    # Determine status code
    # 200: all success
    # 207: partial success (some errors)
    # 500: all failed
    if error_count == 0:
        status_code = 200
    elif success_count > 0:
        status_code = 207
    else:
        status_code = 500
    
    response = {
        "statusCode": status_code,
        "body": json.dumps(body)
    }
    
    logger.info(f"Weather ingestion completed: {success_count}/{len(DEFAULT_LOCATIONS)} success")
    return response
