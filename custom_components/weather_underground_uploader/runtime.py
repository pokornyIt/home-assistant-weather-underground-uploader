"""Runtime data types for Weather Underground Uploader."""

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry

from .api import WeatherUndergroundClient
from .coordinator import WeatherUndergroundUploadCoordinator


@dataclass(slots=True)
class WeatherUndergroundUploaderRuntimeData:
    """Resources owned by one loaded config entry."""

    client: WeatherUndergroundClient
    coordinator: WeatherUndergroundUploadCoordinator


type WeatherUndergroundUploaderConfigEntry = ConfigEntry[WeatherUndergroundUploaderRuntimeData]
