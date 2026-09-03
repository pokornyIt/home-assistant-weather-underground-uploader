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
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,  # pyright: ignore[reportUnknownVariableType]
    NumberSelectorConfig,
    NumberSelectorMode,
    Selector,
    TextSelector,  # pyright: ignore[reportUnknownVariableType]
    TextSelectorConfig,
    TextSelectorType,
)

from .api import WeatherUndergroundAuthenticationError, WeatherUndergroundClient, WeatherUndergroundError
from .const import (
    CONF_MAX_SOURCE_AGE,
    CONF_STATION_ID,
    CONF_STATION_KEY,
    CONF_UPLOAD_INTERVAL,
    DEFAULT_MAX_SOURCE_AGE_MINUTES,
    DEFAULT_UPLOAD_INTERVAL_SECONDS,
    DOMAIN,
    MAX_SOURCE_AGE_MINUTES,
    MAX_UPLOAD_INTERVAL_SECONDS,
    MIN_SOURCE_AGE_MINUTES,
    MIN_UPLOAD_INTERVAL_SECONDS,
)
from .mapping import build_observation
from .models import MAPPING_SPECS
from .selectors import WEATHER_SOURCE_ENTITY_SELECTOR

_STATION_ID_SCHEMA = vol.All(str, vol.Length(min=1))
_STATION_KEY_SELECTOR: Selector[TextSelectorConfig] = TextSelector(  # pyright: ignore[reportUnknownVariableType]
    TextSelectorConfig(type=TextSelectorType.PASSWORD)
)
_UPLOAD_INTERVAL_SELECTOR: Selector[NumberSelectorConfig] = NumberSelector(  # pyright: ignore[reportUnknownVariableType]
    NumberSelectorConfig(
        min=MIN_UPLOAD_INTERVAL_SECONDS,
        max=MAX_UPLOAD_INTERVAL_SECONDS,
        step=10,
        mode=NumberSelectorMode.BOX,
        unit_of_measurement="s",
    )
)
_MAX_SOURCE_AGE_SELECTOR: Selector[NumberSelectorConfig] = NumberSelector(  # pyright: ignore[reportUnknownVariableType]
    NumberSelectorConfig(
        min=MIN_SOURCE_AGE_MINUTES,
        max=MAX_SOURCE_AGE_MINUTES,
        step=1,
        mode=NumberSelectorMode.BOX,
        unit_of_measurement="min",
    )
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
        errors: dict[str, str] = {}
        if user_input is not None:
            station_id: str = user_input[CONF_STATION_ID].strip().upper()
            if station_id:
                user_input[CONF_STATION_ID] = station_id
                await self.async_set_unique_id(station_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=station_id, data=user_input)

            errors[CONF_STATION_ID] = "invalid_station_id"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STATION_ID): _STATION_ID_SCHEMA,
                    vol.Required(CONF_STATION_KEY): _STATION_KEY_SELECTOR,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Start reauthentication for rejected station credentials.

        :param entry_data: Existing entry data supplied by Home Assistant.
        :return: Reauthentication confirmation flow result.
        """
        del entry_data
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Collect and save a replacement Station Key.

        :param user_input: Replacement credential submitted by the user.
        :return: Updated flow result or the credential form.
        """
        if user_input is not None:
            return self.async_update_reload_and_abort(
                self._get_reauth_entry(),
                data_updates={CONF_STATION_KEY: user_input[CONF_STATION_KEY]},
            )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_STATION_KEY): _STATION_KEY_SELECTOR}),
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Change station credentials while preserving the config entry.

        :param user_input: Replacement station details submitted by the user.
        :return: Updated flow result or the credential form.
        """
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            station_id: str = user_input[CONF_STATION_ID].strip().upper()
            if not station_id:
                errors[CONF_STATION_ID] = "invalid_station_id"
            else:
                station_key: str = user_input[CONF_STATION_KEY]
                if not station_key.strip():
                    errors[CONF_STATION_KEY] = "invalid_station_key"
                else:
                    if station_id != entry.unique_id:
                        await self.async_set_unique_id(station_id)
                        self._abort_if_unique_id_configured()

                    observation = build_observation(self.hass, entry.options)
                    if observation:
                        client = WeatherUndergroundClient(
                            async_get_clientsession(self.hass),
                            station_id=station_id,
                            station_key=station_key,
                        )
                        try:
                            await client.async_upload(observation)
                        except WeatherUndergroundAuthenticationError:
                            errors["base"] = "invalid_auth"
                        except WeatherUndergroundError:
                            errors["base"] = "cannot_connect"

                if not errors:
                    return self.async_update_reload_and_abort(
                        entry,
                        unique_id=station_id,
                        title=station_id,
                        data_updates={
                            CONF_STATION_ID: station_id,
                            CONF_STATION_KEY: station_key,
                        },
                    )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_STATION_ID,
                        default=entry.data[CONF_STATION_ID],
                    ): _STATION_ID_SCHEMA,
                    vol.Required(CONF_STATION_KEY): _STATION_KEY_SELECTOR,
                }
            ),
            errors=errors,
        )


class WeatherUndergroundUploaderOptionsFlow(OptionsFlowWithReload):
    """Configure entity mappings for one station."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show or save station options.

        :param user_input: Values submitted by the user, if any.
        :return: Current options-flow result.
        """
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_UPLOAD_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_UPLOAD_INTERVAL,
                            DEFAULT_UPLOAD_INTERVAL_SECONDS,
                        ),
                    ): _UPLOAD_INTERVAL_SELECTOR,
                    vol.Required(
                        CONF_MAX_SOURCE_AGE,
                        default=self.config_entry.options.get(
                            CONF_MAX_SOURCE_AGE,
                            DEFAULT_MAX_SOURCE_AGE_MINUTES,
                        ),
                    ): _MAX_SOURCE_AGE_SELECTOR,
                    **{
                        vol.Optional(
                            spec.option_key,
                            description={"suggested_value": self.config_entry.options.get(spec.option_key)},
                        ): WEATHER_SOURCE_ENTITY_SELECTOR
                        for spec in MAPPING_SPECS
                    },
                }
            ),
        )
