"""Upload controls for Weather Underground Uploader."""

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import WeatherUndergroundAuthenticationError, WeatherUndergroundError
from .const import DOMAIN
from .coordinator import TestUploadNoDataError
from .entity import station_device_info, station_entity_unique_id
from .runtime import WeatherUndergroundUploaderConfigEntry


class WeatherUndergroundUploadNowButton(ButtonEntity):
    """Request an immediate normal station upload."""

    _attr_has_entity_name = True
    _attr_translation_key = "upload_now"
    _attr_icon = "mdi:cloud-upload-outline"

    def __init__(self, entry: WeatherUndergroundUploaderConfigEntry) -> None:
        """Initialize the normal upload button."""
        self._attr_unique_id = station_entity_unique_id(entry, "upload_now")
        self._attr_device_info = station_device_info(entry)
        self._coordinator = entry.runtime_data.coordinator
        self._attr_available = self._coordinator.upload_enabled

    async def async_press(self) -> None:
        """Request a serialized normal upload cycle."""
        await self._coordinator.async_request_refresh()


class WeatherUndergroundTestUploadButton(ButtonEntity):
    """Test station credentials with a currently valid observation."""

    _attr_has_entity_name = True
    _attr_translation_key = "test_upload"
    _attr_icon = "mdi:cloud-check-outline"

    def __init__(self, entry: WeatherUndergroundUploaderConfigEntry) -> None:
        """Initialize the test upload button."""
        self._attr_unique_id = station_entity_unique_id(entry, "test_upload")
        self._attr_device_info = station_device_info(entry)
        self._entry = entry
        self._coordinator = entry.runtime_data.coordinator
        self._attr_available = self._coordinator.upload_enabled

    async def async_press(self) -> None:
        """Send a test upload and report an actionable translated failure."""
        try:
            await self._coordinator.async_test_upload()
        except TestUploadNoDataError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="test_upload_no_data",
            ) from err
        except WeatherUndergroundAuthenticationError as err:
            self._entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="test_upload_invalid_auth",
            ) from err
        except WeatherUndergroundError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="test_upload_failed",
            ) from err


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WeatherUndergroundUploaderConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up upload controls for one station."""
    del hass
    async_add_entities(
        [
            WeatherUndergroundUploadNowButton(entry),
            WeatherUndergroundTestUploadButton(entry),
        ]
    )
