"""Shared Weather Underground Uploader entity helpers."""

from homeassistant.helpers.device_registry import DeviceInfo

from .const import CONF_STATION_ID, DOMAIN
from .runtime import WeatherUndergroundUploaderConfigEntry


def station_device_info(entry: WeatherUndergroundUploaderConfigEntry) -> DeviceInfo:
    """Return device information for one virtual station."""
    station_id = entry.data[CONF_STATION_ID]
    return DeviceInfo(
        identifiers={(DOMAIN, station_id)},
        name=f"Weather Underground {station_id}",
        manufacturer="Weather Underground",
        model="Virtual Personal Weather Station",
    )


def station_entity_unique_id(entry: WeatherUndergroundUploaderConfigEntry, entity_key: str) -> str:
    """Return a stable entity unique ID based on the station identity."""
    return f"{entry.data[CONF_STATION_ID]}_{entity_key}"
