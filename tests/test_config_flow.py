"""Tests for the Weather Underground Uploader config flow."""

from typing import Final

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.weather_underground_uploader.const import (
    CONF_HUMIDITY,
    CONF_STATION_ID,
    CONF_STATION_KEY,
    CONF_TEMPERATURE,
    DOMAIN,
)
from custom_components.weather_underground_uploader.models import MAPPING_SPECS

TEST_STATION_ID: Final = "IPRAGUE1"
TEST_STATION_KEY: Final = "synthetic-test-key"


class TestConfigFlow:
    """Verify station configuration through the UI flow."""

    async def test_user_form(self, hass: HomeAssistant) -> None:
        """The initial step asks for station ID and key."""
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        data_schema = result["data_schema"]
        assert data_schema is not None
        assert set(data_schema.schema) == {
            CONF_STATION_ID,
            CONF_STATION_KEY,
        }

    async def test_create_entry(self, hass: HomeAssistant) -> None:
        """A station creates a config entry with a normalized unique ID."""
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_STATION_ID: f"  {TEST_STATION_ID.lower()}  ",
                CONF_STATION_KEY: TEST_STATION_KEY,
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == TEST_STATION_ID
        assert result["result"].unique_id == TEST_STATION_ID
        assert result["data"][CONF_STATION_ID] == TEST_STATION_ID
        assert CONF_STATION_KEY in result["data"]

    async def test_duplicate_station_aborts(self, hass: HomeAssistant) -> None:
        """An existing Station ID cannot be configured a second time."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=TEST_STATION_ID,
            data={
                CONF_STATION_ID: TEST_STATION_ID,
                CONF_STATION_KEY: TEST_STATION_KEY,
            },
        )
        entry.add_to_hass(hass)

        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_STATION_ID: TEST_STATION_ID.lower(),
                CONF_STATION_KEY: TEST_STATION_KEY,
            },
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"

    async def test_two_different_stations(self, hass: HomeAssistant) -> None:
        """Different Station IDs create independent config entries."""
        for station_id in ("IPRAGUE1", "IBRNO2"):
            result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_STATION_ID: station_id,
                    CONF_STATION_KEY: TEST_STATION_KEY,
                },
            )
            assert result["type"] is FlowResultType.CREATE_ENTRY

        entries = hass.config_entries.async_entries(DOMAIN)
        assert {entry.unique_id for entry in entries} == {"IPRAGUE1", "IBRNO2"}

    async def test_options_flow_is_available(self, hass: HomeAssistant) -> None:
        """A configured station exposes every optional entity mapping."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=TEST_STATION_ID,
            data={
                CONF_STATION_ID: TEST_STATION_ID,
                CONF_STATION_KEY: TEST_STATION_KEY,
            },
        )
        entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(entry.entry_id)

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"
        data_schema = result["data_schema"]
        assert data_schema is not None
        assert set(data_schema.schema) == {spec.option_key for spec in MAPPING_SPECS}

    async def test_options_flow_saves_entity_mappings(self, hass: HomeAssistant) -> None:
        """Submitted entity mappings are stored as config-entry options."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=TEST_STATION_ID,
            data={
                CONF_STATION_ID: TEST_STATION_ID,
                CONF_STATION_KEY: TEST_STATION_KEY,
            },
        )
        entry.add_to_hass(hass)
        result = await hass.config_entries.options.async_init(entry.entry_id)

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_TEMPERATURE: "sensor.outdoor_temperature",
                CONF_HUMIDITY: "input_number.outdoor_humidity",
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert entry.options == {
            CONF_TEMPERATURE: "sensor.outdoor_temperature",
            CONF_HUMIDITY: "input_number.outdoor_humidity",
        }
