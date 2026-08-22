"""Read and normalize mapped Home Assistant weather entities."""

import math
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Final

from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    DEGREE,
    PERCENTAGE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UV_INDEX,
    UnitOfIrradiance,
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import (
    DistanceConverter,
    PressureConverter,
    SpeedConverter,
    TemperatureConverter,
)

from .const import CONF_DEW_POINT
from .models import MAPPING_SPECS, MappingSpec, MeasurementKind

DEFAULT_MAX_STATE_AGE: Final = timedelta(hours=1)

_UNAVAILABLE_STATES: Final = frozenset({"", STATE_UNAVAILABLE, STATE_UNKNOWN})
_ABSOLUTE_ZERO_FAHRENHEIT: Final = -459.67
_MAGNUS_A: Final = 17.625
_MAGNUS_B_CELSIUS: Final = 243.04
_BTU_PER_HOUR_SQUARE_FOOT_TO_WATTS_PER_SQUARE_METER: Final = 3.154590745


def build_observation(
    hass: HomeAssistant,
    options: Mapping[str, object],
    *,
    now: datetime | None = None,
    max_state_age: timedelta = DEFAULT_MAX_STATE_AGE,
) -> dict[str, str]:
    """Build normalized Weather Underground fields from current entity states.

    Invalid, unavailable, missing, or stale optional values are omitted without
    affecting other mappings. An empty result means there is no payload to send.

    :param hass: Home Assistant instance whose state machine is read now.
    :param options: Config-entry options containing entity mappings.
    :param now: Current UTC time override for deterministic tests.
    :param max_state_age: Maximum age since an entity last reported.
    :return: Normalized Weather Underground protocol fields.
    """
    current_time = now or dt_util.utcnow()
    normalized: dict[str, float] = {}

    for spec in MAPPING_SPECS:
        entity_id = options.get(spec.option_key)
        if not isinstance(entity_id, str) or not entity_id:
            continue

        state = hass.states.get(entity_id)
        value = _normalize_state(state, spec, current_time, max_state_age)
        if value is not None:
            normalized[spec.protocol_field] = value

    dew_point_entity = options.get(CONF_DEW_POINT)
    has_explicit_dew_point = isinstance(dew_point_entity, str) and bool(dew_point_entity)
    if not has_explicit_dew_point and "tempf" in normalized and "humidity" in normalized:
        calculated_dew_point = _calculate_dew_point_fahrenheit(normalized["tempf"], normalized["humidity"])
        if calculated_dew_point is not None:
            normalized["dewptf"] = calculated_dew_point

    if "dewptf" in normalized and "tempf" in normalized and normalized["dewptf"] > normalized["tempf"]:
        del normalized["dewptf"]

    return {field: _format_value(value) for field, value in normalized.items()}


def _normalize_state(
    state: State | None,
    spec: MappingSpec,
    now: datetime,
    max_state_age: timedelta,
) -> float | None:
    """Return one normalized finite value when its state is usable."""
    if state is None or state.state.strip().lower() in _UNAVAILABLE_STATES:
        return None
    if max_state_age < timedelta(0) or now - state.last_reported > max_state_age:
        return None

    try:
        value = float(state.state)
    except ValueError:
        return None
    if not math.isfinite(value):
        return None

    unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
    if unit is not None and not isinstance(unit, str):
        return None

    try:
        normalized = _convert_value(value, unit, spec.kind)
    except HomeAssistantError:
        return None

    if not math.isfinite(normalized) or not _is_in_physical_range(normalized, spec.kind):
        return None
    return normalized


def _convert_value(value: float, unit: str | None, kind: MeasurementKind) -> float:
    """Convert a value to its Weather Underground protocol unit."""
    if kind is MeasurementKind.TEMPERATURE:
        return TemperatureConverter.convert(value, unit, UnitOfTemperature.FAHRENHEIT)
    if kind is MeasurementKind.PRESSURE:
        return PressureConverter.convert(value, unit, UnitOfPressure.INHG)
    if kind is MeasurementKind.WIND_SPEED:
        return SpeedConverter.convert(value, unit, UnitOfSpeed.MILES_PER_HOUR)
    if kind is MeasurementKind.RAIN:
        return DistanceConverter.convert(value, unit, UnitOfLength.INCHES)
    if kind is MeasurementKind.HUMIDITY:
        if unit not in (None, PERCENTAGE):
            raise HomeAssistantError("Unsupported humidity unit")
        return value
    if kind is MeasurementKind.WIND_DIRECTION:
        if unit not in (None, DEGREE):
            raise HomeAssistantError("Unsupported wind direction unit")
        return value
    if kind is MeasurementKind.UV_INDEX:
        if unit not in (None, UV_INDEX):
            raise HomeAssistantError("Unsupported UV index unit")
        return value
    if unit == UnitOfIrradiance.WATTS_PER_SQUARE_METER:
        return value
    if unit == UnitOfIrradiance.BTUS_PER_HOUR_SQUARE_FOOT:
        return value * _BTU_PER_HOUR_SQUARE_FOOT_TO_WATTS_PER_SQUARE_METER
    raise HomeAssistantError("Unsupported solar radiation unit")


def _is_in_physical_range(value: float, kind: MeasurementKind) -> bool:
    """Check broad physical limits without imposing device-specific ranges."""
    if kind is MeasurementKind.TEMPERATURE:
        return value >= _ABSOLUTE_ZERO_FAHRENHEIT
    if kind is MeasurementKind.HUMIDITY:
        return 0 <= value <= 100
    if kind is MeasurementKind.WIND_DIRECTION:
        return 0 <= value <= 360
    if kind is MeasurementKind.PRESSURE:
        return value > 0
    return value >= 0


def _calculate_dew_point_fahrenheit(temperature_f: float, humidity: float) -> float | None:
    """Calculate dew point with the Magnus formula."""
    if humidity <= 0:
        return None
    temperature_c = TemperatureConverter.convert(
        temperature_f,
        UnitOfTemperature.FAHRENHEIT,
        UnitOfTemperature.CELSIUS,
    )
    gamma = math.log(humidity / 100) + (_MAGNUS_A * temperature_c) / (_MAGNUS_B_CELSIUS + temperature_c)
    dew_point_c = (_MAGNUS_B_CELSIUS * gamma) / (_MAGNUS_A - gamma)
    return TemperatureConverter.convert(
        dew_point_c,
        UnitOfTemperature.CELSIUS,
        UnitOfTemperature.FAHRENHEIT,
    )


def _format_value(value: float) -> str:
    """Format a protocol number without locale or insignificant zeroes."""
    formatted = f"{value:.6f}".rstrip("0").rstrip(".")
    return "0" if formatted == "-0" else formatted
