from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple
import asyncio
import json
import logging
import os
import unicodedata

from tenacity import retry, stop_after_attempt, wait_exponential
import aiohttp

log = logging.getLogger(__name__)


def strip_accents(unistr: str) -> str:
	norm = unicodedata.normalize("NFKD", unistr)
	return "".join(chr for chr in norm if not unicodedata.combining(chr))


def load_cache(path: Path) -> Dict[str, Tuple[float, float]]:
	if path.exists():
		return json.loads(path.read_text())
	return {}


def save_cache(cache: Dict[str, Tuple[float, float]], path: Path) -> None:
	path.write_text(json.dumps(cache, indent="\t", sort_keys=True))


@retry(wait=wait_exponential(min=1, max=30), stop=stop_after_attempt(5), reraise=True)
async def http_get_google_maps_location(
	query: str,
	session: aiohttp.ClientSession,
	timeout_s: int,
	google_maps_api_key: str,
) -> Tuple[float, float]:
	url = f"https://maps.googleapis.com/maps/api/geocode/json?address={aiohttp.helpers.quote(query)}&key={google_maps_api_key}"
	async with session.get(url, timeout=timeout_s) as resp:
		payload = await resp.json()
		if payload["status"] != "OK":
			raise RuntimeError(f"Geocode failed for '{query}': {payload['status']}")
		loc = payload["results"][0]["geometry"]["location"]
		return loc["lat"], loc["lng"]


async def geocode_google_maps_location(
	name: str,
	city: str,
	alt_map: Dict[str, str],
	timeout_s: int,
	probe_delay_s: float,
	gate: asyncio.Semaphore,
	session: aiohttp.ClientSession,
	google_maps_api_key: str,
	cache: Dict[str, Tuple[float, float]],
) -> Tuple[str, Tuple[float, float]]:
	if name in cache:
		return name, tuple(cache[name])
	probes: List[str] = [alt_map.get(name, name)]
	if city not in probes[0]:
		probes.append(f"{name}, {city}")
	probes.extend(
		[
			f"{name}, {city}, France",
			strip_accents(name) + f", {city}",
		]
	)
	for probe in probes:
		async with gate:
			try:
				coords = await http_get_google_maps_location(
					probe, session, timeout_s, google_maps_api_key
				)
				cache[name] = coords
				return name, coords
			except Exception as e:
				log.debug("Probe '%s' failed: %s", probe, e)
				await asyncio.sleep(probe_delay_s)
	raise RuntimeError(f"Geocoding failed for {name}")


async def geocode_google_maps_locations(
	places: List[str],
	city: str,
	alt_map: Dict[str, str],
	rate_limit_qps: int,
	timeout_s: int,
	probe_delay_s: float,
	google_maps_api_key: str,
	cache: Dict[str, Tuple[float, float]],
) -> Dict[str, Tuple[float, float]]:
	gate = asyncio.Semaphore(rate_limit_qps)
	async with aiohttp.ClientSession() as session:
		tasks = [
			geocode_google_maps_location(
				place,
				city,
				alt_map,
				timeout_s,
				probe_delay_s,
				gate,
				session,
				google_maps_api_key,
				cache,
			)
			for place in places
		]
		results = await asyncio.gather(*tasks)
	return dict(results)


def geocode(
	places: List[str],
	city: str,
	alt_map: Dict[str, str],
	cache: Dict[str, Tuple[float, float]],
	rate_limit_qps: int,
	timeout_s: int,
	probe_delay_s: float,
) -> Dict[str, Tuple[float, float]]:
	google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
	if not google_maps_api_key:
		raise RuntimeError("GOOGLE_MAPS_API_KEY environment variable missing")
	coro = geocode_google_maps_locations(
		places,
		city,
		alt_map,
		rate_limit_qps,
		timeout_s,
		probe_delay_s,
		google_maps_api_key,
		cache,
	)
	return asyncio.run(coro)
