"""Repair flows for Bicing Open Data bot challenges."""

from __future__ import annotations

import voluptuous as vol  # type: ignore

from homeassistant.components.repairs import RepairsFlow
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import issue_registry as ir

from .const import CHALLENGE_URL, DOMAIN, ISSUE_BOT_CHALLENGE, TOKEN
from .lib.bike_stations_api import (
    BikeStationApi,
    BikeStationAuthError,
    BikeStationChallengeError,
    BikeStationTemporaryError,
)


def challenge_issue_id(entry_id: str) -> str:
    """Return a stable issue id for a config entry."""
    return f"{ISSUE_BOT_CHALLENGE}_{entry_id}"


@callback
def async_create_challenge_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Create (or refresh) a fixable repair issue for a bot challenge."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        challenge_issue_id(entry_id),
        is_fixable=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_BOT_CHALLENGE,
        translation_placeholders={"challenge_url": CHALLENGE_URL},
        data={"entry_id": entry_id},
    )


@callback
def async_delete_challenge_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Delete the bot-challenge repair issue if it exists."""
    ir.async_delete_issue(hass, DOMAIN, challenge_issue_id(entry_id))


class BotChallengeRepairFlow(RepairsFlow):
    """Guide the user through solving the Open Data BCN bot challenge."""

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the first step of a fix flow."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Ask the user to solve the challenge, then retry the API."""
        errors: dict[str, str] = {}

        if user_input is not None:
            entry = self._async_config_entry()
            if entry is None:
                return self.async_abort(reason="entry_not_found")

            token = entry.options.get(TOKEN, entry.data[TOKEN])
            try:
                await BikeStationApi.get_bike_stations(token)
            except BikeStationChallengeError:
                errors["base"] = "challenge_still_blocked"
            except BikeStationTemporaryError:
                errors["base"] = "temporary_error"
            except BikeStationAuthError:
                errors["base"] = "auth_failed"
            else:
                domain_data = self.hass.data.get(DOMAIN, {}).get(entry.entry_id)
                coordinator = (domain_data or {}).get("coordinator")
                if coordinator is not None:
                    await coordinator.async_request_refresh()
                # CREATE_ENTRY removes the issue from the registry.
                return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={"challenge_url": CHALLENGE_URL},
        )

    def _async_config_entry(self) -> ConfigEntry | None:
        entry_id = (self.data or {}).get("entry_id")
        if not entry_id:
            return None
        return self.hass.config_entries.async_get_entry(entry_id)


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create a repair flow for the given issue."""
    return BotChallengeRepairFlow()
