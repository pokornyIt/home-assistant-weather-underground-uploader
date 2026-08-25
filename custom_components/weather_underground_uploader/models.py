"""Data models for mapped weather observations."""

from collections.abc import Mapping
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


class MappingProblemType(StrEnum):
    """Reason a configured measurement cannot be uploaded."""

    MISSING_ENTITY = "missing_entity"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"
    NON_NUMERIC = "non_numeric"
    NON_FINITE = "non_finite"
    UNSUPPORTED_UNIT = "unsupported_unit"
    OUT_OF_RANGE = "out_of_range"
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class MappingSpec:
    """Describe one Home Assistant to Weather Underground field mapping."""

    option_key: str
    protocol_field: str
    kind: MeasurementKind


@dataclass(frozen=True, slots=True)
class MappingValidationProblem:
    """Describe one currently unusable configured mapping."""

    mapping_key: str
    entity_id: str
    problem_type: MappingProblemType


@dataclass(frozen=True, slots=True)
class ObservationResult:
    """Normalized upload fields and independently detected mapping problems."""

    observation: dict[str, str]
    problems: tuple[MappingValidationProblem, ...]


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


def has_configured_mapping(options: Mapping[str, object]) -> bool:
    """Return whether station options contain at least one entity mapping."""
    return any(bool(options.get(spec.option_key)) for spec in MAPPING_SPECS)
