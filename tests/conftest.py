"""Shared fixtures for Weather Underground Uploader tests."""

from collections.abc import Generator

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    """Enable loading custom integrations in every test.

    :param enable_custom_integrations: Home Assistant custom-integration fixture.
    :return: Fixture lifecycle generator.
    """
    yield
