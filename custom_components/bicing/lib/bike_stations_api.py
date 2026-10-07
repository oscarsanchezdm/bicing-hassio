from __future__ import annotations

from dataclasses import dataclass
import asyncio
import json
import logging

import aiohttp  # type: ignore

from .. import const

_LOGGER = logging.getLogger(__name__)


class BikeStationApiError(Exception):
    """Base error for the Bicing Open Data API."""


class BikeStationAuthError(BikeStationApiError):
    """Raised when the API rejects the access token (HTTP 401/403)."""


class BikeStationChallengeError(BikeStationApiError):
    """Raised when the portal blocks the request with a bot/captcha challenge."""


class BikeStationTemporaryError(BikeStationApiError):
    """Raised for transient upstream/network/response errors."""


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
    def _looks_like_challenge(url: str, content_type: str | None, body_text: str) -> bool:
        lowered_url = url.lower()
        lowered_body = body_text.lower()
        if "/challenge" in lowered_url:
            return True
        if "bot detection" in lowered_body or "hcaptcha" in lowered_body:
            return True
        if content_type and "text/html" in content_type.lower() and "challenge" in lowered_body:
            return True
        return False

    @staticmethod
    async def _fetch_json(session: aiohttp.ClientSession, url: str) -> dict:
        """Fetch a JSON resource, classifying auth vs challenge vs temporary errors."""
        try:
            async with session.get(url, allow_redirects=True) as response:
                content_type = response.headers.get("Content-Type")
                final_url = str(response.url)
                body = await response.read()
                body_text = body.decode("utf-8", errors="replace")

                if response.status in (401, 403):
                    raise BikeStationAuthError(
                        f"Token rebutjat pel servidor (HTTP {response.status})."
                    )

                if BikeStationApi._looks_like_challenge(final_url, content_type, body_text):
                    _LOGGER.warning(
                        "Open Data BCN ha bloquejat la petició amb un challenge anti-bot "
                        "(status=%s, url=%s, content-type=%s).",
                        response.status,
                        final_url,
                        content_type,
                    )
                    raise BikeStationChallengeError(
                        "El portal Open Data BCN ha bloquejat la petició amb un challenge anti-bot."
                    )

                if response.status >= 400:
                    raise BikeStationTemporaryError(
                        f"Error temporal de l'API del Bicing (HTTP {response.status})."
                    )

                if not BikeStationApi._is_json_content_type(content_type):
                    _LOGGER.error(
                        "El servidor ha retornat un contingut inesperat. Status=%s, Content-Type=%s",
                        response.status,
                        content_type,
                    )
                    raise BikeStationTemporaryError(
                        f"La resposta no és un JSON: {content_type}"
                    )

                try:
                    return json.loads(body_text)
                except json.JSONDecodeError as exc:
                    raise BikeStationTemporaryError(
                        "La resposta JSON de l'API del Bicing no és vàlida."
                    ) from exc
        except (BikeStationAuthError, BikeStationChallengeError, BikeStationTemporaryError):
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError, TimeoutError) as exc:
            raise BikeStationTemporaryError(
                f"Error de connexió amb l'API del Bicing: {exc}"
            ) from exc

    @staticmethod
    async def get_bike_stations(token: str) -> list[StationInfo]:
        headers = {"Authorization": token}
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            payload = await BikeStationApi._fetch_json(session, const.STATION_INFO_ENDPOINT)

        stations = []
        for station_data in payload["data"]["stations"]:
            stations.append(
                StationInfo(
                    id=station_data["station_id"],
                    name=station_data["name"],
                )
            )
        return stations

    @staticmethod
    async def get_station_name(token: str, station_id) -> str:
        headers = {"Authorization": token}
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            payload = await BikeStationApi._fetch_json(session, const.STATION_INFO_ENDPOINT)

        for station in payload["data"]["stations"]:
            if str(station["station_id"]) == str(station_id):
                return station["name"]

        return f"Estació {station_id}"

    @staticmethod
    async def get_stations_status(token: str, station_ids) -> list[StationStatus]:
        headers = {"Authorization": token}
        max_attempts = 2
        last_exc: Exception | None = None

        for attempt in range(max_attempts):
            try:
                timeout = aiohttp.ClientTimeout(total=15)
                async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                    payload = await BikeStationApi._fetch_json(
                        session, const.STATION_STATUS_ENDPOINT
                    )

                station_status_list = []
                for station in payload["data"]["stations"]:
                    if str(station["station_id"]) in map(str, station_ids):
                        station_status_list.append(
                            StationStatus(
                                id=station["station_id"],
                                bikes_available=station["num_bikes_available_types"][
                                    "mechanical"
                                ],
                                ebikes_available=station["num_bikes_available_types"]["ebike"],
                                docks_available=station["num_docks_available"],
                            )
                        )
                return station_status_list
            except BikeStationChallengeError:
                raise
            except BikeStationAuthError:
                raise
            except BikeStationTemporaryError as exc:
                last_exc = exc
                if attempt == max_attempts - 1:
                    raise
                _LOGGER.warning(
                    "Error temporal obtenint l'estat de les estacions (%s). Reintentant una vegada...",
                    exc,
                )
                await asyncio.sleep(1)

        assert last_exc is not None
        raise last_exc
