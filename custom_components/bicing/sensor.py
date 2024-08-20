import logging
from datetime import timedelta
from typing import Mapping, Any

import json
from .const import (
    CONF_STATION_IDS,
    UPDATE_INTERVAL,
    TOKEN,
    #CONF_SHOW_IN_MAP
)

import aiohttp

from .lib.bike_stations_api import BikeStationApi, StationStatus

from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.components.sensor import (
    SensorEntityDescription, SensorEntity
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    stations = token = entry.options.get(CONF_STATION_IDS, entry.data[CONF_STATION_IDS])
    token = entry.options.get(TOKEN, entry.data[TOKEN])

    _LOGGER.info(f"Creating Bicing stations {stations} ")

    coordinator = BicingStationCoordinator(hass, stations, token)
    await coordinator.async_config_entry_first_refresh()

    names = []

    for i, station in enumerate(stations):
        try:
            names.append(await BikeStationApi.get_station_name(token, station))

        except aiohttp.ContentTypeError as exc: #token error
            _LOGGER.error("Error connectant-se amb l'API del Bicing. El token podria ser invàlid.")
            return

        except aiohttp.ServerConnectionError as exc:
            _LOGGER.error("Error connectant-se amb l'API del Bicing.")
            return
        
        sensor = BicingStationSensor(names[-1], names[-1], station, coordinator)
        async_add_entities([sensor])

class BicingStationCoordinator(DataUpdateCoordinator):

    def __init__(self, hass: HomeAssistant, stations, token):
        super().__init__(hass=hass, logger=_LOGGER, name="Bicing Station", update_interval=timedelta(minutes=UPDATE_INTERVAL))
        self._token = token
        self._stations = stations

    async def async_config_entry_first_refresh(self) -> None:
        #self._latitude = gas_station.latitude
        #self._longitude = gas_station.longitude
        await super().async_config_entry_first_refresh()

    async def _async_update_data(self):
        try:
            status = await BikeStationApi.get_stations_status(self._token, self._stations)
        except aiohttp.ContentTypeError as exc: #token error
            raise ConfigEntryAuthFailed("Error connectant-se amb l'API del Bicing. El token podria ser invàlid.") from exc
        except aiohttp.ServerConnectionError as exc:
            _LOGGER.error("Error connectant-se amb l'API del Bicing.")
            return
        
        _LOGGER.debug(f"Bulk update={status}")
        return status


class BicingStationSensor(CoordinatorEntity, SensorEntity):

    def __init__(self, name: str, unique_id: str, id:str, coordinator):
        super().__init__(coordinator=coordinator)
        self.id = id
        self._state = None
        self._attrs: dict[str, Any] = {}
        self._attr_name = name
        self._attr_unique_id = unique_id
        #self._show_in_map = show_in_map
        self.entity_description = SensorEntityDescription(
            key=name,
            icon="mdi:bicycle",
            state_class="measurement"
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        for d in data:
            if str(d.id)==str(self.id):
                self._state = (d.bikes_available + d.ebikes_available)
                self._attrs['Bicicletes elèctriques disponibles'] = d.ebikes_available
                self._attrs['Bicicletes mecàniques disponibles'] = d.bikes_available
                self._attrs['Ancoratges disponibles'] = d.docks_available
                break

        #if self._show_in_map:
        #    self._attrs['latitude'] = data['latitude']
        #    self._attrs['longitude'] = data['longitude']

        self.async_write_ha_state()

    @property
    def native_value(self) -> StateType:
        return self._state

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        return self._attrs
