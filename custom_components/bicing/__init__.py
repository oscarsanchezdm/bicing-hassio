"""Estat del Bicing"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

import aiohttp
from homeassistant.exceptions import ConfigEntryAuthFailed

from .lib.bike_stations_api import BikeStationApi

from .const import DOMAIN, TOKEN

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    #provar que el token sigui bo
    try:
        stations = await BikeStationApi.get_bike_stations(entry.options.get(TOKEN, entry.data[TOKEN]))
    except aiohttp.ContentTypeError as exc: #token error
        raise ConfigEntryAuthFailed("Error connectant-se amb l'API del Bicing. El token podria ser invàlid.") from exc     
    except aiohttp.ServerConnectionError as exc:
        return False
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_options))
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)


async def _async_update_options(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Handle options update."""
    # update entry replacing data with new options
    hass.config_entries.async_update_entry(config_entry, data={**config_entry.data, **config_entry.options})
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, config_entry):
    version = config_entry.version

    if version == 1:
        data = {
            **config_entry.data,
        }

        hass.config_entries.async_update_entry(config_entry, data=data)
        config_entry.version = 2

    return True
