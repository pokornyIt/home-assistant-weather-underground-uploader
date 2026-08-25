"""Shared Home Assistant selectors for weather source entities."""

from homeassistant.helpers.selector import (
    EntitySelector,  # pyright: ignore[reportUnknownVariableType]
    EntitySelectorConfig,
    Selector,
)

WEATHER_SOURCE_ENTITY_SELECTOR: Selector[EntitySelectorConfig] = EntitySelector(  # pyright: ignore[reportUnknownVariableType]
    EntitySelectorConfig(filter=[{"domain": ["sensor", "input_number"]}])
)
