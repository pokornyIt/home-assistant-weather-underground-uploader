"""Coordinate Weather Underground uploads for one config entry."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any, override

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .api import WeatherUndergroundAuthenticationError, WeatherUndergroundClient, WeatherUndergroundError
from .const import CONF_UPLOAD_INTERVAL, DEFAULT_UPLOAD_INTERVAL_SECONDS
from .mapping import build_observation
from .models import has_configured_mapping

_LOGGER = logging.getLogger(__name__)


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
        self._transient_failure_logged = False

    @override
    async def _async_update_data(self) -> UploadState:
        """Build and upload one fresh observation."""
        if not self.upload_enabled:
            return self.data

        attempted_at = dt_util.utcnow()
        observation = build_observation(self.hass, self._entry.options, now=attempted_at)
        if not observation:
            return UploadState(
                status=UploadStatus.NO_DATA,
                last_attempt=attempted_at,
                last_success=self.data.last_success,
                consecutive_failures=self.data.consecutive_failures + 1,
            )

        try:
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
