"""Tests for entity mapping and unit normalization."""

from datetime import timedelta
from typing import Final

import pytest
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    DEGREE,
    PERCENTAGE,
    STATE_UNAVAILABLE,
    UnitOfIrradiance,
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.weather_underground_uploader.const import (
    CONF_DAILY_RAIN,
    CONF_DEW_POINT,
    CONF_HOURLY_RAIN,
    CONF_HUMIDITY,
    CONF_PRESSURE,
    CONF_SOLAR_RADIATION,
    CONF_TEMPERATURE,
    CONF_UV_INDEX,
    CONF_WIND_DIRECTION,
    CONF_WIND_GUST,
    CONF_WIND_SPEED,
)
from custom_components.weather_underground_uploader.mapping import build_observation

UNIT: Final = ATTR_UNIT_OF_MEASUREMENT


def _set_measurement(hass: HomeAssistant, entity_id: str, value: object, unit: str | None = None) -> None:
    """Set a synthetic measurement state."""
    attributes = {} if unit is None else {UNIT: unit}
    hass.states.async_set(entity_id, str(value), attributes)


def test_metric_values_are_normalized(hass: HomeAssistant) -> None:
    """Metric source entities produce Weather Underground protocol units."""
    measurements = {
        CONF_TEMPERATURE: ("sensor.temperature", 20, UnitOfTemperature.CELSIUS),
        CONF_HUMIDITY: ("sensor.humidity", 50, PERCENTAGE),
        CONF_PRESSURE: ("sensor.pressure", 1013.25, UnitOfPressure.HPA),
        CONF_DEW_POINT: ("sensor.dew_point", 10, UnitOfTemperature.CELSIUS),
        CONF_WIND_DIRECTION: ("sensor.wind_direction", 180, DEGREE),
        CONF_WIND_SPEED: ("sensor.wind_speed", 10, UnitOfSpeed.KILOMETERS_PER_HOUR),
        CONF_WIND_GUST: ("sensor.wind_gust", 5, UnitOfSpeed.METERS_PER_SECOND),
        CONF_HOURLY_RAIN: ("sensor.hourly_rain", 2.54, UnitOfLength.MILLIMETERS),
        CONF_DAILY_RAIN: ("sensor.daily_rain", 25.4, UnitOfLength.MILLIMETERS),
        CONF_UV_INDEX: ("sensor.uv_index", 4.2, None),
        CONF_SOLAR_RADIATION: (
            "sensor.solar_radiation",
            500,
            UnitOfIrradiance.WATTS_PER_SQUARE_METER,
        ),
    }
    for entity_id, value, unit in measurements.values():
        _set_measurement(hass, entity_id, value, unit)

    observation = build_observation(hass, {key: entity_id for key, (entity_id, _, _) in measurements.items()})

    assert float(observation["tempf"]) == pytest.approx(68)
    assert float(observation["humidity"]) == pytest.approx(50)
    assert float(observation["baromin"]) == pytest.approx(29.9213, rel=1e-5)
    assert float(observation["dewptf"]) == pytest.approx(50)
    assert float(observation["winddir"]) == pytest.approx(180)
    assert float(observation["windspeedmph"]) == pytest.approx(6.21371, rel=1e-5)
    assert float(observation["windgustmph"]) == pytest.approx(11.1847, rel=1e-5)
    assert float(observation["rainin"]) == pytest.approx(0.1)
    assert float(observation["dailyrainin"]) == pytest.approx(1)
    assert float(observation["UV"]) == pytest.approx(4.2)
    assert float(observation["solarradiation"]) == pytest.approx(500)


def test_imperial_values_are_preserved(hass: HomeAssistant) -> None:
    """Values already using protocol units do not change."""
    _set_measurement(hass, "sensor.temperature", 72.5, UnitOfTemperature.FAHRENHEIT)
    _set_measurement(hass, "sensor.pressure", 30.01, UnitOfPressure.INHG)
    _set_measurement(hass, "sensor.wind", 12.5, UnitOfSpeed.MILES_PER_HOUR)
    _set_measurement(hass, "sensor.rain", 0.25, UnitOfLength.INCHES)

    observation = build_observation(
        hass,
        {
            CONF_TEMPERATURE: "sensor.temperature",
            CONF_PRESSURE: "sensor.pressure",
            CONF_WIND_SPEED: "sensor.wind",
            CONF_DAILY_RAIN: "sensor.rain",
        },
    )

    assert observation == {
        "tempf": "72.5",
        "baromin": "30.01",
        "windspeedmph": "12.5",
        "dailyrainin": "0.25",
    }


