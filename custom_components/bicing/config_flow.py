from __future__ import annotations

import logging
from typing import Any

import json

import aiohttp

import voluptuous as vol # type: ignore
from homeassistant.core import callback # type: ignore

from homeassistant import config_entries # type: ignore
from homeassistant.data_entry_flow import FlowResult # type: ignore
from homeassistant.helpers.selector import ( # type: ignore
    SelectSelector,
    SelectSelectorConfig,
    SelectOptionDict,
    SelectSelectorMode,
    TextSelector
)

from homeassistant.helpers.entity_registry import async_entries_for_config_entry
from homeassistant.const import STATE_UNAVAILABLE

from homeassistant.helpers import config_validation as cv # type: ignore

from .const import *
from .lib.bike_stations_api import BikeStationApi

_LOGGER = logging.getLogger(__name__)

class PlaceholderHub:
    def __init__(self, token: str) -> None:
        """Initialize."""
        self.token = token

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    token: str
    station_ids: []
    config_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            self.token = user_input[TOKEN]
            return await self.async_step_station()

        schema = vol.Schema({
            vol.Required(TOKEN): TextSelector()
        })
        return self.async_show_form(step_id="user", data_schema=schema, last_step=False)

    async def async_step_station(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self.station_ids = []
            for station_input in user_input[CONF_STATION_IDS]:
                self.station_ids.append(station_input)
            
            await self.async_set_unique_id("Bicing")
            return self.async_create_entry(title="Bicing", data={
                TOKEN: self.token,
                CONF_STATION_IDS: self.station_ids,
            })
        
        try:
            stations = await BikeStationApi.get_bike_stations(self.token)
        except aiohttp.ContentTypeError as exc: #token error
            return self.async_abort(reason="token_error")        
        except aiohttp.ServerConnectionError as exc:
            return self.async_abort(reason="status_error")
                
        options = list(map(lambda p: SelectOptionDict(label=str(p.id) + " - " + p.name, value=str(p.id)), stations))

        schema = vol.Schema({
            vol.Required(CONF_STATION_IDS): SelectSelector(
                SelectSelectorConfig(options=options, multiple=True, mode=SelectSelectorMode.DROPDOWN)
            )
        })
        return self.async_show_form(step_id="station", data_schema=schema)
    
    async def async_step_token(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            self.token = user_input[TOKEN]
            return await self.async_update_token(data={
                TOKEN: user_input[TOKEN],
                CONF_STATION_IDS: self.config_entry.data[CONF_STATION_IDS]
            })

        schema = vol.Schema({
            vol.Required(TOKEN): TextSelector()
        })

        return self.async_show_form(step_id="token", data_schema = schema)

    async def async_step_reauth(self, user_input=None):
        """Perform reauth upon an API authentication error."""
        self.config_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Dialog that informs the user that reauth is required."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=vol.Schema({}),
            )
        return await self.async_step_token()

    async def async_update_token(self, data: dict) -> dict:
        """Create an oauth config entry or update existing entry for reauth."""
        if self.config_entry:
            return self.async_update_reload_and_abort(
                self.config_entry,
                data=data,
            )
        return await super().async_update_token(data)
    
    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        self.config_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
            
        estacions_actuals = self.config_entry.data[CONF_STATION_IDS]
        token_actual = self.config_entry.data[TOKEN]
        
        if user_input is not None:
            station_ids = []

            for station_input in user_input[CONF_STATION_IDS]:
                station_ids.append(station_input)
            
            self.station_ids = station_ids

            self.hass.config_entries.async_update_entry(
                self.config_entry, data={TOKEN: token_actual, CONF_STATION_IDS: station_ids}, options=self.config_entry.options
            )
            
            # buscar entitats antigues
            entity_registry = self.hass.helpers.entity_registry.async_get()
            entity_entries = async_entries_for_config_entry(entity_registry, self.config_entry.entry_id)

            entities_to_remove = []
            _LOGGER.error(entity_entries)

            for e in entity_entries:
                entity = self.hass.states.get(e.entity_id)
                if entity.state != STATE_UNAVAILABLE:
                    continue
                entities_to_remove.append(e)

            for e in entities_to_remove:
                entity_registry.async_remove(e.entity_id)

            return self.async_abort(reason="data_updated") 
        
        try:
            stations = await BikeStationApi.get_bike_stations(token_actual)
        except aiohttp.ContentTypeError as exc: #token error
            return self.async_abort(reason="token_error")      
        except aiohttp.ServerConnectionError as exc:
            return self.async_abort(reason="status_error")
        
        options = list(map(lambda p: SelectOptionDict(label=str(p.id) + " - " + p.name, value=str(p.id)), stations))

        schema = vol.Schema({
            vol.Required(CONF_STATION_IDS,default=list(estacions_actuals)): SelectSelector(
                SelectSelectorConfig(options=options, multiple=True, mode=SelectSelectorMode.DROPDOWN)
            )
        })

        return self.async_show_form(step_id="reconfigure", data_schema=schema)

