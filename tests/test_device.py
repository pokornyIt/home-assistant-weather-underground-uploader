"""Tests for station devices and registry identity."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.weather_underground_uploader.const import (
    CONF_STATION_ID,
    CONF_STATION_KEY,
    DOMAIN,
)

EXPECTED_ENTITY_KEYS = {
    "consecutive_failures",
    "last_successful_upload",
    "last_upload_attempt",
    "test_upload",
    "upload_now",
    "upload_status",
}


def _create_entry(hass: HomeAssistant, station_id: str) -> MockConfigEntry:
    """Create one synthetic unmapped station entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=station_id,
        unique_id=station_id,
        data={
            CONF_STATION_ID: station_id,
            CONF_STATION_KEY: "synthetic-test-key",
        },
    )
    entry.add_to_hass(hass)
    return entry


async def _setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Set up an entry and wait for registry updates."""
    if entry.state is ConfigEntryState.NOT_LOADED:
        assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED


def _station_entities(hass: HomeAssistant, entry: MockConfigEntry) -> list[er.RegistryEntry]:
    """Return integration entities owned by one station entry."""
    registry = er.async_get(hass)
    return [
        entity for entity in er.async_entries_for_config_entry(registry, entry.entry_id) if entity.platform == DOMAIN
    ]


async def test_station_registers_one_device_with_all_operational_entities(hass: HomeAssistant) -> None:
    """One config entry creates one identified device containing every entity."""
    entry = _create_entry(hass, "IPRAGUE1")

    await _setup_entry(hass, entry)

    device_registry = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
    assert len(devices) == 1
    device = devices[0]
    assert device.identifiers == {(DOMAIN, entry.entry_id)}
    assert device.name == "Weather Underground IPRAGUE1"
    assert device.manufacturer == "Weather Underground"
    assert device.model == "Virtual Personal Weather Station"

    entities = _station_entities(hass, entry)
    assert {entity.unique_id for entity in entities} == {
        f"{entry.entry_id}_{entity_key}" for entity_key in EXPECTED_ENTITY_KEYS
    }
    assert {entity.device_id for entity in entities} == {device.id}


async def test_multiple_stations_register_independent_devices(hass: HomeAssistant) -> None:
    """Multiple config entries cannot merge their devices or entities."""
    entries = [_create_entry(hass, station_id) for station_id in ("IPRAGUE1", "IBRNO2")]
    for entry in entries:
        await _setup_entry(hass, entry)

    device_registry = dr.async_get(hass)
    devices = [dr.async_entries_for_config_entry(device_registry, entry.entry_id)[0] for entry in entries]
    assert devices[0].id != devices[1].id
    assert {device.name for device in devices} == {
        "Weather Underground IBRNO2",
        "Weather Underground IPRAGUE1",
    }
    for entry, device in zip(entries, devices, strict=True):
        assert device.identifiers == {(DOMAIN, entry.entry_id)}
        assert {entity.device_id for entity in _station_entities(hass, entry)} == {device.id}


async def test_reload_preserves_device_and_entity_registry_entries(hass: HomeAssistant) -> None:
    """Reloading a station does not create duplicate devices or entities."""
    entry = _create_entry(hass, "IPRAGUE1")
    await _setup_entry(hass, entry)
    device_registry = dr.async_get(hass)
    original_device = dr.async_entries_for_config_entry(device_registry, entry.entry_id)[0]
    original_entities = {entity.unique_id: entity.entity_id for entity in _station_entities(hass, entry)}

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
    assert [device.id for device in devices] == [original_device.id]
    assert {entity.unique_id: entity.entity_id for entity in _station_entities(hass, entry)} == original_entities


async def test_setup_migrates_released_station_id_registry_keys(hass: HomeAssistant) -> None:
    """Existing devices and entities retain their registry IDs during migration."""
    entry = _create_entry(hass, "IPRAGUE1")
    device_registry = dr.async_get(hass)
    old_device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "IPRAGUE1")},
        name="Weather Underground IPRAGUE1",
    )
    entity_registry = er.async_get(hass)
    old_entity = entity_registry.async_get_or_create(
        "sensor",
        DOMAIN,
        "IPRAGUE1_upload_status",
        config_entry=entry,
        device_id=old_device.id,
        suggested_object_id="weather_underground_iprague1_upload_status",
    )

    await _setup_entry(hass, entry)

    devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
    assert len(devices) == 1
    assert devices[0].id == old_device.id
    assert devices[0].identifiers == {(DOMAIN, entry.entry_id)}
    migrated_entity = entity_registry.async_get(old_entity.entity_id)
    assert migrated_entity is not None
    assert migrated_entity.unique_id == f"{entry.entry_id}_upload_status"
    assert migrated_entity.device_id == old_device.id
