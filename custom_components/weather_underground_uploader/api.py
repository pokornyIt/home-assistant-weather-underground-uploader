"""Asynchronous Weather Underground PWS upload client."""

from collections.abc import Mapping
from http import HTTPStatus
from typing import Final

from aiohttp import ClientError, ClientSession, ClientTimeout

UPLOAD_ENDPOINT: Final = "https://weatherstation.wunderground.com/weatherstation/updateweatherstation.php"
SOFTWARE_TYPE: Final = "home-assistant-weather-underground-uploader"
DEFAULT_TIMEOUT_SECONDS: Final = 10.0
MAX_RESPONSE_BYTES: Final = 4096

_SUCCESS_RESPONSE: Final = "success"
_AUTHENTICATION_ERROR_PREFIX: Final = "INVALIDPASSWORDID"
_RESERVED_FIELDS: Final = frozenset({"ID", "PASSWORD", "dateutc", "softwaretype", "action"})


class WeatherUndergroundError(Exception):
    """Base class for sanitized Weather Underground client errors."""


class WeatherUndergroundAuthenticationError(WeatherUndergroundError):
    """Raised when Weather Underground rejects station credentials."""


class WeatherUndergroundRateLimitError(WeatherUndergroundError):
    """Raised when Weather Underground rate-limits an upload."""


class WeatherUndergroundConnectionError(WeatherUndergroundError):
    """Raised for timeouts, transport errors, and server failures."""


class WeatherUndergroundResponseError(WeatherUndergroundError):
    """Raised when Weather Underground returns an unexpected response."""

    def __init__(self, status: int) -> None:
        """Initialize an unexpected-response error.

        :param status: Credential-free HTTP response status.
        """
        super().__init__("Weather Underground returned an unexpected response")
        self.status: int = status


class WeatherUndergroundClient:
    """Send normalized observation fields to Weather Underground."""

    __slots__ = ("_session", "_station_id", "_station_key", "_timeout")

    def __init__(
        self,
        session: ClientSession,
        station_id: str,
        station_key: str,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Initialize the Weather Underground client.

        :param session: Shared asynchronous HTTP session.
        :param station_id: Weather Underground PWS Station ID.
        :param station_key: Weather Underground PWS Station Key.
        :param timeout: Total request timeout in seconds.
        :raises ValueError: If credentials are empty or timeout is not positive.
        """
        if not station_id or not station_key:
            raise ValueError("Weather Underground station credentials must not be empty")
        if timeout <= 0:
            raise ValueError("Weather Underground request timeout must be positive")

        self._session: ClientSession = session
        self._station_id: str = station_id
        self._station_key: str = station_key
        self._timeout: ClientTimeout = ClientTimeout(total=timeout)

    async def async_upload(self, observation: Mapping[str, str]) -> None:
        """Upload one observation containing normalized protocol fields.

        The observation values must already use Weather Underground field names,
        semantics, and units. This client only adds protocol metadata and sends
        the request.

        :param observation: Non-empty normalized Weather Underground fields.
        :raises ValueError: If the observation is empty or overrides protocol metadata.
        :raises WeatherUndergroundConnectionError: If transport fails.
        """
        if not observation:
            raise ValueError("Weather Underground observation must not be empty")
        if _RESERVED_FIELDS.intersection(observation):
            raise ValueError("Weather Underground observation contains reserved fields")

        parameters: dict[str, str] = {
            "ID": self._station_id,
            "PASSWORD": self._station_key,
            "dateutc": "now",
            "softwaretype": SOFTWARE_TYPE,
            "action": "updateraw",
            **observation,
        }

        try:
            async with self._session.get(
                UPLOAD_ENDPOINT,
                params=parameters,
                timeout=self._timeout,
                allow_redirects=False,
            ) as response:
                status: int = response.status
                response_body: bytes = await response.content.read(MAX_RESPONSE_BYTES + 1)
        except TimeoutError, ClientError:
            raise WeatherUndergroundConnectionError("Unable to reach Weather Underground") from None

        self._validate_response(status, response_body)

    @staticmethod
    def _validate_response(status: int, response_body: bytes) -> None:
        """Validate a bounded Weather Underground protocol response.

        :param status: HTTP response status.
        :param response_body: Bounded raw response body.
        :raises WeatherUndergroundAuthenticationError: If credentials are rejected.
        :raises WeatherUndergroundRateLimitError: If the request is rate-limited.
        :raises WeatherUndergroundConnectionError: If the service is unavailable.
        :raises WeatherUndergroundResponseError: If the response is unexpected.
        """
        if status == HTTPStatus.TOO_MANY_REQUESTS:
            raise WeatherUndergroundRateLimitError("Weather Underground rate limit exceeded")
        if status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            raise WeatherUndergroundAuthenticationError("Weather Underground rejected the station credentials")
        if status == HTTPStatus.REQUEST_TIMEOUT or status >= HTTPStatus.INTERNAL_SERVER_ERROR:
            raise WeatherUndergroundConnectionError("Weather Underground service is unavailable")
        if status != HTTPStatus.OK or len(response_body) > MAX_RESPONSE_BYTES:
            raise WeatherUndergroundResponseError(status)

        body: str = response_body.decode("utf-8", errors="replace").strip()
        if body.startswith(_AUTHENTICATION_ERROR_PREFIX):
            raise WeatherUndergroundAuthenticationError("Weather Underground rejected the station credentials")
        if body != _SUCCESS_RESPONSE:
            raise WeatherUndergroundResponseError(status)
