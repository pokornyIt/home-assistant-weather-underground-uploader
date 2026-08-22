"""Home Assistant Weather Underground Uploader integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Weather Underground Uploader from a config entry.

    :param hass: Home Assistant instance.
    :param entry: Weather Underground station config entry.
    :return: Whether setup completed successfully.
    """
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Weather Underground Uploader config entry.

    :param hass: Home Assistant instance.
    :param entry: Weather Underground station config entry.
    :return: Whether unload completed successfully.
    """
    return True
