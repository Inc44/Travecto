from __future__ import annotations
from typing import List, Tuple
import asyncio
import logging
import os

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

log = logging.getLogger(__name__)


@retry(wait=wait_exponential(min=1, max=30), stop=stop_after_attempt(5), reraise=True)
async def http_get_google_maps_directions(
	origin: Tuple[float, float],
	destination: Tuple[float, float],
	mode: str,
	session: aiohttp.ClientSession,
	http_timeout_s: int,
	google_maps_api_key: str,
) -> dict:
	lat1, lng1 = origin
	lat2, lng2 = destination
	url = f"https://maps.googleapis.com/maps/api/directions/json?origin={lat1},{lng1}&destination={lat2},{lng2}&mode={mode}&key={google_maps_api_key}"
	async with session.get(url, timeout=http_timeout_s) as resp:
		payload = await resp.json()
		if payload["status"] != "OK":
			raise RuntimeError(f"Directions failed: {payload['status']}")
		return payload["routes"][0]


async def http_get_google_maps_directions_distance_matrix(
	coords: List[Tuple[float, float]],
	mode: str,
	rate_limit_qps: int,
	http_timeout_s: int,
	google_maps_api_key: str,
) -> List[List[int]]:
	size = len(coords)
	distance_matrix: List[List[int]] = [[0] * size for _ in range(size)]
	gate = asyncio.Semaphore(rate_limit_qps)
	async with aiohttp.ClientSession() as session:
		tasks = []
		for i in range(size):
			for j in range(i + 1, size):

				async def http_fetch_google_maps_directions(
					i=i, j=j
				) -> Tuple[int, int, int]:
					async with gate:
						route = await http_get_google_maps_directions(
							coords[i],
							coords[j],
							mode,
							session,
							http_timeout_s,
							google_maps_api_key,
						)
					distance = route["legs"][0]["distance"]["value"]
					return i, j, distance

				tasks.append(http_fetch_google_maps_directions())
		results = await asyncio.gather(*tasks)
	for i, j, distance in results:
		distance_matrix[i][j] = distance
		distance_matrix[j][i] = distance
	return distance_matrix


def directions_distance_matrix(
	coords: List[Tuple[float, float]],
	mode: str,
	rate_limit_qps: int,
	http_timeout_s: int,
) -> List[List[int]]:
	google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
	if not google_maps_api_key:
		raise RuntimeError("GOOGLE_MAPS_API_KEY environment variable missing")
	coro = http_get_google_maps_directions_distance_matrix(
		coords, mode, rate_limit_qps, http_timeout_s, google_maps_api_key
	)
	return asyncio.run(coro)


def decode_google_maps_polyline(line: str) -> List[Tuple[float, float]]:
	def decode_value() -> int:
		nonlocal idx
		value = bit_shift = 0
		while True:
			encoded_byte = ord(line[idx]) - 63
			idx += 1
			value |= (encoded_byte & 0x1F) << bit_shift
			bit_shift += 5
			if encoded_byte < 0x20:
				break
		return ~(value >> 1) if value & 1 else value >> 1

	idx = lat = lng = 0
	coords: List[Tuple[float, float]] = []
	while idx < len(line):
		lat += decode_value()
		lng += decode_value()
		coords.append((lat / 1e5, lng / 1e5))
	return coords


async def google_maps_directions_polyline(
	origin: Tuple[float, float],
	destination: Tuple[float, float],
	mode: str,
	http_timeout_s: int,
	google_maps_api_key: str,
) -> List[Tuple[float, float]]:
	async with aiohttp.ClientSession() as session:
		route = await http_get_google_maps_directions(
			origin, destination, mode, session, http_timeout_s, google_maps_api_key
		)
	encoded = route["overview_polyline"]["points"]
	return decode_google_maps_polyline(encoded)


def directions_polyline(
	origin: Tuple[float, float],
	destination: Tuple[float, float],
	mode: str,
	http_timeout_s: int,
) -> List[Tuple[float, float]]:
	google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
	if not google_maps_api_key:
		raise RuntimeError("GOOGLE_MAPS_API_KEY environment variable missing")
	coro = google_maps_directions_polyline(
		origin, destination, mode, http_timeout_s, google_maps_api_key
	)
	return asyncio.run(coro)
