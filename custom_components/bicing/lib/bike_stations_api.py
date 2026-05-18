from dataclasses import dataclass
import logging

import aiohttp # type: ignore

from .. import const

_LOGGER = logging.getLogger(__name__)

@dataclass
class StationInfo:
    id: int
    name: str

@dataclass
class StationStatus:
    id: str
    bikes_available: int
    ebikes_available: int
    docks_available: int

class BikeStationApi:
    @staticmethod
    def _is_json_content_type(content_type: str | None) -> bool:
        if not content_type:
            return False
        return content_type.lower().split(";", 1)[0].strip() == "application/json"

    @staticmethod
    async def get_bike_stations(token):
        headers = {
            'Authorization': token,
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(const.STATION_INFO_ENDPOINT) as response:
                content_type = response.headers.get("Content-Type")
                if not BikeStationApi._is_json_content_type(content_type):
                    _LOGGER.error("El servidor ha retornat un contingut inesperat. Status=%s, Content-Type=%s", response.status, content_type)
                    raise aiohttp.ContentTypeError(request_info=response.request_info, history=response.history, message=f"La resposta no és un JSON: {content_type}")
                json = await response.json()

        stations = []
        for station_data in json['data']['stations']:
            station = StationInfo(
                id=station_data['station_id'],
                name=station_data['name']
            )
            stations.append(station)
        return stations
        

    @staticmethod
    async def get_station_name(token, station_id):
        headers = {
            'Authorization': token,
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(const.STATION_INFO_ENDPOINT) as response:
                content_type = response.headers.get("Content-Type")
                if not BikeStationApi._is_json_content_type(content_type):
                    _LOGGER.error("El servidor ha retornat un contingut inesperat. Status=%s, Content-Type=%s", response.status, content_type)
                    raise aiohttp.ContentTypeError(request_info=response.request_info, history=response.history, message=f"La resposta no és un JSON: {content_type}")
                json = await response.json()

        bike_station = None
        for station in json['data']['stations']:
            if str(station['station_id']) == str(station_id):
                bike_station = station
                break

        if bike_station is None:
            return f"Estació {station_id}"
        
        return bike_station['name']
 
    @staticmethod
    async def get_stations_status(token, station_ids):
        headers = {
            'Authorization': token,
        }
        json_response = None
        for attempt in range(1, 3):
            try:
                timeout = aiohttp.ClientTimeout(total=15)
                async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                    async with session.get(const.STATION_STATUS_ENDPOINT) as response:
                        content_type = response.headers.get("Content-Type")
                        if not BikeStationApi._is_json_content_type(content_type):
                            _LOGGER.error("El servidor ha retornat un contingut inesperat. Status=%s, Content-Type=%s", response.status, content_type)
                            raise aiohttp.ContentTypeError(request_info=response.request_info, history=response.history, message=f"La resposta no és un JSON: {content_type}")
                        json_response = await response.json()
                        break
            except (aiohttp.ServerConnectionError, aiohttp.ClientConnectionError, aiohttp.ServerTimeoutError, TimeoutError):
                if attempt == 1:
                    _LOGGER.warning("Error temporal obtenint l'estat de les estacions. Reintentant una vegada...")
                    continue
                raise

        station_status_list = []

        for station in json_response['data']['stations']:
            if str(station['station_id']) in map(str, station_ids):
                station_status = StationStatus(
                    id=station['station_id'],
                    bikes_available=station['num_bikes_available_types']['mechanical'],
                    ebikes_available=station['num_bikes_available_types']['ebike'],
                    docks_available=station['num_docks_available']
                )
                station_status_list.append(station_status)  # Afegir el diccionari a la llista

        return station_status_list  # Tornar la llista de diccionaris
