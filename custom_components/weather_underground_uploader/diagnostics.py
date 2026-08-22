"""Diagnostics for Weather Underground Uploader config entries."""

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data  # pyright: ignore[reportUnknownVariableType]
from homeassistant.loader import async_get_integration

from .const import CONF_STATION_KEY, CONF_UPLOAD_INTERVAL, DEFAULT_UPLOAD_INTERVAL_SECONDS, DOMAIN
from .models import MAPPING_SPECS
from .runtime import WeatherUndergroundUploaderConfigEntry

_TO_REDACT = {CONF_STATION_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: WeatherUndergroundUploaderConfigEntry,
) -> dict[str, Any]:
    """Return secret-safe diagnostics for one virtual station."""
    integration = await async_get_integration(hass, DOMAIN)
    upload_state = entry.runtime_data.coordinator.data

    return {
        "integration": {
            "version": str(integration.version),
        },
        "config_entry": async_redact_data(dict(entry.data), _TO_REDACT),
        "configuration": {
            "upload_interval": int(
                entry.options.get(
                    CONF_UPLOAD_INTERVAL,
                    DEFAULT_UPLOAD_INTERVAL_SECONDS,
                )
            ),
            "mappings": {
                spec.option_key: entity_id
                for spec in MAPPING_SPECS
                if isinstance((entity_id := entry.options.get(spec.option_key)), str) and entity_id
            },
        },
        "upload": {
            "status": upload_state.status.value,
            "last_attempt": upload_state.last_attempt.isoformat() if upload_state.last_attempt else None,
            "last_success": upload_state.last_success.isoformat() if upload_state.last_success else None,
            "consecutive_failures": upload_state.consecutive_failures,
        },
    }
