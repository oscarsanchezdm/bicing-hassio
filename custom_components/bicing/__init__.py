"""Estat del Bicing"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import CHALLENGE_URL, DOMAIN, TOKEN
from .lib.bike_stations_api import (
    BikeStationApi,
    BikeStationAuthError,
    BikeStationChallengeError,
    BikeStationTemporaryError,
)
from .repairs import async_create_challenge_issue, async_delete_challenge_issue

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Bicing from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})

    token = entry.options.get(TOKEN, entry.data[TOKEN])

    try:
        await BikeStationApi.get_bike_stations(token)
    except BikeStationAuthError as exc:
        _LOGGER.error("Token de l'API del Bicing rebutjat: %s", exc)
        raise ConfigEntryAuthFailed(
            "Error connectant-se amb l'API del Bicing. El token és invàlid."
        ) from exc
    except BikeStationChallengeError as exc:
        _LOGGER.error(
            "Open Data BCN ha bloquejat l'accés amb un challenge anti-bot. "
            "Obriu %s des d'un dispositiu amb la mateixa IP pública que Home Assistant.",
            CHALLENGE_URL,
        )
        async_create_challenge_issue(hass, entry.entry_id)
        raise ConfigEntryNotReady(
            "Open Data BCN ha bloquejat la petició amb un challenge anti-bot. "
            f"Obriu {CHALLENGE_URL} des de la mateixa IP pública que Home Assistant "
            "i torneu-ho a provar. Si continua, reinicieu el router per canviar d'IP."
        ) from exc
    except BikeStationTemporaryError as exc:
        _LOGGER.error("Error temporal connectant-se amb l'API del Bicing: %s", exc)
        raise ConfigEntryNotReady(
            "Error temporal connectant-se amb l'API del Bicing."
        ) from exc

    async_delete_challenge_issue(hass, entry.entry_id)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_options))
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(config_entry.entry_id, None)
    return unload_ok


async def _async_update_options(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Handle options update."""
    hass.config_entries.async_update_entry(
        config_entry, data={**config_entry.data, **config_entry.options}
    )
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entry versions."""
    version = config_entry.version

    if version == 1:
        data = {
            **config_entry.data,
        }

        hass.config_entries.async_update_entry(config_entry, data=data)
        config_entry.version = 2

    return True
