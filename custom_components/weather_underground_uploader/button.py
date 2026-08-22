"""Manual upload button for Weather Underground Uploader."""

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import station_device_info, station_entity_unique_id
from .runtime import WeatherUndergroundUploaderConfigEntry


class WeatherUndergroundUploadButton(ButtonEntity):
    """Request an immediate station upload."""

    _attr_has_entity_name = True
    _attr_translation_key = "upload_now"
    _attr_icon = "mdi:cloud-upload-outline"

    def __init__(self, entry: WeatherUndergroundUploaderConfigEntry) -> None:
        """Initialize the manual upload button."""
        self._attr_unique_id = station_entity_unique_id(entry, "upload_now")
        self._attr_device_info = station_device_info(entry)
        self._coordinator = entry.runtime_data.coordinator
        self._attr_available = self._coordinator.upload_enabled

    async def async_press(self) -> None:
        """Request a serialized upload cycle."""
        await self._coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WeatherUndergroundUploaderConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the manual upload button for one station."""
    del hass
    async_add_entities([WeatherUndergroundUploadButton(entry)])
