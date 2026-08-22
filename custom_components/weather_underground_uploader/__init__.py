"""Home Assistant Weather Underground Uploader integration."""

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WeatherUndergroundClient
from .const import CONF_STATION_ID, CONF_STATION_KEY
from .coordinator import WeatherUndergroundUploadCoordinator
from .runtime import WeatherUndergroundUploaderConfigEntry, WeatherUndergroundUploaderRuntimeData

PLATFORMS = (Platform.SENSOR, Platform.BUTTON)


async def async_setup_entry(hass: HomeAssistant, entry: WeatherUndergroundUploaderConfigEntry) -> bool:
    """Set up Weather Underground Uploader from a config entry.

    :param hass: Home Assistant instance.
    :param entry: Weather Underground station config entry.
    :return: Whether setup completed successfully.
    """
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
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: WeatherUndergroundUploaderConfigEntry) -> bool:
    """Unload a Weather Underground Uploader config entry.

    :param hass: Home Assistant instance.
    :param entry: Weather Underground station config entry.
    :return: Whether unload completed successfully.
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
