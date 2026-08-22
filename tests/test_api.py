"""Tests for the Weather Underground upload client."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from http import HTTPStatus
from typing import Final, cast

import pytest
from aiohttp import ClientConnectionError, ClientSession
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)
from yarl import URL

from custom_components.weather_underground_uploader.api import (
    MAX_RESPONSE_BYTES,
    SOFTWARE_TYPE,
    UPLOAD_ENDPOINT,
    WeatherUndergroundAuthenticationError,
    WeatherUndergroundClient,
    WeatherUndergroundConnectionError,
    WeatherUndergroundRateLimitError,
    WeatherUndergroundResponseError,
)

TEST_STATION_ID: Final = "IPRAGUE1"
TEST_STATION_KEY: Final = "synthetic-secret-marker"
TEST_OBSERVATION: Final = {"tempf": "68", "humidity": "50"}


@pytest.fixture
async def client_session(
    aioclient_mock: AiohttpClientMocker,
) -> AsyncGenerator[ClientSession]:
    """Create an aiohttp session connected to the request mocker.

    :param aioclient_mock: Aiohttp request mocker.
    :return: Managed asynchronous HTTP session.
    """
    session: ClientSession = aioclient_mock.create_session(asyncio.get_running_loop())
    yield session
    await session.close()


class TestWeatherUndergroundClient:
    """Verify upload protocol behavior and sanitized failures."""

    async def test_uploads_normalized_observation(
        self,
        aioclient_mock: AiohttpClientMocker,
        client_session: ClientSession,
    ) -> None:
        """A successful response accepts a normalized partial observation."""
        aioclient_mock.get(UPLOAD_ENDPOINT, text="success")
        client = WeatherUndergroundClient(client_session, TEST_STATION_ID, TEST_STATION_KEY)

        await client.async_upload(TEST_OBSERVATION)

        assert aioclient_mock.call_count == 1
        request_url: URL = cast(URL, aioclient_mock.mock_calls[0][1])
        assert request_url.scheme == "https"
        assert request_url.query["dateutc"] == "now"
        assert request_url.query["softwaretype"] == SOFTWARE_TYPE
        assert request_url.query["action"] == "updateraw"
        assert request_url.query["tempf"] == "68"
        assert request_url.query["humidity"] == "50"
        assert {"ID", "PASSWORD"}.issubset(set(request_url.query))

    @pytest.mark.parametrize(
        ("status", "body"),
        [
            (HTTPStatus.UNAUTHORIZED, ""),
            (HTTPStatus.FORBIDDEN, ""),
            (HTTPStatus.OK, "INVALIDPASSWORDID|credentials rejected"),
        ],
    )
    async def test_rejects_invalid_credentials(
        self,
        aioclient_mock: AiohttpClientMocker,
        client_session: ClientSession,
        status: HTTPStatus,
        body: str,
    ) -> None:
        """Authentication responses raise a dedicated sanitized error."""
        aioclient_mock.get(UPLOAD_ENDPOINT, status=status, text=body)
        client = WeatherUndergroundClient(client_session, TEST_STATION_ID, TEST_STATION_KEY)

        with pytest.raises(WeatherUndergroundAuthenticationError) as error:
            await client.async_upload(TEST_OBSERVATION)

        self._assert_error_is_sanitized(error.value)

    async def test_distinguishes_rate_limit(
        self,
        aioclient_mock: AiohttpClientMocker,
        client_session: ClientSession,
    ) -> None:
        """HTTP 429 raises a dedicated rate-limit error."""
        aioclient_mock.get(
            UPLOAD_ENDPOINT,
            status=HTTPStatus.TOO_MANY_REQUESTS,
            text="retry later",
        )
        client = WeatherUndergroundClient(client_session, TEST_STATION_ID, TEST_STATION_KEY)

        with pytest.raises(WeatherUndergroundRateLimitError) as error:
            await client.async_upload(TEST_OBSERVATION)

        self._assert_error_is_sanitized(error.value)

    @pytest.mark.parametrize(
        "request_error",
        [
            TimeoutError(TEST_STATION_KEY),
            ClientConnectionError(TEST_STATION_KEY),
        ],
    )
    async def test_sanitizes_transport_failures(
        self,
        aioclient_mock: AiohttpClientMocker,
        client_session: ClientSession,
        request_error: Exception,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Timeout and network errors cannot expose request credentials."""
        aioclient_mock.get(UPLOAD_ENDPOINT, exc=request_error)
        client = WeatherUndergroundClient(client_session, TEST_STATION_ID, TEST_STATION_KEY)

        with (
            caplog.at_level(logging.DEBUG),
            pytest.raises(WeatherUndergroundConnectionError) as error,
        ):
            await client.async_upload(TEST_OBSERVATION)

        self._assert_error_is_sanitized(error.value)
        assert TEST_STATION_KEY not in caplog.text

    async def test_classifies_server_failure_as_connection_error(
        self,
        aioclient_mock: AiohttpClientMocker,
        client_session: ClientSession,
    ) -> None:
        """A server failure is reported as a retryable connection error."""
        aioclient_mock.get(
            UPLOAD_ENDPOINT,
            status=HTTPStatus.SERVICE_UNAVAILABLE,
            text="service unavailable",
        )
        client = WeatherUndergroundClient(client_session, TEST_STATION_ID, TEST_STATION_KEY)

        with pytest.raises(WeatherUndergroundConnectionError) as error:
            await client.async_upload(TEST_OBSERVATION)

        self._assert_error_is_sanitized(error.value)

    @pytest.mark.parametrize(
        ("status", "body"),
        [
            (HTTPStatus.OK, "unexpected"),
            (HTTPStatus.BAD_REQUEST, "bad request"),
            (HTTPStatus.OK, "x" * (MAX_RESPONSE_BYTES + 1)),
        ],
    )
    async def test_rejects_unexpected_response(
        self,
        aioclient_mock: AiohttpClientMocker,
        client_session: ClientSession,
        status: HTTPStatus,
        body: str,
    ) -> None:
        """Malformed protocol and HTTP responses raise a response error."""
        aioclient_mock.get(UPLOAD_ENDPOINT, status=status, text=body)
        client = WeatherUndergroundClient(client_session, TEST_STATION_ID, TEST_STATION_KEY)

        with pytest.raises(WeatherUndergroundResponseError) as error:
            await client.async_upload(TEST_OBSERVATION)

        assert error.value.status == status
        self._assert_error_is_sanitized(error.value)

    @pytest.mark.parametrize("observation", [{}, {"PASSWORD": "override"}])
    async def test_rejects_invalid_observation(
        self,
        client_session: ClientSession,
        observation: dict[str, str],
    ) -> None:
        """Empty observations and reserved protocol fields are rejected locally."""
        client = WeatherUndergroundClient(client_session, TEST_STATION_ID, TEST_STATION_KEY)

        with pytest.raises(ValueError):
            await client.async_upload(observation)

    @staticmethod
    def _assert_error_is_sanitized(error: Exception) -> None:
        """Assert that an exception does not expose simulated credentials.

        :param error: Raised client exception.
        """
        assert TEST_STATION_KEY not in str(error)
        assert "PASSWORD" not in str(error)
        assert UPLOAD_ENDPOINT not in str(error)
