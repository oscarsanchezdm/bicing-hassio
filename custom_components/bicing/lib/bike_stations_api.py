from dataclasses import dataclass
import logging

import aiohttp # type: ignore

import json

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
    async def get_bike_stations(token):
        headers = {
            'Authorization': token,
        }
        session = aiohttp.ClientSession(headers=headers)
        response = await session.get(const.STATION_INFO_ENDPOINT)

        # fix bug petició retornada en XML
        if response.headers.get('content-type') == 'application/xml; charset=UTF-8':
            _LOGGER.error("El servidor ha retornat un contingut inesperat:" + response)
            return

        if response.headers.get('content-type') != 'application/json; charset=UTF-8':
            raise aiohttp.ContentTypeError(request_info=response.request_info,history=response.history,message=f"La resposta no és un JSON: {response.headers.get('Content-Type')}")
        json = await response.json()
        await session.close()

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
        session = aiohttp.ClientSession(headers=headers)
        response = await session.get(const.STATION_INFO_ENDPOINT)

        # fix bug petició retornada en XML
        if response.headers.get('content-type') == 'application/xml; charset=UTF-8':
            _LOGGER.error("El servidor ha retornat un contingut inesperat:" + response)
            return
        
        if response.headers.get('content-type') != 'application/json; charset=UTF-8':
            raise aiohttp.ContentTypeError(request_info=response.request_info,history=response.history,message=f"La resposta no és un JSON: {response.headers.get('Content-Type')}")
            
        json = await response.json()
        await session.close()

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
        session = aiohttp.ClientSession(headers=headers)
        response = await session.get(const.STATION_STATUS_ENDPOINT)
      
        # fix bug petició retornada en XML
        if response.headers.get('content-type') == 'application/xml; charset=UTF-8':
            _LOGGER.error("El servidor ha retornat un contingut inesperat:" + response)
            return

        if response.headers.get('content-type') != 'application/json; charset=UTF-8':
            raise aiohttp.ContentTypeError(request_info=response.request_info,history=response.history,message=f"La resposta no és un JSON: {response.headers.get('Content-Type')}")

        json = await response.json()
        await session.close()

        station_status_list = []

        for station in json['data']['stations']:
            if str(station['station_id']) in map(str, station_ids):
                station_status = StationStatus(
                    id=station['station_id'],
                    bikes_available=station['num_bikes_available_types']['mechanical'],
                    ebikes_available=station['num_bikes_available_types']['ebike'],
                    docks_available=station['num_docks_available']
                )
                station_status_list.append(station_status)  # Afegir el diccionari a la llista

        return station_status_list  # Tornar la llista de diccionaris