"""Home Assistant Repairs support for persistent mapping problems."""

from collections.abc import Mapping
from typing import Any, Protocol

import voluptuous as vol
from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow, RepairsFlowResult
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .models import MAPPING_SPECS, MappingProblemType
from .selectors import WEATHER_SOURCE_ENTITY_SELECTOR

_MAPPING_ISSUE_PREFIX = "mapping_problem"
_MAPPING_KEYS = frozenset(spec.option_key for spec in MAPPING_SPECS)


class _MappingProblem(Protocol):
    """Minimum mapping problem data needed by Repairs."""

    @property
    def entity_id(self) -> str:
        """Return the configured entity ID."""
        ...

    @property
    def problem_type(self) -> MappingProblemType:
        """Return the classified validation problem."""
        ...

    @property
    def persistent(self) -> bool:
        """Return whether the problem is actionable."""
        ...


def mapping_issue_id(entry_id: str, mapping_key: str) -> str:
    """Return the stable issue ID for one station mapping.

    :param entry_id: Home Assistant config-entry ID.
    :param mapping_key: Mapping option key.
    :return: Stable Repairs issue ID.
    """
    return f"{_MAPPING_ISSUE_PREFIX}_{entry_id}_{mapping_key}"


@callback
def async_sync_mapping_issues(
    hass: HomeAssistant,
    entry: ConfigEntry[Any],
    problems: Mapping[str, _MappingProblem],
) -> None:
    """Create persistent mapping issues and remove recovered ones.

    :param hass: Home Assistant instance.
    :param entry: Station config entry.
    :param problems: Current mapping problems keyed by mapping option.
    """
    registry = ir.async_get(hass)
    for mapping_key in _MAPPING_KEYS:
        issue_id = mapping_issue_id(entry.entry_id, mapping_key)
        current = problems.get(mapping_key)
        existing = registry.async_get_issue(DOMAIN, issue_id)

        if current is None:
            ir.async_delete_issue(hass, DOMAIN, issue_id)
            continue

        issue_data: dict[str, str | int | float | None] = {
            "entry_id": entry.entry_id,
            "mapping_key": mapping_key,
            "entity_id": current.entity_id,
            "problem_type": current.problem_type.value,
        }
        if not current.persistent:
            if existing is not None and existing.data != issue_data:
                ir.async_delete_issue(hass, DOMAIN, issue_id)
            continue

        ir.async_create_issue(
            hass=hass,
            domain=DOMAIN,
            issue_id=issue_id,
            data=issue_data,
            is_fixable=True,
            is_persistent=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="mapping_problem",
            translation_placeholders={
                "entity_id": current.entity_id,
                "mapping": mapping_key,
                "station": entry.title,
            },
        )


class MappingRepairFlow(RepairsFlow):
    """Replace or remove one persistently unusable mapping."""

    def __init__(self, entry: ConfigEntry[Any], mapping_key: str, entity_id: str) -> None:
        """Initialize a mapping repair flow.

        :param entry: Station config entry being repaired.
        :param mapping_key: Mapping option key being repaired.
        :param entity_id: Currently configured entity ID.
        """
        super().__init__()
        self._entry = entry
        self._mapping_key = mapping_key
        self._entity_id = entity_id

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> RepairsFlowResult:
        """Start the mapping repair flow.

        :param user_input: Ignored initial flow input.
        :return: Mapping repair step result.
        """
        return await self.async_step_mapping()

    async def async_step_mapping(self, user_input: dict[str, Any] | None = None) -> RepairsFlowResult:
        """Replace the affected source entity or remove its mapping.

        :param user_input: Replacement entity submitted by the user.
        :return: Updated flow result or the repair form.
        """
        if user_input is not None:
            options = dict(self._entry.options)
            replacement = user_input.get(CONF_ENTITY_ID)
            if isinstance(replacement, str) and replacement:
                options[self._mapping_key] = replacement
            else:
                options.pop(self._mapping_key, None)

            self.hass.config_entries.async_update_entry(self._entry, options=options)
            await self.hass.config_entries.async_reload(self._entry.entry_id)
            return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="mapping",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ENTITY_ID,
                        description={"suggested_value": self._entity_id},
                    ): WEATHER_SOURCE_ENTITY_SELECTOR,
                }
            ),
            description_placeholders={
                "entity_id": self._entity_id,
                "mapping": self._mapping_key,
                "station": self._entry.title,
            },
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create a fix flow for a persistent mapping issue.

    :param hass: Home Assistant instance.
    :param issue_id: Repairs issue ID.
    :param data: Issue data, if available.
    :return: Appropriate Repairs flow.
    """
    if (
        issue_id.startswith(f"{_MAPPING_ISSUE_PREFIX}_")
        and data is not None
        and isinstance(entry_id := data.get("entry_id"), str)
        and isinstance(mapping_key := data.get("mapping_key"), str)
        and mapping_key in _MAPPING_KEYS
        and isinstance(entity_id := data.get("entity_id"), str)
        and (entry := hass.config_entries.async_get_entry(entry_id)) is not None
        and entry.domain == DOMAIN
    ):
        return MappingRepairFlow(entry, mapping_key, entity_id)

    return ConfirmRepairFlow()
