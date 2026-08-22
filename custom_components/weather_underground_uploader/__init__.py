"""Home Assistant Weather Underground Uploader integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WeatherUndergroundClient
from .const import CONF_STATION_ID, CONF_STATION_KEY

type WeatherUndergroundUploaderConfigEntry = ConfigEntry[WeatherUndergroundClient]


async def async_setup_entry(hass: HomeAssistant, entry: WeatherUndergroundUploaderConfigEntry) -> bool:
    """Set up Weather Underground Uploader from a config entry.

    :param hass: Home Assistant instance.
    :param entry: Weather Underground station config entry.
    :return: Whether setup completed successfully.
    """
    entry.runtime_data = WeatherUndergroundClient(
        async_get_clientsession(hass),
        station_id=entry.data[CONF_STATION_ID],
        station_key=entry.data[CONF_STATION_KEY],
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: WeatherUndergroundUploaderConfigEntry) -> bool:
    """Unload a Weather Underground Uploader config entry.

    :param hass: Home Assistant instance.
    :param entry: Weather Underground station config entry.
    :return: Whether unload completed successfully.
    """
    return True
