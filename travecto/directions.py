from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Tuple

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

log = logging.getLogger(__name__)


def load_directions_cache(path: Path) -> Dict[str, int]:
	if path.exists():
		return json.loads(path.read_text(encoding="utf-8"))
	return {}


def save_directions_cache(cache: Dict[str, int], path: Path) -> None:
	path.write_text(
		json.dumps(cache, indent="\t", sort_keys=True, ensure_ascii=False),
		encoding="utf-8",
	)


@retry(wait=wait_exponential(min=1, max=30), stop=stop_after_attempt(5), reraise=True)
async def fetch_google_maps_directions(
	origin: Tuple[float, float],
	destination: Tuple[float, float],
	mode: str,
	session: aiohttp.ClientSession,
	http_timeout_s: int,
	google_maps_api_key: str,
) -> dict:
	lat1, lng1 = origin
	lat2, lng2 = destination
	url = (
		"https://maps.googleapis.com/maps/api/directions/json?"
		f"origin={lat1},{lng1}&destination={lat2},{lng2}&mode={mode}&key={google_maps_api_key}"
	)
	async with session.get(url, timeout=http_timeout_s) as resp:
		payload = await resp.json()
		if payload["status"] != "OK":
			raise RuntimeError(f"Directions failed: {payload['status']}")
		return payload["routes"][0]


def directions_distance_matrix(
	coords: List[Tuple[float, float]],
	mode: str,
	rate_limit_qps: int,
	http_timeout_s: int,
	quiet: bool,
	directions_cache_path: Path,
) -> List[List[int]]:
	google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
	if not google_maps_api_key:
		raise RuntimeError("GOOGLE_MAPS_API_KEY environment variable missing")
	directions_cache = load_directions_cache(directions_cache_path)
	size = len(coords)
	distance_matrix = [[0] * size for _ in range(size)]
	cache_misses = []
	for i in range(size):
		for j in range(i + 1, size):
			cache_key = build_cache_key(coords[i], coords[j], mode)
			if cache_key in directions_cache:
				distance = directions_cache[cache_key]
				distance_matrix[i][j] = distance_matrix[j][i] = distance
			else:
				cache_misses.append((i, j))
	if not cache_misses:
		if not quiet:
			print("All directions found in cache")
		return distance_matrix

	async def fetch_missing_directions() -> List[Tuple[int, int, int]]:
		gate = asyncio.Semaphore(rate_limit_qps)
		async with aiohttp.ClientSession() as session:
			tasks = []
			for i, j in cache_misses:

				async def fetch_directions(i=i, j=j) -> Tuple[int, int, int]:
					async with gate:
						route = await fetch_google_maps_directions(
							coords[i],
							coords[j],
							mode,
							session,
							http_timeout_s,
							google_maps_api_key,
						)
						distance = route["legs"][0]["distance"]["value"]
						return i, j, distance

				tasks.append(fetch_directions())
			if quiet:
				return await asyncio.gather(*tasks)
			from tqdm import tqdm

			results = []
			pbar = tqdm(total=len(tasks), desc="Fetching directions")
			for coro in asyncio.as_completed(tasks):
				result = await coro
				results.append(result)
				pbar.update()
			pbar.close()
			return results

	for i, j, distance in asyncio.run(fetch_missing_directions()):
		distance_matrix[i][j] = distance_matrix[j][i] = distance
		directions_cache[build_cache_key(coords[i], coords[j], mode)] = distance
	save_directions_cache(directions_cache, directions_cache_path)
	return distance_matrix


def build_cache_key(
	coord1: Tuple[float, float], coord2: Tuple[float, float], mode: str
) -> str:
	lat1, lng1 = coord1
	lat2, lng2 = coord2
	return f"{lat1},{lng1}|{lat2},{lng2}|{mode}"


def decode_google_maps_polyline(encoded_line: str) -> List[Tuple[float, float]]:
	def decode_value() -> int:
		nonlocal idx
		value = bit_shift = 0
		while True:
			encoded_byte = ord(encoded_line[idx]) - 63
			idx += 1
			value |= (encoded_byte & 0x1F) << bit_shift
			bit_shift += 5
			if encoded_byte < 0x20:
				break
		return ~(value >> 1) if value & 1 else value >> 1

	idx = lat = lng = 0
	coords = []
	while idx < len(encoded_line):
		lat += decode_value()
		lng += decode_value()
		coords.append((lat / 1e5, lng / 1e5))
	return coords


async def fetch_google_maps_directions_polyline(
	origin: Tuple[float, float],
	destination: Tuple[float, float],
	mode: str,
	http_timeout_s: int,
	google_maps_api_key: str,
) -> List[Tuple[float, float]]:
	async with aiohttp.ClientSession() as session:
		route = await fetch_google_maps_directions(
			origin, destination, mode, session, http_timeout_s, google_maps_api_key
		)
		encoded_polyline = route["overview_polyline"]["points"]
		return decode_google_maps_polyline(encoded_polyline)


def directions_polyline(
	origin: Tuple[float, float],
	destination: Tuple[float, float],
	mode: str,
	http_timeout_s: int,
) -> List[Tuple[float, float]]:
	google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
	if not google_maps_api_key:
		raise RuntimeError("GOOGLE_MAPS_API_KEY environment variable missing")
	return asyncio.run(
		fetch_google_maps_directions_polyline(
			origin, destination, mode, http_timeout_s, google_maps_api_key
		)
	)
