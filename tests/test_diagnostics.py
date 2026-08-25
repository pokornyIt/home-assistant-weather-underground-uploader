"""Tests for secret-safe integration diagnostics."""

import json
from datetime import UTC, datetime
from typing import Final

from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import REDACTED
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.weather_underground_uploader.const import (
    CONF_HUMIDITY,
    CONF_STATION_ID,
    CONF_STATION_KEY,
    CONF_TEMPERATURE,
    CONF_UPLOAD_INTERVAL,
    DOMAIN,
)
from custom_components.weather_underground_uploader.coordinator import UploadState, UploadStatus
from custom_components.weather_underground_uploader.diagnostics import async_get_config_entry_diagnostics

TEST_STATION_KEY: Final = "synthetic-diagnostics-secret-marker"


async def test_config_entry_diagnostics_are_useful_and_redacted(hass: HomeAssistant) -> None:
    """Diagnostics include selected operational data but never the Station Key."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="IPRAGUE1",
        unique_id="IPRAGUE1",
        data={
            CONF_STATION_ID: "IPRAGUE1",
            CONF_STATION_KEY: TEST_STATION_KEY,
        },
        options={
            CONF_UPLOAD_INTERVAL: 120,
            CONF_TEMPERATURE: "sensor.outdoor_temperature",
            CONF_HUMIDITY: "input_number.outdoor_humidity",
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    upload_time = datetime(2026, 8, 22, 12, 30, tzinfo=UTC)
    entry.runtime_data.coordinator.data = UploadState(
        status=UploadStatus.ERROR,
        last_attempt=upload_time,
        last_success=None,
        consecutive_failures=3,
    )
    mapping_problems = entry.runtime_data.coordinator.mapping_problems
    assert set(mapping_problems) == {CONF_TEMPERATURE, CONF_HUMIDITY}

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics == {
        "integration": {"version": "0.1.2"},
        "config_entry": {
            CONF_STATION_ID: "IPRAGUE1",
            CONF_STATION_KEY: REDACTED,
        },
        "configuration": {
            "upload_interval": 120,
            "mappings": {
                CONF_TEMPERATURE: "sensor.outdoor_temperature",
                CONF_HUMIDITY: "input_number.outdoor_humidity",
            },
        },
        "upload": {
            "status": "error",
            "last_attempt": "2026-08-22T12:30:00+00:00",
            "last_success": None,
            "consecutive_failures": 3,
        },
        "mapping_problems": {
            mapping_key: {
                "entity_id": problem.entity_id,
                "type": "missing_entity",
                "first_detected": problem.first_detected.isoformat(),
                "last_detected": problem.last_detected.isoformat(),
                "consecutive_occurrences": 1,
                "persistent": False,
            }
            for mapping_key, problem in mapping_problems.items()
        },
    }
    assert TEST_STATION_KEY not in json.dumps(diagnostics)
    assert entry.data[CONF_STATION_KEY] == TEST_STATION_KEY

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