def test_imperial_solar_radiation_is_normalized(hass: HomeAssistant) -> None:
    """Imperial irradiance is converted to watts per square meter."""
    _set_measurement(
        hass,
        "sensor.solar_radiation",
        100,
        UnitOfIrradiance.BTUS_PER_HOUR_SQUARE_FOOT,
    )

    observation = build_observation(hass, {CONF_SOLAR_RADIATION: "sensor.solar_radiation"})

    assert float(observation["solarradiation"]) == pytest.approx(315.459, rel=1e-5)


def test_invalid_values_are_omitted_independently(hass: HomeAssistant) -> None:
    """Bad optional mappings do not suppress a valid mapping."""
    _set_measurement(hass, "sensor.valid", 55, PERCENTAGE)
    _set_measurement(hass, "sensor.unavailable", STATE_UNAVAILABLE, UnitOfTemperature.CELSIUS)
    _set_measurement(hass, "sensor.non_numeric", "wet", UnitOfLength.MILLIMETERS)
    _set_measurement(hass, "sensor.non_finite", "nan", UnitOfSpeed.METERS_PER_SECOND)
    _set_measurement(hass, "sensor.bad_range", -1)
    _set_measurement(hass, "sensor.bad_unit", 20, UnitOfLength.METERS)

    observation = build_observation(
        hass,
        {
            CONF_HUMIDITY: "sensor.valid",
            CONF_TEMPERATURE: "sensor.unavailable",
            CONF_DAILY_RAIN: "sensor.non_numeric",
            CONF_WIND_SPEED: "sensor.non_finite",
            CONF_UV_INDEX: "sensor.bad_range",
            CONF_PRESSURE: "sensor.bad_unit",
            CONF_WIND_GUST: "sensor.missing",
        },
    )

    assert observation == {"humidity": "55"}


def test_stale_value_is_omitted(hass: HomeAssistant) -> None:
    """An entity that has not reported within the freshness window is omitted."""
    now = dt_util.utcnow()
    hass.states.async_set(
        "sensor.temperature",
        "20",
        {UNIT: UnitOfTemperature.CELSIUS},
        timestamp=(now - timedelta(hours=2)).timestamp(),
    )

    observation = build_observation(hass, {CONF_TEMPERATURE: "sensor.temperature"}, now=now)

    assert observation == {}


def test_dew_point_is_calculated_when_not_mapped(hass: HomeAssistant) -> None:
    """Temperature and humidity provide a calculated dew point."""
    _set_measurement(hass, "sensor.temperature", 20, UnitOfTemperature.CELSIUS)
    _set_measurement(hass, "input_number.humidity", 50)

    observation = build_observation(
        hass,
        {
            CONF_TEMPERATURE: "sensor.temperature",
            CONF_HUMIDITY: "input_number.humidity",
        },
    )

    assert float(observation["dewptf"]) == pytest.approx(48.7, abs=0.1)


def test_explicit_dew_point_wins(hass: HomeAssistant) -> None:
    """A mapped dew point takes precedence over calculation."""
    _set_measurement(hass, "sensor.temperature", 20, UnitOfTemperature.CELSIUS)
    _set_measurement(hass, "sensor.humidity", 50, PERCENTAGE)
    _set_measurement(hass, "sensor.dew_point", 5, UnitOfTemperature.CELSIUS)

    observation = build_observation(
        hass,
        {
            CONF_TEMPERATURE: "sensor.temperature",
            CONF_HUMIDITY: "sensor.humidity",
            CONF_DEW_POINT: "sensor.dew_point",
        },
    )

    assert observation["dewptf"] == "41"


def test_current_state_is_read_for_each_observation(hass: HomeAssistant) -> None:
    """State changes are reflected without rebuilding mapping configuration."""
    options = {CONF_TEMPERATURE: "sensor.temperature"}
    _set_measurement(hass, "sensor.temperature", 10, UnitOfTemperature.CELSIUS)
    first = build_observation(hass, options)

    _set_measurement(hass, "sensor.temperature", 20, UnitOfTemperature.CELSIUS)
    second = build_observation(hass, options)

    assert first["tempf"] == "50"
    assert second["tempf"] == "68"
