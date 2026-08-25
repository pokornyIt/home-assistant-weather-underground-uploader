"""Tests for Home Assistant Repairs support."""

from unittest.mock import AsyncMock, patch

from homeassistant.components.repairs import repairs_flow_manager
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT, CONF_ENTITY_ID, STATE_UNAVAILABLE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.weather_underground_uploader.api import (
    WeatherUndergroundClient,
    WeatherUndergroundConnectionError,
)
from custom_components.weather_underground_uploader.const import (
    CONF_HUMIDITY,
    CONF_STATION_ID,
    CONF_STATION_KEY,
    CONF_TEMPERATURE,
    CONF_UPLOAD_INTERVAL,
    DOMAIN,
)
from custom_components.weather_underground_uploader.coordinator import (
    PERSISTENT_MAPPING_PROBLEM_OCCURRENCES,
)
from custom_components.weather_underground_uploader.repairs import mapping_issue_id
from custom_components.weather_underground_uploader.selectors import WEATHER_SOURCE_ENTITY_SELECTOR


def _create_entry(hass: HomeAssistant, station_id: str = "IPRAGUE1") -> MockConfigEntry:
    """Create a synthetic station with one invalid and one valid mapping."""
    temperature_entity = f"sensor.{station_id.lower()}_temperature"
    humidity_entity = f"sensor.{station_id.lower()}_humidity"
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=station_id,
        unique_id=station_id,
        data={
            CONF_STATION_ID: station_id,
            CONF_STATION_KEY: "synthetic-test-key",
        },
        options={
            CONF_UPLOAD_INTERVAL: 300,
            CONF_TEMPERATURE: temperature_entity,
            CONF_HUMIDITY: humidity_entity,
        },
    )
    entry.add_to_hass(hass)
    hass.states.async_set(temperature_entity, STATE_UNAVAILABLE)
    hass.states.async_set(humidity_entity, "55")
    return entry


async def _setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Set up a station and wait for platform forwarding."""
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def _unload_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Unload a station and cancel its coordinator timer."""
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_persistent_mapping_issue_is_deduplicated_and_resolved(hass: HomeAssistant) -> None:
    """A repeated mapping failure creates one issue that recovery removes."""
    entry = _create_entry(hass)
    upload = AsyncMock()
    issue_id = mapping_issue_id(entry.entry_id, CONF_TEMPERATURE)
    registry = ir.async_get(hass)

    with patch.object(WeatherUndergroundClient, "async_upload", upload):
        await _setup_entry(hass, entry)
        coordinator = entry.runtime_data.coordinator
        assert registry.async_get_issue(DOMAIN, issue_id) is None

        for _ in range(PERSISTENT_MAPPING_PROBLEM_OCCURRENCES - 1):
            await coordinator.async_refresh()

        issue = registry.async_get_issue(DOMAIN, issue_id)
        assert issue is not None
        assert issue.data is not None
        assert issue.is_fixable
        assert not issue.is_persistent
        assert issue.severity is ir.IssueSeverity.WARNING
        assert issue.translation_key == "mapping_problem"
        assert issue.data == {
            "entry_id": entry.entry_id,
            "mapping_key": CONF_TEMPERATURE,
            "entity_id": entry.options[CONF_TEMPERATURE],
            "problem_type": "unavailable",
        }
        assert issue.translation_placeholders == {
            "entity_id": entry.options[CONF_TEMPERATURE],
            "mapping": CONF_TEMPERATURE,
            "station": "IPRAGUE1",
        }
        assert CONF_STATION_KEY not in issue.data
        created = issue.created

        await coordinator.async_refresh()
        deduplicated = registry.async_get_issue(DOMAIN, issue_id)
        assert deduplicated is not None
        assert deduplicated is issue
        assert deduplicated.created == created

        hass.states.async_set(
            entry.options[CONF_TEMPERATURE],
            "20",
            {ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS},
        )
        await coordinator.async_refresh()

    assert registry.async_get_issue(DOMAIN, issue_id) is None
    assert upload.await_count == PERSISTENT_MAPPING_PROBLEM_OCCURRENCES + 2
    await _unload_entry(hass, entry)


async def test_transient_network_failures_do_not_create_repairs(hass: HomeAssistant) -> None:
    """Repeated Weather Underground outages do not create Repairs issues."""
    entry = _create_entry(hass)
    hass.states.async_set(
        entry.options[CONF_TEMPERATURE],
        "20",
        {ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS},
    )
    upload = AsyncMock(side_effect=WeatherUndergroundConnectionError("synthetic outage"))

    with patch.object(WeatherUndergroundClient, "async_upload", upload):
        await _setup_entry(hass, entry)
        coordinator = entry.runtime_data.coordinator
        for _ in range(PERSISTENT_MAPPING_PROBLEM_OCCURRENCES):
            await coordinator.async_refresh()

    assert not [issue for (domain, _), issue in ir.async_get(hass).issues.items() if domain == DOMAIN]
    await _unload_entry(hass, entry)


async def test_mapping_repair_flow_replaces_only_affected_option(hass: HomeAssistant) -> None:
    """The fix flow replaces one mapping and preserves every other option."""
    entry = _create_entry(hass)
    issue_id = mapping_issue_id(entry.entry_id, CONF_TEMPERATURE)
    assert await async_setup_component(hass, "repairs", {})
    upload = AsyncMock()
    with patch.object(WeatherUndergroundClient, "async_upload", upload):
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

        issue_data: dict[str, str | int | float | None] = {
            "entry_id": entry.entry_id,
            "mapping_key": CONF_TEMPERATURE,
            "entity_id": entry.options[CONF_TEMPERATURE],
            "problem_type": "missing_entity",
        }
        ir.async_create_issue(
            hass=hass,
            domain=DOMAIN,
            issue_id=issue_id,
            data=issue_data,
            is_fixable=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key="mapping_problem",
        )
        manager = repairs_flow_manager(hass)
        assert manager is not None

        result = await manager.async_init(DOMAIN, data={"issue_id": issue_id})

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "mapping"
        data_schema = result["data_schema"]
        assert data_schema is not None
        assert {key.schema for key in data_schema.schema} == {CONF_ENTITY_ID}
        assert list(data_schema.schema.values()) == [WEATHER_SOURCE_ENTITY_SELECTOR]

        replacement = "sensor.replacement_temperature"
        reload_entry = AsyncMock(return_value=True)
        with patch.object(hass.config_entries, "async_reload", reload_entry):
            result = await manager.async_configure(
                result["flow_id"],
                {CONF_ENTITY_ID: replacement},
            )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert entry.options == {
            CONF_UPLOAD_INTERVAL: 300,
            CONF_TEMPERATURE: replacement,
            CONF_HUMIDITY: "sensor.iprague1_humidity",
        }
        reload_entry.assert_awaited_once_with(entry.entry_id)
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
        await _unload_entry(hass, entry)
