"""Data models for mapped weather observations."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from .const import (
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


class MeasurementKind(StrEnum):
    """Supported measurement conversion categories."""

    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    PRESSURE = "pressure"
    WIND_DIRECTION = "wind_direction"
    WIND_SPEED = "wind_speed"
    RAIN = "rain"
    UV_INDEX = "uv_index"
    SOLAR_RADIATION = "solar_radiation"


@dataclass(frozen=True, slots=True)
class MappingSpec:
    """Describe one Home Assistant to Weather Underground field mapping."""

    option_key: str
    protocol_field: str
    kind: MeasurementKind


MAPPING_SPECS: Final = (
    MappingSpec(CONF_TEMPERATURE, "tempf", MeasurementKind.TEMPERATURE),
    MappingSpec(CONF_HUMIDITY, "humidity", MeasurementKind.HUMIDITY),
    MappingSpec(CONF_PRESSURE, "baromin", MeasurementKind.PRESSURE),
    MappingSpec(CONF_DEW_POINT, "dewptf", MeasurementKind.TEMPERATURE),
    MappingSpec(CONF_WIND_DIRECTION, "winddir", MeasurementKind.WIND_DIRECTION),
    MappingSpec(CONF_WIND_SPEED, "windspeedmph", MeasurementKind.WIND_SPEED),
    MappingSpec(CONF_WIND_GUST, "windgustmph", MeasurementKind.WIND_SPEED),
    MappingSpec(CONF_HOURLY_RAIN, "rainin", MeasurementKind.RAIN),
    MappingSpec(CONF_DAILY_RAIN, "dailyrainin", MeasurementKind.RAIN),
    MappingSpec(CONF_UV_INDEX, "UV", MeasurementKind.UV_INDEX),
    MappingSpec(CONF_SOLAR_RADIATION, "solarradiation", MeasurementKind.SOLAR_RADIATION),
)
