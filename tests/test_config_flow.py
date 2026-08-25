"""Tests for the Weather Underground Uploader config flow."""

from typing import Final
from unittest.mock import AsyncMock, patch

import voluptuous as vol
import voluptuous_serialize
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import config_validation as cv
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.weather_underground_uploader.api import (
    WeatherUndergroundAuthenticationError,
    WeatherUndergroundClient,
    WeatherUndergroundConnectionError,
)
from custom_components.weather_underground_uploader.const import (
    CONF_HUMIDITY,
    CONF_STATION_ID,
    CONF_STATION_KEY,
    CONF_TEMPERATURE,
    CONF_UPLOAD_INTERVAL,
    DEFAULT_UPLOAD_INTERVAL_SECONDS,
    DOMAIN,
)
from custom_components.weather_underground_uploader.models import MAPPING_SPECS
from custom_components.weather_underground_uploader.selectors import WEATHER_SOURCE_ENTITY_SELECTOR

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
        serialized_schema = voluptuous_serialize.convert(data_schema, custom_serializer=cv.custom_serializer)
        assert len(serialized_schema) == 2

    async def test_empty_normalized_station_id_is_rejected(self, hass: HomeAssistant) -> None:
        """A Station ID containing only whitespace is rejected after normalization."""
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_STATION_ID: "   ",
                CONF_STATION_KEY: TEST_STATION_KEY,
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {CONF_STATION_ID: "invalid_station_id"}

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
        assert set(data_schema.schema) == {
            CONF_UPLOAD_INTERVAL,
            *(spec.option_key for spec in MAPPING_SPECS),
        }
        mapping_selectors = [
            validator for key, validator in data_schema.schema.items() if key.schema != CONF_UPLOAD_INTERVAL
        ]
        assert mapping_selectors == [WEATHER_SOURCE_ENTITY_SELECTOR] * len(MAPPING_SPECS)
        assert WEATHER_SOURCE_ENTITY_SELECTOR.config["filter"] == [{"domain": ["sensor", "input_number"]}]

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
            CONF_UPLOAD_INTERVAL: float(DEFAULT_UPLOAD_INTERVAL_SECONDS),
        }
        await hass.async_block_till_done()
        assert await hass.config_entries.async_unload(entry.entry_id)

    async def test_reauthentication_updates_only_station_key(self, hass: HomeAssistant) -> None:
        """Reauthentication replaces the rejected key and preserves station identity."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=TEST_STATION_ID,
            data={
                CONF_STATION_ID: TEST_STATION_ID,
                CONF_STATION_KEY: TEST_STATION_KEY,
            },
        )
        entry.add_to_hass(hass)
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": entry.entry_id,
            },
            data=dict(entry.data),
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_STATION_KEY: "replacement-synthetic-key"},
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "reauth_successful"
        assert entry.data == {
            CONF_STATION_ID: TEST_STATION_ID,
            CONF_STATION_KEY: "replacement-synthetic-key",
        }
        await hass.async_block_till_done()
        assert await hass.config_entries.async_unload(entry.entry_id)

    async def test_reconfigure_form_does_not_prefill_station_key(self, hass: HomeAssistant) -> None:
        """The native reconfigure form identifies the station without returning its secret."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=TEST_STATION_ID,
            data={
                CONF_STATION_ID: TEST_STATION_ID,
                CONF_STATION_KEY: TEST_STATION_KEY,
            },
        )
        entry.add_to_hass(hass)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reconfigure"
        data_schema = result["data_schema"]
        assert data_schema is not None
        schema_keys = {key.schema: key for key in data_schema.schema}
        assert schema_keys[CONF_STATION_ID].default() == TEST_STATION_ID
        assert schema_keys[CONF_STATION_KEY].default is vol.UNDEFINED

    async def test_reconfigure_rejects_empty_normalized_credentials(self, hass: HomeAssistant) -> None:
        """Whitespace-only credential fields are rejected without changing the entry."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=TEST_STATION_ID,
            data={CONF_STATION_ID: TEST_STATION_ID, CONF_STATION_KEY: TEST_STATION_KEY},
        )
        entry.add_to_hass(hass)

        invalid_inputs = (
            ({CONF_STATION_ID: "   ", CONF_STATION_KEY: "replacement-synthetic-key"}, CONF_STATION_ID),
            ({CONF_STATION_ID: TEST_STATION_ID, CONF_STATION_KEY: "   "}, CONF_STATION_KEY),
        )
        for user_input, invalid_field in invalid_inputs:
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
            )
            result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input)

            assert result["type"] is FlowResultType.FORM
            assert result["errors"] == {
                invalid_field: f"invalid_{invalid_field}",
            }

        assert entry.data == {CONF_STATION_ID: TEST_STATION_ID, CONF_STATION_KEY: TEST_STATION_KEY}

    async def test_reconfigure_updates_credentials_and_preserves_options(self, hass: HomeAssistant) -> None:
        """Valid new credentials update identity without replacing mappings or the entry."""
        options = {
            CONF_TEMPERATURE: "sensor.outdoor_temperature",
            CONF_UPLOAD_INTERVAL: 120,
        }
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=TEST_STATION_ID,
            title=TEST_STATION_ID,
            data={
                CONF_STATION_ID: TEST_STATION_ID,
                CONF_STATION_KEY: TEST_STATION_KEY,
            },
            options=options,
        )
        entry.add_to_hass(hass)
        hass.states.async_set(
            "sensor.outdoor_temperature",
            "20",
            {"unit_of_measurement": "°C"},
        )
        original_entry_id = entry.entry_id
        upload = AsyncMock()

        with (
            patch(
                "custom_components.weather_underground_uploader.config_flow.WeatherUndergroundClient"
            ) as client_class,
            patch.object(hass.config_entries, "async_schedule_reload") as schedule_reload,
        ):
            client_class.return_value.async_upload = upload
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={
                    "source": config_entries.SOURCE_RECONFIGURE,
                    "entry_id": entry.entry_id,
                },
            )
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_STATION_ID: "  ibrno2  ",
                    CONF_STATION_KEY: "replacement-synthetic-key",
                },
            )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "reconfigure_successful"
        assert entry.entry_id == original_entry_id
        assert entry.unique_id == "IBRNO2"
        assert entry.title == "IBRNO2"
        assert entry.data == {
            CONF_STATION_ID: "IBRNO2",
            CONF_STATION_KEY: "replacement-synthetic-key",
        }
        assert entry.options == options
        assert client_class.call_args.kwargs["station_id"] == "IBRNO2"
        assert client_class.call_args.kwargs["station_key"] == "replacement-synthetic-key"
        upload.assert_awaited_once_with({"tempf": "68"})
        schedule_reload.assert_called_once_with(entry.entry_id)

    async def test_reconfigure_rejects_duplicate_station_id(self, hass: HomeAssistant) -> None:
        """A reconfigured Station ID cannot collide with another entry."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=TEST_STATION_ID,
            data={CONF_STATION_ID: TEST_STATION_ID, CONF_STATION_KEY: TEST_STATION_KEY},
        )
        duplicate = MockConfigEntry(
            domain=DOMAIN,
            unique_id="IBRNO2",
            data={CONF_STATION_ID: "IBRNO2", CONF_STATION_KEY: "other-synthetic-key"},
        )
        entry.add_to_hass(hass)
        duplicate.add_to_hass(hass)
        original_data = dict(entry.data)
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_STATION_ID: "ibrno2", CONF_STATION_KEY: "replacement-synthetic-key"},
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"
        assert entry.unique_id == TEST_STATION_ID
        assert entry.data == original_data

    async def test_failed_reconfigure_validation_preserves_credentials(self, hass: HomeAssistant) -> None:
        """Rejected new credentials leave the prior config entry unchanged."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=TEST_STATION_ID,
            data={CONF_STATION_ID: TEST_STATION_ID, CONF_STATION_KEY: TEST_STATION_KEY},
            options={CONF_TEMPERATURE: "sensor.outdoor_temperature"},
        )
        entry.add_to_hass(hass)
        hass.states.async_set("sensor.outdoor_temperature", "20", {"unit_of_measurement": "°C"})
        original_data = dict(entry.data)
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
        )

        with patch.object(
            WeatherUndergroundClient,
            "async_upload",
            AsyncMock(side_effect=WeatherUndergroundAuthenticationError("synthetic rejection")),
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_STATION_ID: "ibrno2", CONF_STATION_KEY: "rejected-synthetic-key"},
            )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reconfigure"
        assert result["errors"] == {"base": "invalid_auth"}
        assert entry.unique_id == TEST_STATION_ID
        assert entry.data == original_data

    async def test_reconfigure_connection_failure_preserves_credentials(self, hass: HomeAssistant) -> None:
        """A temporary validation failure can be retried without changing stored data."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=TEST_STATION_ID,
            data={CONF_STATION_ID: TEST_STATION_ID, CONF_STATION_KEY: TEST_STATION_KEY},
            options={CONF_TEMPERATURE: "sensor.outdoor_temperature"},
        )
        entry.add_to_hass(hass)
        hass.states.async_set("sensor.outdoor_temperature", "20", {"unit_of_measurement": "°C"})
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
        )

        with patch.object(
            WeatherUndergroundClient,
            "async_upload",
            AsyncMock(side_effect=WeatherUndergroundConnectionError("synthetic outage")),
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_STATION_ID: TEST_STATION_ID, CONF_STATION_KEY: "replacement-synthetic-key"},
            )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}
        assert entry.data[CONF_STATION_KEY] == TEST_STATION_KEY

    async def test_reconfigure_without_valid_mapping_skips_validation(self, hass: HomeAssistant) -> None:
        """Credentials remain editable when no observation can be built for validation."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=TEST_STATION_ID,
            data={CONF_STATION_ID: TEST_STATION_ID, CONF_STATION_KEY: TEST_STATION_KEY},
        )
        entry.add_to_hass(hass)
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
        )

        with patch.object(WeatherUndergroundClient, "async_upload", AsyncMock()) as upload:
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_STATION_ID: TEST_STATION_ID, CONF_STATION_KEY: "replacement-synthetic-key"},
            )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "reconfigure_successful"
        assert entry.data[CONF_STATION_KEY] == "replacement-synthetic-key"
        upload.assert_not_awaited()
