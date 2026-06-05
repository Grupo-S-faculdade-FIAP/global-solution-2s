"""Unit tests for OpenMeteoClient (mocked HTTP)."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from app.clients.openmeteo import OpenMeteoClient, clear_openmeteo_cache
from weather_fixtures import OPENMETEO_HOURLY_JSON, make_mock_response


@pytest.fixture
def client():
    clear_openmeteo_cache()
    c = OpenMeteoClient()
    c.session = MagicMock()
    return c


@patch("app.clients.openmeteo.requests.get")
def test_get_current_parses_response(mock_get):
    mock_get.return_value = make_mock_response(OPENMETEO_HOURLY_JSON)
    clear_openmeteo_cache()

    result = OpenMeteoClient().get_current(lat=-23.55, lon=-46.63)

    assert result["temperature"] == 25.5
    assert result["humidity"] == 70
    assert result["pressure"] == 1013.2
    assert result["wind_speed"] == 5.2
    assert result["wind_direction"] == 180
    assert result["precipitation"] == 0.0
    assert result["timestamp"] == "2026-06-05T12:00"
    mock_get.assert_called_once()
    assert mock_get.call_args.kwargs.get("timeout") == 10


@patch("app.clients.openmeteo.requests.get")
def test_get_current_raises_on_http_error(mock_get):
    mock_get.return_value = make_mock_response({}, status_code=429)
    clear_openmeteo_cache()

    with pytest.raises(Exception, match="Failed to fetch weather data"):
        OpenMeteoClient().get_current(lat=-23.55, lon=-46.63)


@patch("app.clients.openmeteo.requests.get")
def test_get_current_raises_on_connection_error(mock_get):
    mock_get.side_effect = requests.exceptions.ConnectionError("offline")
    clear_openmeteo_cache()

    with pytest.raises(Exception, match="Failed to fetch weather data"):
        OpenMeteoClient().get_current(lat=-23.55, lon=-46.63)


def test_get_historical_hourly_parses_records(client):
    client.session.get.return_value = make_mock_response(OPENMETEO_HOURLY_JSON)

    records = client.get_historical_hourly(
        lat=-23.55,
        lon=-46.63,
        start_date="2026-06-01",
        end_date="2026-06-05",
    )

    assert len(records) == 2
    assert records[0]["temperature"] == 25.5
    assert records[0]["wind_speed_kmh"] == pytest.approx(18.72)
    assert records[0]["latitude"] == -23.55
    assert records[1]["precipitation"] == 0.5


def test_get_historical_hourly_handles_none_wind(client):
    payload = {
        "hourly": {
            **OPENMETEO_HOURLY_JSON["hourly"],
            "wind_speed_10m": [None],
            "time": ["2026-06-05T12:00"],
            "temperature_2m": [20.0],
            "relative_humidity_2m": [50],
            "precipitation": [None],
        }
    }
    client.session.get.return_value = make_mock_response(payload)

    records = client.get_historical_hourly(
        lat=0.0, lon=0.0, start_date="2026-01-01", end_date="2026-01-02"
    )

    assert records[0]["wind_speed_kmh"] == 0.0
    assert records[0]["precipitation"] == 0.0


def test_get_historical_hourly_raises_on_failure(client):
    client.session.get.side_effect = requests.exceptions.Timeout("slow")

    with pytest.raises(Exception, match="Failed to fetch historical weather"):
        client.get_historical_hourly(
            lat=-23.55, lon=-46.63,
            start_date="2026-01-01", end_date="2026-01-02",
        )


def test_validate_coordinates_rejects_invalid(client):
    with pytest.raises(ValueError, match="latitude"):
        client.get_current(lat=91, lon=0)
    with pytest.raises(ValueError, match="longitude"):
        client.get_current(lat=0, lon=181)
