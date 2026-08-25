"""Tests for upload coordination and operational entities."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT, STATE_UNAVAILABLE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.weather_underground_uploader.api import (
    WeatherUndergroundAuthenticationError,
    WeatherUndergroundClient,
    WeatherUndergroundConnectionError,
)
from custom_components.weather_underground_uploader.const import (
    CONF_STATION_ID,
    CONF_STATION_KEY,
    CONF_TEMPERATURE,
    CONF_UPLOAD_INTERVAL,
    DOMAIN,
)
from custom_components.weather_underground_uploader.coordinator import (
    UploadStatus,
    WeatherUndergroundUploadCoordinator,
)


def _create_entry(
    hass: HomeAssistant,
    *,
    station_id: str = "IPRAGUE1",
    interval: int = 300,
    mapped: bool = True,
) -> MockConfigEntry:
    """Create a synthetic configured station."""
    options: dict[str, str | int] = {CONF_UPLOAD_INTERVAL: interval}
    if mapped:
        options[CONF_TEMPERATURE] = f"sensor.{station_id.lower()}_temperature"
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=station_id,
        unique_id=station_id,
        data={
            CONF_STATION_ID: station_id,
            CONF_STATION_KEY: "synthetic-test-key",
        },
        options=options,
    )
    entry.add_to_hass(hass)
    if mapped:
        hass.states.async_set(
            entry.options[CONF_TEMPERATURE],
            "20",
            {ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS},
        )
    return entry


async def _setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Set up an entry and wait for its platforms."""
    if entry.state is ConfigEntryState.NOT_LOADED:
        assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED


