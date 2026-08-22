"""Tests for the Weather Underground Uploader lifecycle."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.weather_underground_uploader.const import (
    CONF_STATION_ID,
    CONF_STATION_KEY,
    DOMAIN,
)


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
        )
        entry.add_to_hass(hass)

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED

        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.NOT_LOADED
