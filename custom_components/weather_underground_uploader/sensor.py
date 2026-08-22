"""Operational sensors for Weather Underground Uploader."""

from collections.abc import Callable
from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import UploadState, UploadStatus, WeatherUndergroundUploadCoordinator
from .entity import station_device_info, station_entity_unique_id
from .runtime import WeatherUndergroundUploaderConfigEntry


class WeatherUndergroundOperationalSensor(SensorEntity):
    """Base sensor exposing coordinator state for one virtual station."""

    _attr_has_entity_name = True
    _attr_available = True

    def __init__(
        self,
        entry: WeatherUndergroundUploaderConfigEntry,
        description: SensorEntityDescription,
        value_fn: Callable[[UploadState], datetime | int | str | None],
    ) -> None:
        """Initialize an operational sensor."""
        self.entity_description = description
        self._attr_unique_id = station_entity_unique_id(entry, description.key)
        self._attr_device_info = station_device_info(entry)
        self._coordinator: WeatherUndergroundUploadCoordinator = entry.runtime_data.coordinator
        self._value_fn = value_fn
        self._attr_native_value = value_fn(self._coordinator.data)

    async def async_added_to_hass(self) -> None:
        """Subscribe to coordinator state changes."""
        await super().async_added_to_hass()
        self.async_on_remove(self._coordinator.async_add_listener(self._handle_coordinator_update))

    @callback
    def _handle_coordinator_update(self) -> None:
        """Write the latest in-memory coordinator state."""
        self._attr_native_value = self._value_fn(self._coordinator.data)
        self.async_write_ha_state()


class WeatherUndergroundStatusSensor(WeatherUndergroundOperationalSensor):
    """Expose the latest upload result."""

    def __init__(self, entry: WeatherUndergroundUploaderConfigEntry) -> None:
        """Initialize the upload status sensor."""
        self._attr_options = [status.value for status in UploadStatus]
        super().__init__(
            entry,
            SensorEntityDescription(
                key="upload_status",
                translation_key="upload_status",
                device_class=SensorDeviceClass.ENUM,
            ),
            lambda state: state.status.value,
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WeatherUndergroundUploaderConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up operational sensors for one station."""
    del hass
    async_add_entities(
        [
            WeatherUndergroundStatusSensor(entry),
            WeatherUndergroundOperationalSensor(
                entry,
                SensorEntityDescription(
                    key="last_upload_attempt",
                    translation_key="last_upload_attempt",
                    device_class=SensorDeviceClass.TIMESTAMP,
                ),
                lambda state: state.last_attempt,
            ),
            WeatherUndergroundOperationalSensor(
                entry,
                SensorEntityDescription(
                    key="last_successful_upload",
                    translation_key="last_successful_upload",
                    device_class=SensorDeviceClass.TIMESTAMP,
                ),
                lambda state: state.last_success,
            ),
            WeatherUndergroundOperationalSensor(
                entry,
                SensorEntityDescription(
                    key="consecutive_failures",
                    translation_key="consecutive_failures",
                    icon="mdi:alert-circle-outline",
                ),
                lambda state: state.consecutive_failures,
            ),
        ]
    )
