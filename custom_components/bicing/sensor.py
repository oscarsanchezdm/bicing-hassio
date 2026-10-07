import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CONF_STATION_IDS,
    DOMAIN,
    STALE_DATA_TTL_HOURS,
    TOKEN,
    UPDATE_INTERVAL,
)
from .lib.bike_stations_api import (
    BikeStationApi,
    BikeStationAuthError,
    BikeStationChallengeError,
    BikeStationTemporaryError,
)
from .repairs import async_create_challenge_issue, async_delete_challenge_issue

_LOGGER = logging.getLogger(__name__)

_STALE_DATA_TTL = timedelta(hours=STALE_DATA_TTL_HOURS)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    stations = entry.options.get(CONF_STATION_IDS, entry.data[CONF_STATION_IDS])
    token = entry.options.get(TOKEN, entry.data[TOKEN])

    _LOGGER.info("Creating Bicing stations %s", stations)

    coordinator = BicingStationCoordinator(hass, entry, stations, token)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})
    hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator

    await coordinator.async_config_entry_first_refresh()

    for station in stations:
        try:
            name = await BikeStationApi.get_station_name(token, station)
        except BikeStationAuthError:
            _LOGGER.error(
                "Error obtenint el nom de l'estació %s: token rebutjat.", station
            )
            return
        except BikeStationChallengeError:
            _LOGGER.error(
                "Error obtenint el nom de l'estació %s: challenge anti-bot.", station
            )
            async_create_challenge_issue(hass, entry.entry_id)
            name = f"Estació {station}"
        except BikeStationTemporaryError:
            _LOGGER.error(
                "Error temporal obtenint el nom de l'estació %s.", station
            )
            name = f"Estació {station}"

        async_add_entities([BicingStationSensor(name, name, station, coordinator)])


class BicingStationCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, stations, token):
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name="Bicing Station",
            update_interval=timedelta(minutes=UPDATE_INTERVAL),
        )
        self._entry = entry
        self._token = token
        self._stations = stations
        self._last_success_time: datetime | None = None

    async def async_config_entry_first_refresh(self) -> None:
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
            status = await BikeStationApi.get_stations_status(
                self._token, self._stations
            )
        except BikeStationAuthError as exc:
            _LOGGER.error("Token de l'API del Bicing rebutjat durant l'actualització.")
            raise ConfigEntryAuthFailed(
                "Token de l'API del Bicing rebutjat."
            ) from exc
        except (BikeStationChallengeError, BikeStationTemporaryError) as exc:
            if isinstance(exc, BikeStationChallengeError):
                async_create_challenge_issue(self.hass, self._entry.entry_id)

            cached = self._cached_data_if_fresh(exc)
            if cached is not None:
                return cached

            _LOGGER.error("Error connectant-se amb l'API del Bicing: %s", exc)
            raise UpdateFailed(str(exc)) from exc

        self._last_success_time = datetime.now(timezone.utc)
        async_delete_challenge_issue(self.hass, self._entry.entry_id)
        _LOGGER.debug("Bulk update=%s", status)
        return status


class BicingStationSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, name: str, unique_id: str, id: str, coordinator):
        super().__init__(coordinator=coordinator)
        self.id = id
        self._state = None
        self._attrs: dict[str, Any] = {}
        self._attr_name = name
        self._attr_unique_id = unique_id
        self.entity_description = SensorEntityDescription(
            key=name, icon="mdi:bicycle", state_class="measurement"
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @property
    def available(self) -> bool:
        """Prefer unknown over unavailable after prolonged API failures."""
        return True

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if not self.coordinator.last_update_success:
            self._state = None
            self._attrs = {}
            self.async_write_ha_state()
            return

        data = self.coordinator.data
        if data is None:
            _LOGGER.debug("No coordinator data available for station %s", self.id)
            return
        for d in data:
            if str(d.id) == str(self.id):
                self._state = d.bikes_available + d.ebikes_available
                self._attrs["Bicicletes elèctriques disponibles"] = d.ebikes_available
                self._attrs["Bicicletes mecàniques disponibles"] = d.bikes_available
                self._attrs["Ancoratges disponibles"] = d.docks_available
                break

        self.async_write_ha_state()

    @property
    def native_value(self) -> StateType:
        return self._state

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        return self._attrs