async def _unload_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Unload an entry and cancel its coordinator timer."""
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_successful_upload_updates_operational_entities(hass: HomeAssistant) -> None:
    """A successful cycle publishes timestamps, status, and a reset counter."""
    entry = _create_entry(hass)
    upload = AsyncMock()
    with patch.object(WeatherUndergroundClient, "async_upload", upload):
        await _setup_entry(hass, entry)

    upload.assert_awaited_once_with({"tempf": "68"})
    assert entry.runtime_data.coordinator.data.status is UploadStatus.SUCCESS
    status_state = hass.states.get("sensor.weather_underground_iprague1_upload_status")
    failures_state = hass.states.get("sensor.weather_underground_iprague1_consecutive_failures")
    attempt_state = hass.states.get("sensor.weather_underground_iprague1_last_upload_attempt")
    success_state = hass.states.get("sensor.weather_underground_iprague1_last_successful_upload")
    assert status_state is not None and status_state.state == UploadStatus.SUCCESS
    assert failures_state is not None and failures_state.state == "0"
    assert attempt_state is not None and attempt_state.state not in (
        "unknown",
        "unavailable",
    )
    assert success_state is not None and success_state.state not in (
        "unknown",
        "unavailable",
    )
    await _unload_entry(hass, entry)


async def test_empty_observation_does_not_call_api(hass: HomeAssistant) -> None:
    """A cycle with no valid measurement reports no data without a request."""
    entry = _create_entry(hass)
    hass.states.async_remove(entry.options[CONF_TEMPERATURE])
    upload = AsyncMock()
    with patch.object(WeatherUndergroundClient, "async_upload", upload):
        await _setup_entry(hass, entry)

    upload.assert_not_awaited()
    assert entry.runtime_data.coordinator.data.status is UploadStatus.NO_DATA
    assert entry.runtime_data.coordinator.data.consecutive_failures == 1
    await _unload_entry(hass, entry)


async def test_unmapped_station_remains_idle_and_unscheduled(hass: HomeAssistant) -> None:
    """A station without mappings stays idle and disables test upload."""
    entry = _create_entry(hass, mapped=False)
    upload = AsyncMock()
    with patch.object(WeatherUndergroundClient, "async_upload", upload):
        await _setup_entry(hass, entry)
        coordinator = entry.runtime_data.coordinator
        await coordinator.async_refresh()

    upload.assert_not_awaited()
    assert coordinator.update_interval is None
    assert coordinator.data.status is UploadStatus.IDLE
    assert coordinator.data.last_attempt is None
    assert coordinator.data.consecutive_failures == 0
    button_state = hass.states.get("button.weather_underground_iprague1_test_upload")
    assert button_state is not None and button_state.state == STATE_UNAVAILABLE
    await _unload_entry(hass, entry)


async def test_transient_failure_recovers_on_next_cycle(hass: HomeAssistant) -> None:
    """A temporary API failure leaves the entry loaded and later recovers."""
    entry = _create_entry(hass)
    upload = AsyncMock(side_effect=[WeatherUndergroundConnectionError("temporary failure"), None])
    with patch.object(WeatherUndergroundClient, "async_upload", upload):
        await _setup_entry(hass, entry)
        coordinator = entry.runtime_data.coordinator
        assert coordinator.data.status is UploadStatus.ERROR
        assert coordinator.data.consecutive_failures == 1
        assert entry.state is ConfigEntryState.LOADED

        await coordinator.async_refresh()

    assert coordinator.data.status is UploadStatus.SUCCESS
    assert coordinator.data.consecutive_failures == 0
    assert upload.await_count == 2
    await _unload_entry(hass, entry)


async def test_authentication_failure_starts_reauth(hass: HomeAssistant) -> None:
    """Rejected credentials stop scheduling and start the linked repair flow."""
    entry = _create_entry(hass)
    upload = AsyncMock(side_effect=WeatherUndergroundAuthenticationError("rejected"))
    with (
        patch.object(WeatherUndergroundClient, "async_upload", upload),
        patch.object(WeatherUndergroundUploadCoordinator, "async_config_entry_first_refresh", AsyncMock()),
    ):
        await _setup_entry(hass, entry)
        coordinator = entry.runtime_data.coordinator
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    assert coordinator.data.status is UploadStatus.AUTHENTICATION_ERROR
    assert not coordinator.last_update_success
    flows = list(entry.async_get_active_flows(hass, {"reauth"}))
    assert len(flows) == 1
    result = await hass.config_entries.flow.async_configure(
        flows[0]["flow_id"],
        {CONF_STATION_KEY: "replacement-synthetic-key"},
    )
    assert result["reason"] == "reauth_successful"
    await hass.async_block_till_done()
    await _unload_entry(hass, entry)


async def test_concurrent_refreshes_do_not_overlap(hass: HomeAssistant) -> None:
    """The coordinator serializes slow upload requests for a station."""
    entry = _create_entry(hass)
    first_started = asyncio.Event()
    release_first = asyncio.Event()
    active = 0
    maximum_active = 0
    calls = 0

    async def slow_upload(_client: WeatherUndergroundClient, _observation: dict[str, str]) -> None:
        nonlocal active, calls, maximum_active
        calls += 1
        active += 1
        maximum_active = max(maximum_active, active)
        if calls == 1:
            first_started.set()
            await release_first.wait()
        active -= 1

    with (
        patch.object(WeatherUndergroundClient, "async_upload", slow_upload),
        patch.object(WeatherUndergroundUploadCoordinator, "async_config_entry_first_refresh", AsyncMock()),
    ):
        await _setup_entry(hass, entry)
        coordinator = entry.runtime_data.coordinator
        first = asyncio.create_task(coordinator.async_refresh())
        await first_started.wait()
        second = asyncio.create_task(coordinator.async_refresh())
        await asyncio.sleep(0)
        assert calls == 1
        release_first.set()
        await asyncio.gather(first, second)

    assert calls == 2
    assert maximum_active == 1
    await _unload_entry(hass, entry)


async def test_test_upload_does_not_overlap_scheduled_upload(hass: HomeAssistant) -> None:
    """Test and normal uploads share the station request lock."""
    entry = _create_entry(hass)
    first_started = asyncio.Event()
    release_first = asyncio.Event()
    active = 0
    maximum_active = 0
    calls = 0

    async def slow_upload(_client: WeatherUndergroundClient, _observation: dict[str, str]) -> None:
        nonlocal active, calls, maximum_active
        calls += 1
        active += 1
        maximum_active = max(maximum_active, active)
        if calls == 1:
            first_started.set()
            await release_first.wait()
        active -= 1

    with (
        patch.object(WeatherUndergroundClient, "async_upload", slow_upload),
        patch.object(WeatherUndergroundUploadCoordinator, "async_config_entry_first_refresh", AsyncMock()),
    ):
        await _setup_entry(hass, entry)
        coordinator = entry.runtime_data.coordinator
        scheduled = asyncio.create_task(coordinator.async_refresh())
        await first_started.wait()
        test = asyncio.create_task(coordinator.async_test_upload())
        await asyncio.sleep(0)
        assert calls == 1
        release_first.set()
        await asyncio.gather(scheduled, test)

    assert calls == 2
    assert maximum_active == 1
    await _unload_entry(hass, entry)


async def test_stations_have_independent_coordinators(hass: HomeAssistant) -> None:
    """Each config entry owns its client, interval, and coordinator state."""
    first = _create_entry(hass, station_id="IPRAGUE1", interval=120)
    second = _create_entry(hass, station_id="IBRNO2", interval=600)
    with patch.object(WeatherUndergroundClient, "async_upload", AsyncMock()):
        await _setup_entry(hass, first)
        await _setup_entry(hass, second)

    assert first.runtime_data.client is not second.runtime_data.client
    assert first.runtime_data.coordinator is not second.runtime_data.coordinator
    assert first.runtime_data.coordinator.update_interval is not None
    assert second.runtime_data.coordinator.update_interval is not None
    assert first.runtime_data.coordinator.update_interval.total_seconds() == 120
    assert second.runtime_data.coordinator.update_interval.total_seconds() == 600

    await _unload_entry(hass, first)
    await _unload_entry(hass, second)


async def test_first_mapping_reloads_and_uploads_immediately(hass: HomeAssistant) -> None:
    """Saving the first mapping enables scheduling and uploads immediately."""
    entry = _create_entry(hass, interval=300, mapped=False)
    upload = AsyncMock()
    with patch.object(WeatherUndergroundClient, "async_upload", upload):
        await _setup_entry(hass, entry)
        previous_coordinator = entry.runtime_data.coordinator
        assert previous_coordinator.update_interval is None

        temperature_entity = "sensor.synthetic_temperature"
        hass.states.async_set(
            temperature_entity,
            "20",
            {ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS},
        )
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_TEMPERATURE: temperature_entity,
                CONF_UPLOAD_INTERVAL: 120,
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == "create_entry"
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.coordinator is not previous_coordinator
    assert entry.runtime_data.coordinator.update_interval is not None
    assert entry.runtime_data.coordinator.update_interval.total_seconds() == 120
    upload.assert_awaited_once_with({"tempf": "68"})
    await _unload_entry(hass, entry)


async def test_upload_button_sends_test_observation(hass: HomeAssistant) -> None:
    """A successful test uploads current data without changing operational state."""
    entry = _create_entry(hass)
    upload = AsyncMock()
    with patch.object(WeatherUndergroundClient, "async_upload", upload):
        await _setup_entry(hass, entry)
        state_before_test = entry.runtime_data.coordinator.data
        upload.reset_mock()
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.weather_underground_iprague1_test_upload"},
            blocking=True,
        )
        await hass.async_block_till_done()

    upload.assert_awaited_once_with({"tempf": "68"})
    assert entry.runtime_data.coordinator.data is state_before_test
    await _unload_entry(hass, entry)


async def test_test_upload_reports_invalid_credentials_and_starts_reauth(hass: HomeAssistant) -> None:
    """A rejected test upload reports invalid credentials without changing counters."""
    entry = _create_entry(hass)
    upload = AsyncMock(side_effect=[None, WeatherUndergroundAuthenticationError("rejected")])
    with patch.object(WeatherUndergroundClient, "async_upload", upload):
        await _setup_entry(hass, entry)
        state_before_test = entry.runtime_data.coordinator.data

        with pytest.raises(HomeAssistantError) as error:
            await hass.services.async_call(
                "button",
                "press",
                {"entity_id": "button.weather_underground_iprague1_test_upload"},
                blocking=True,
            )
        await hass.async_block_till_done()

    assert error.value.translation_domain == DOMAIN
    assert error.value.translation_key == "test_upload_invalid_auth"
    assert entry.runtime_data.coordinator.data is state_before_test
    assert len(list(entry.async_get_active_flows(hass, {"reauth"}))) == 1
    await _unload_entry(hass, entry)


async def test_test_upload_reports_transient_failure(hass: HomeAssistant) -> None:
    """A transient test failure is distinct from invalid credentials."""
    entry = _create_entry(hass)
    upload = AsyncMock(side_effect=[None, WeatherUndergroundConnectionError("temporary failure")])
    with patch.object(WeatherUndergroundClient, "async_upload", upload):
        await _setup_entry(hass, entry)
        state_before_test = entry.runtime_data.coordinator.data

        with pytest.raises(HomeAssistantError) as error:
            await hass.services.async_call(
                "button",
                "press",
                {"entity_id": "button.weather_underground_iprague1_test_upload"},
                blocking=True,
            )

    assert error.value.translation_domain == DOMAIN
    assert error.value.translation_key == "test_upload_failed"
    assert entry.runtime_data.coordinator.data is state_before_test
    assert not list(entry.async_get_active_flows(hass, {"reauth"}))
    await _unload_entry(hass, entry)


async def test_test_upload_requires_a_currently_valid_measurement(hass: HomeAssistant) -> None:
    """A configured mapping without valid data produces an actionable error."""
    entry = _create_entry(hass)
    upload = AsyncMock()
    with patch.object(WeatherUndergroundClient, "async_upload", upload):
        await _setup_entry(hass, entry)
        state_before_test = entry.runtime_data.coordinator.data
        upload.reset_mock()
        hass.states.async_remove(entry.options[CONF_TEMPERATURE])

        with pytest.raises(ServiceValidationError) as error:
            await hass.services.async_call(
                "button",
                "press",
                {"entity_id": "button.weather_underground_iprague1_test_upload"},
                blocking=True,
            )

    assert error.value.translation_domain == DOMAIN
    assert error.value.translation_key == "test_upload_no_data"
    upload.assert_not_awaited()
    assert entry.runtime_data.coordinator.data is state_before_test
    await _unload_entry(hass, entry)
