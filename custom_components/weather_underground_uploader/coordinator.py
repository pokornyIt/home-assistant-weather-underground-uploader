"""Coordinate Weather Underground uploads for one config entry."""

import asyncio
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any, Final, override

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .api import WeatherUndergroundAuthenticationError, WeatherUndergroundClient, WeatherUndergroundError
from .const import CONF_UPLOAD_INTERVAL, DEFAULT_UPLOAD_INTERVAL_SECONDS
from .mapping import build_observation, build_observation_result
from .models import MappingProblemType, MappingValidationProblem, has_configured_mapping
from .repairs import async_sync_mapping_issues

_LOGGER = logging.getLogger(__name__)
PERSISTENT_MAPPING_PROBLEM_OCCURRENCES: Final = 3


class UploadStatus(StrEnum):
    """Operational result of the most recent upload cycle."""

    IDLE = "idle"
    SUCCESS = "success"
    NO_DATA = "no_data"
    ERROR = "error"
    AUTHENTICATION_ERROR = "authentication_error"


@dataclass(frozen=True, slots=True)
class UploadState:
    """Current non-sensitive operational upload state."""

    status: UploadStatus = UploadStatus.IDLE
    last_attempt: datetime | None = None
    last_success: datetime | None = None
    consecutive_failures: int = 0


@dataclass(frozen=True, slots=True)
class MappingProblemState:
    """Track one mapping problem across consecutive upload cycles."""

    mapping_key: str
    entity_id: str
    problem_type: MappingProblemType
    first_detected: datetime
    last_detected: datetime
    consecutive_occurrences: int = 1

    @property
    def persistent(self) -> bool:
        """Return whether the problem has repeated enough to be actionable."""
        return self.consecutive_occurrences >= PERSISTENT_MAPPING_PROBLEM_OCCURRENCES


def mapping_problem_details(
    problems: Mapping[str, MappingProblemState],
) -> dict[str, dict[str, str | int | bool]]:
    """Serialize current mapping problems without station credentials.

    :param problems: Current mapping problem states keyed by mapping option.
    :return: Safe serializable mapping problem details.
    """
    return {
        mapping_key: {
            "entity_id": problem.entity_id,
            "type": problem.problem_type.value,
            "first_detected": problem.first_detected.isoformat(),
            "last_detected": problem.last_detected.isoformat(),
            "consecutive_occurrences": problem.consecutive_occurrences,
            "persistent": problem.persistent,
        }
        for mapping_key, problem in problems.items()
    }


class TestUploadNoDataError(Exception):
    """Raised when no currently valid mapped measurement can be tested."""


class WeatherUndergroundUploadCoordinator(DataUpdateCoordinator[UploadState]):
    """Schedule serialized uploads and publish their operational state."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry[Any],
        client: WeatherUndergroundClient,
    ) -> None:
        """Initialize a station upload coordinator.

        :param hass: Home Assistant instance.
        :param entry: Weather Underground station config entry.
        :param client: Credential-safe upload client.
        """
        interval_seconds = int(entry.options.get(CONF_UPLOAD_INTERVAL, DEFAULT_UPLOAD_INTERVAL_SECONDS))
        self.upload_enabled: bool = has_configured_mapping(entry.options)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"Weather Underground Uploader {entry.title}",
            update_interval=timedelta(seconds=interval_seconds) if self.upload_enabled else None,
        )
        self.data = UploadState()
        self._entry = entry
        self._client = client
        self._upload_lock = asyncio.Lock()
        self._transient_failure_logged = False
        self._mapping_problems: dict[str, MappingProblemState] = {}

    @property
    def mapping_problems(self) -> Mapping[str, MappingProblemState]:
        """Return currently detected problems keyed by mapped measurement."""
        return self._mapping_problems

    async def async_test_upload(self) -> None:
        """Send a test observation without changing normal upload state.

        :raises TestUploadNoDataError: If no mapped measurement is currently valid.
        """
        observation = build_observation(self.hass, self._entry.options, now=dt_util.utcnow())
        if not observation:
            raise TestUploadNoDataError

        async with self._upload_lock:
            await self._client.async_upload(observation)

    @override
    async def _async_update_data(self) -> UploadState:
        """Build and upload one fresh observation.

        :return: The resulting operational upload state.
        :raises ConfigEntryAuthFailed: If station credentials are rejected.
        """
        if not self.upload_enabled:
            return self.data

        attempted_at = dt_util.utcnow()
        result = build_observation_result(self.hass, self._entry.options, now=attempted_at)
        self._update_mapping_problems(result.problems, attempted_at)
        observation = result.observation
        if not observation:
            return UploadState(
                status=UploadStatus.NO_DATA,
                last_attempt=attempted_at,
                last_success=self.data.last_success,
                consecutive_failures=self.data.consecutive_failures + 1,
            )

        try:
            async with self._upload_lock:
                await self._client.async_upload(observation)
        except WeatherUndergroundAuthenticationError as err:
            self.data = UploadState(
                status=UploadStatus.AUTHENTICATION_ERROR,
                last_attempt=attempted_at,
                last_success=self.data.last_success,
                consecutive_failures=self.data.consecutive_failures + 1,
            )
            raise ConfigEntryAuthFailed("Weather Underground station credentials were rejected") from err
        except WeatherUndergroundError:
            failures = self.data.consecutive_failures + 1
            if not self._transient_failure_logged:
                _LOGGER.warning("Weather Underground upload failed; the station will retry automatically")
                self._transient_failure_logged = True
            else:
                _LOGGER.debug("Weather Underground upload remains unavailable")
            return UploadState(
                status=UploadStatus.ERROR,
                last_attempt=attempted_at,
                last_success=self.data.last_success,
                consecutive_failures=failures,
            )

        if self._transient_failure_logged:
            _LOGGER.info("Weather Underground uploads recovered")
            self._transient_failure_logged = False
        return UploadState(
            status=UploadStatus.SUCCESS,
            last_attempt=attempted_at,
            last_success=attempted_at,
            consecutive_failures=0,
        )

    def _update_mapping_problems(
        self,
        current_problems: tuple[MappingValidationProblem, ...],
        detected_at: datetime,
    ) -> None:
        """Advance consecutive problem state and drop recovered mappings.

        :param current_problems: Problems detected during the current cycle.
        :param detected_at: UTC timestamp of the current detection.
        """
        updated: dict[str, MappingProblemState] = {}
        for current in current_problems:
            previous = self._mapping_problems.get(current.mapping_key)
            if (
                previous is not None
                and previous.entity_id == current.entity_id
                and previous.problem_type is current.problem_type
            ):
                updated[current.mapping_key] = MappingProblemState(
                    mapping_key=current.mapping_key,
                    entity_id=current.entity_id,
                    problem_type=current.problem_type,
                    first_detected=previous.first_detected,
                    last_detected=detected_at,
                    consecutive_occurrences=previous.consecutive_occurrences + 1,
                )
            else:
                updated[current.mapping_key] = MappingProblemState(
                    mapping_key=current.mapping_key,
                    entity_id=current.entity_id,
                    problem_type=current.problem_type,
                    first_detected=detected_at,
                    last_detected=detected_at,
                )

        self._mapping_problems = updated
        async_sync_mapping_issues(self.hass, self._entry, self._mapping_problems)
