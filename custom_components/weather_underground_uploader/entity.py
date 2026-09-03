"""Shared Weather Underground Uploader entity helpers."""

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo

from .const import CONF_STATION_ID, DOMAIN
from .runtime import WeatherUndergroundUploaderConfigEntry


def station_device_info(entry: WeatherUndergroundUploaderConfigEntry) -> DeviceInfo:
    """Return device information for one virtual station.

    :param entry: Station config entry.
    :return: Home Assistant device information.
    """
    station_id = entry.data[CONF_STATION_ID]
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Weather Underground {station_id}",
        manufacturer="Weather Underground",
        model="Virtual Personal Weather Station",
    )


def station_entity_unique_id(entry: WeatherUndergroundUploaderConfigEntry, entity_key: str) -> str:
    """Return a stable entity unique ID based on the station identity.

    :param entry: Station config entry.
    :param entity_key: Stable key for the entity type.
    :return: Entity registry unique ID.
    """
    return f"{entry.entry_id}_{entity_key}"


@callback
def async_migrate_station_registry(hass: HomeAssistant, entry: WeatherUndergroundUploaderConfigEntry) -> None:
    """Migrate released Station ID registry keys to stable config-entry keys.

    :param hass: Home Assistant instance.
    :param entry: Station config entry whose registries are migrated.
    """
    station_id = entry.data[CONF_STATION_ID]
    old_identifier = (DOMAIN, station_id)
    new_identifier = (DOMAIN, entry.entry_id)

    device_registry = dr.async_get(hass)
    if (
        old_device := device_registry.async_get_device(identifiers={old_identifier})
    ) is not None and device_registry.async_get_device(identifiers={new_identifier}) is None:
        device_registry.async_update_device(old_device.id, new_identifiers={new_identifier})

    entity_registry = er.async_get(hass)
    old_prefix = f"{station_id}_"
    for entity_entry in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        if entity_entry.platform != DOMAIN or not entity_entry.unique_id.startswith(old_prefix):
            continue

        new_unique_id = f"{entry.entry_id}_{entity_entry.unique_id.removeprefix(old_prefix)}"
        if entity_registry.async_get_entity_id(entity_entry.domain, DOMAIN, new_unique_id) is None:
            entity_registry.async_update_entity(entity_entry.entity_id, new_unique_id=new_unique_id)
