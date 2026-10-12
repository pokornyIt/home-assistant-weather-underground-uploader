"""Tests for the Weather Underground Uploader lifecycle."""

from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.weather_underground_uploader import async_migrate_entry
from custom_components.weather_underground_uploader.api import WeatherUndergroundClient
from custom_components.weather_underground_uploader.const import (
    CONF_STATION_ID,
    CONF_STATION_KEY,
    CONF_UPLOAD_INTERVAL,
    DOMAIN,
)
from custom_components.weather_underground_uploader.coordinator import WeatherUndergroundUploadCoordinator
from custom_components.weather_underground_uploader.runtime import WeatherUndergroundUploaderRuntimeData


@pytest.mark.parametrize(
    ("legacy_interval", "expected_interval"),
    [
        (None, 30),
        (60, 5),
        (290, 5),
        (300, 30),
        (300.0, 30),
        (301, 10),
        (350, 10),
        (600, 10),
        (600.1, 15),
        (1800, 30),
        (3600, 60),
        (86400, 1440),
        (86401, 1440),
    ],
)
async def test_migrate_legacy_upload_interval_to_minutes(
    hass: HomeAssistant,
    legacy_interval: float | int | None,
    expected_interval: int,
) -> None:
    """Version 1 entries convert their saved seconds exactly once."""
    options: dict[str, str | float | int] = {"preserved_option": "value"}
    if legacy_interval is not None:
        options[CONF_UPLOAD_INTERVAL] = legacy_interval
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="IPRAGUE1",
        data={CONF_STATION_ID: "IPRAGUE1", CONF_STATION_KEY: "synthetic-test-key"},
        options=options,
        version=1,
    )
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry)
    assert entry.version == 2
    assert entry.options == {"preserved_option": "value", CONF_UPLOAD_INTERVAL: expected_interval}

    with patch.object(hass.config_entries, "async_update_entry") as update_entry:
        assert await async_migrate_entry(hass, entry)

    update_entry.assert_not_called()


class TestConfigEntryLifecycle:
    """Verify config-entry setup and unload behavior."""

    async def test_setup_and_unload(self, hass: HomeAssistant) -> None:
        """A station entry can be set up, reloaded, and unloaded cleanly."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id="IPRAGUE1",
            data={
                CONF_STATION_ID: "IPRAGUE1",
                CONF_STATION_KEY: "synthetic-test-key",
            },
            version=2,
        )
        entry.add_to_hass(hass)

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED
        assert isinstance(entry.runtime_data, WeatherUndergroundUploaderRuntimeData)
        assert isinstance(entry.runtime_data.client, WeatherUndergroundClient)
        assert isinstance(entry.runtime_data.coordinator, WeatherUndergroundUploadCoordinator)
        assert hass.states.get("sensor.weather_underground_iprague1_upload_status") is not None
        assert hass.states.get("button.weather_underground_iprague1_upload_now") is not None
        assert hass.states.get("button.weather_underground_iprague1_test_upload") is not None

        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.NOT_LOADED
