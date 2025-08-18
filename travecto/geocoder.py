from __future__ import annotations

import asyncio
import logging
import os
import unicodedata
from typing import Dict, List, Tuple

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

log = logging.getLogger(__name__)


def strip_accents(text: str) -> str:
	normalized_text = unicodedata.normalize("NFKD", text)
	return "".join(char for char in normalized_text if not unicodedata.combining(char))


@retry(wait=wait_exponential(min=1, max=30), stop=stop_after_attempt(5), reraise=True)
async def fetch_google_maps_location(
	query: str,
	session: aiohttp.ClientSession,
	http_timeout_s: int,
	google_maps_api_key: str,
) -> Tuple[float, float]:
	url = (
		"https://maps.googleapis.com/maps/api/geocode/json?address="
		f"{aiohttp.helpers.quote(query)}&key={google_maps_api_key}"
	)
	async with session.get(url, timeout=http_timeout_s) as resp:
		payload = await resp.json()
	if payload["status"] != "OK":
		raise RuntimeError(f"Geocode failed for '{query}': {payload['status']}")
	location = payload["results"][0]["geometry"]["location"]
	return location["lat"], location["lng"]


async def geocode_google_maps_location(
	name: str,
	city: str,
	alt_map: Dict[str, str],
	http_timeout_s: int,
	probe_delay_s: float,
	gate: asyncio.Semaphore,
	session: aiohttp.ClientSession,
	google_maps_api_key: str,
	cache: Dict[str, Tuple[float, float]],
) -> Tuple[str, Tuple[float, float]]:
	if name in cache:
		return name, cache[name]
	search_queries = [alt_map.get(name, name)]
	if city not in search_queries[0]:
		search_queries.append(f"{name}, {city}")
	search_queries.extend(
		[
			f"{name}, {city}, France",
			strip_accents(name) + f", {city}",
		]
	)
	for query in search_queries:
		async with gate:
			try:
				coords = await fetch_google_maps_location(
					query, session, http_timeout_s, google_maps_api_key
				)
				cache[name] = coords
				return name, coords
			except Exception as e:
				log.debug("Query '%s' failed: %s", query, e)
		await asyncio.sleep(probe_delay_s)
	raise RuntimeError(f"Geocoding failed for {name}")


async def geocode_google_maps_locations(
	places: List[str],
	city: str,
	alt_map: Dict[str, str],
	rate_limit_qps: int,
	http_timeout_s: int,
	probe_delay_s: float,
	google_maps_api_key: str,
	cache: Dict[str, Tuple[float, float]],
	quiet: bool,
) -> Dict[str, Tuple[float, float]]:
	if all(place in cache for place in places):
		if not quiet:
			print("All geocoded places found in cache")
		return {place: cache[place] for place in places}
	gate = asyncio.Semaphore(rate_limit_qps)
	async with aiohttp.ClientSession() as session:
		tasks = [
			geocode_google_maps_location(
				place,
				city,
				alt_map,
				http_timeout_s,
				probe_delay_s,
				gate,
				session,
				google_maps_api_key,
				cache,
			)
			for place in places
		]
		if quiet:
			results = await asyncio.gather(*tasks)
		else:
			from tqdm import tqdm

			pbar = tqdm(total=len(tasks), desc=f"Geocoding {city.capitalize()}")
			results = []
			for task in asyncio.as_completed(tasks):
				result = await task
				results.append(result)
				pbar.update()
			pbar.close()
	return dict(results)


def geocode(
	places: List[str],
	city: str,
	alt_map: Dict[str, str],
	cache: Dict[str, Tuple[float, float]],
	rate_limit_qps: int,
	http_timeout_s: int,
	probe_delay_s: float,
	quiet: bool,
) -> Dict[str, Tuple[float, float]]:
	google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
	if not google_maps_api_key:
		raise RuntimeError("GOOGLE_MAPS_API_KEY environment variable missing")
	return asyncio.run(
		geocode_google_maps_locations(
			places,
			city,
			alt_map,
			rate_limit_qps,
			http_timeout_s,
			probe_delay_s,
			google_maps_api_key,
			cache,
			quiet,
		)
	)
