"""Config flow for Weather Underground Uploader."""

from typing import Any, override

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    Selector,
    TextSelector,  # pyright: ignore[reportUnknownVariableType]
    TextSelectorConfig,
    TextSelectorType,
)

from .const import CONF_STATION_ID, CONF_STATION_KEY, DOMAIN

_STATION_ID_SCHEMA = vol.All(str, str.strip, vol.Length(min=1), str.upper)
_STATION_KEY_SELECTOR: Selector[TextSelectorConfig] = TextSelector(  # pyright: ignore[reportUnknownVariableType]
    TextSelectorConfig(type=TextSelectorType.PASSWORD)
)


class WeatherUndergroundUploaderConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Weather Underground Uploader."""

    VERSION = 1

    @staticmethod
    @callback
    @override
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Create the options flow.

        :param config_entry: Weather Underground station config entry.
        :return: Options flow handler.
        """
        return WeatherUndergroundUploaderOptionsFlow()

    @override
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle setup initiated by a user.

        :param user_input: Values submitted by the user, if any.
        :return: Current config-flow result.
        """
        if user_input is not None:
            station_id: str = user_input[CONF_STATION_ID]
            await self.async_set_unique_id(station_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(title=station_id, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STATION_ID): _STATION_ID_SCHEMA,
                    vol.Required(CONF_STATION_KEY): _STATION_KEY_SELECTOR,
                }
            ),
        )


class WeatherUndergroundUploaderOptionsFlow(OptionsFlowWithReload):
    """Provide the options-flow foundation for future station settings."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show or save station options.

        Entity mappings and upload behavior are added by later roadmap issues.

        :param user_input: Values submitted by the user, if any.
        :return: Current options-flow result.
        """
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="init", data_schema=vol.Schema({}))
