import logging
from datetime import datetime, timedelta, timezone
from typing import Mapping, Any

import json
from .const import (
    CONF_STATION_IDS,
    UPDATE_INTERVAL,
    STALE_DATA_TTL_HOURS,
    TOKEN,
    #CONF_SHOW_IN_MAP
)

import aiohttp

from .lib.bike_stations_api import BikeStationApi, StationStatus

from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity, UpdateFailed

from homeassistant.components.sensor import (
    SensorEntityDescription, SensorEntity
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

_STALE_DATA_TTL = timedelta(hours=STALE_DATA_TTL_HOURS)


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
            _LOGGER.error("Error connectant-se amb l'API del Bicing. El token podria ser invàlid (Content-Type inesperat).")
            return

        except aiohttp.ServerConnectionError as exc:
            _LOGGER.error("Error connectant-se amb l'API del Bicing. Error de servidor")
            return
        
        except aiohttp.ClientConnectionError as exc:
            _LOGGER.error("Error connectant-se amb l'API del Bicing. Error del client (certificats,etc.)")
            return
        
        sensor = BicingStationSensor(names[-1], names[-1], station, coordinator)
        async_add_entities([sensor])

class BicingStationCoordinator(DataUpdateCoordinator):

    def __init__(self, hass: HomeAssistant, stations, token):
        super().__init__(hass=hass, logger=_LOGGER, name="Bicing Station", update_interval=timedelta(minutes=UPDATE_INTERVAL))
        self._token = token
        self._stations = stations
        self._last_success_time: datetime | None = None

    async def async_config_entry_first_refresh(self) -> None:
        #self._latitude = gas_station.latitude
        #self._longitude = gas_station.longitude
        await super().async_config_entry_first_refresh()

    def _cached_data_if_fresh(self, exc: Exception):
        """Return last known data while failures are within the stale TTL."""
        if self.data is None or self._last_success_time is None:
            return None

        age = datetime.now(timezone.utc) - self._last_success_time
        if age >= _STALE_DATA_TTL:
            return None

        _LOGGER.warning(
            "Error temporal obtenint dades del Bicing (%s). "
            "Es manté l'últim estat conegut (fa %s; límit %s).",
            exc,
            age,
            _STALE_DATA_TTL,
        )
        return self.data

    async def _async_update_data(self):
        try:
            status = await BikeStationApi.get_stations_status(self._token, self._stations)

        except (
            aiohttp.ContentTypeError,
            aiohttp.ServerConnectionError,
            aiohttp.ClientConnectionError,
            aiohttp.ServerTimeoutError,
            TimeoutError,
        ) as exc:
            cached = self._cached_data_if_fresh(exc)
            if cached is not None:
                return cached

            _LOGGER.error("Error connectant-se amb l'API del Bicing: %s", exc)

            if isinstance(exc, aiohttp.ContentTypeError):
                raise UpdateFailed(
                    "Error temporal connectant-se amb l'API del Bicing (Content-Type inesperat)."
                ) from exc
            if isinstance(exc, aiohttp.ClientConnectionError) and not isinstance(
                exc, aiohttp.ServerConnectionError
            ):
                raise UpdateFailed(
                    "Error del client connectant-se amb l'API del Bicing."
                ) from exc
            if isinstance(exc, (aiohttp.ServerTimeoutError, TimeoutError)):
                raise UpdateFailed("Timeout connectant-se amb l'API del Bicing.") from exc
            raise UpdateFailed("Error temporal connectant-se amb l'API del Bicing.") from exc

        self._last_success_time = datetime.now(timezone.utc)
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

    @property
    def available(self) -> bool:
        """Prefer unknown over unavailable after prolonged API failures."""
        # Transient failures reuse cached coordinator data (last_update_success stays
        # True). After the stale TTL, UpdateFailed is raised and we clear the state
        # to unknown while remaining available.
        return True

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if not self.coordinator.last_update_success:
            # Prolonged failure past the stale TTL: show unknown instead of a stale value.
            self._state = None
            self._attrs = {}
            self.async_write_ha_state()
            return

        data = self.coordinator.data
        if data is None:
            _LOGGER.debug("No coordinator data available for station %s", self.id)
            return
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
