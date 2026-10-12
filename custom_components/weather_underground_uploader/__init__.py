"""Home Assistant Weather Underground Uploader integration."""

from math import ceil, isfinite

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WeatherUndergroundClient
from .const import (
    CONF_STATION_ID,
    CONF_STATION_KEY,
    CONF_UPLOAD_INTERVAL,
    DEFAULT_UPLOAD_INTERVAL_MINUTES,
    MAX_UPLOAD_INTERVAL_MINUTES,
    MIN_UPLOAD_INTERVAL_MINUTES,
    UPLOAD_INTERVAL_STEP_MINUTES,
)
from .coordinator import WeatherUndergroundUploadCoordinator
from .entity import async_migrate_station_registry
from .repairs import async_sync_mapping_issues
from .runtime import WeatherUndergroundUploaderConfigEntry, WeatherUndergroundUploaderRuntimeData

PLATFORMS = (Platform.SENSOR, Platform.BUTTON)


async def async_migrate_entry(hass: HomeAssistant, entry: WeatherUndergroundUploaderConfigEntry) -> bool:
    """Migrate legacy upload intervals from seconds to minutes.

    :param hass: Home Assistant instance.
    :param entry: Config entry to migrate.
    :return: Whether the entry is supported and ready to set up.
    """
    if entry.version > 2:
        return False
    if entry.version == 2:
        return True

    if CONF_UPLOAD_INTERVAL not in entry.options:
        interval_minutes = DEFAULT_UPLOAD_INTERVAL_MINUTES
    else:
        interval_seconds = entry.options[CONF_UPLOAD_INTERVAL]
        if interval_seconds == 300:
            interval_minutes = DEFAULT_UPLOAD_INTERVAL_MINUTES
        elif (
            isinstance(interval_seconds, bool)
            or not isinstance(interval_seconds, int | float)
            or not isfinite(interval_seconds)
        ):
            return False
        else:
            interval_minutes = min(
                MAX_UPLOAD_INTERVAL_MINUTES,
                max(
                    MIN_UPLOAD_INTERVAL_MINUTES,
                    ceil(interval_seconds / (UPLOAD_INTERVAL_STEP_MINUTES * 60)) * UPLOAD_INTERVAL_STEP_MINUTES,
                ),
            )

    hass.config_entries.async_update_entry(
        entry,
        options={**entry.options, CONF_UPLOAD_INTERVAL: interval_minutes},
        version=2,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: WeatherUndergroundUploaderConfigEntry) -> bool:
    """Set up Weather Underground Uploader from a config entry.

    :param hass: Home Assistant instance.
    :param entry: Weather Underground station config entry.
    :return: Whether setup completed successfully.
    """
    async_migrate_station_registry(hass, entry)
    client = WeatherUndergroundClient(
        async_get_clientsession(hass),
        station_id=entry.data[CONF_STATION_ID],
        station_key=entry.data[CONF_STATION_KEY],
    )
    coordinator = WeatherUndergroundUploadCoordinator(hass, entry, client)
    entry.async_on_unload(coordinator.async_add_listener(lambda: None))
    entry.runtime_data = WeatherUndergroundUploaderRuntimeData(client, coordinator)
    if coordinator.upload_enabled:
        await coordinator.async_config_entry_first_refresh()
    else:
        async_sync_mapping_issues(hass, entry, {})
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: WeatherUndergroundUploaderConfigEntry) -> bool:
    """Unload a Weather Underground Uploader config entry.

    :param hass: Home Assistant instance.
    :param entry: Weather Underground station config entry.
    :return: Whether unload completed successfully.
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
