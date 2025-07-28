from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .geocoder import geocode, load_cache, save_cache
from .solver import tsp

log = logging.getLogger(__name__)


def haversine_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> int:
	earth_radius_m = 6_371_008
	lat1, lng1 = map(math.radians, coord1)
	lat2, lng2 = map(math.radians, coord2)
	dlat = lat2 - lat1
	dlon = lng2 - lng1
	hav = (
		math.sin(dlat / 2) ** 2
		+ math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
	)
	return int(earth_radius_m * 2 * math.atan2(math.sqrt(hav), math.sqrt(1 - hav)))


def haversine_distance_matrix(coords: List[Tuple[float, float]]) -> List[List[int]]:
	size = len(coords)
	return [
		[0 if i == j else haversine_distance(coords[i], coords[j]) for j in range(size)]
		for i in range(size)
	]


def centroid(coords: List[Tuple[float, float]]) -> Tuple[float, float]:
	lat = sum(c[0] for c in coords) / len(coords)
	lon = sum(c[1] for c in coords) / len(coords)
	return lat, lon


def assign_days(
	coords: Dict[str, Tuple[float, float]],
	mandatory: Dict[int, List[str]],
	home: str,
) -> Dict[int, List[str]]:
	days: Dict[int, List[str]] = {d: list(lst) for d, lst in mandatory.items()}
	anchors = {d: centroid([coords[p] for p in lst]) for d, lst in days.items()}
	for place in coords:
		if place == home or any(place in grp for grp in days.values()):
			continue
		nearest = min(
			anchors, key=lambda d: haversine_distance(coords[place], anchors[d])
		)
		days[nearest].append(place)
	return days


def avg_speed_kmh(settings: Dict[str, Any]) -> float:
	metro_t = settings.get("metro_time", 0.5)
	metro_kmh = settings.get("metro_speed", 30)
	walk_t = settings.get("walking_time", 0.5)
	walk_kmh = settings.get("walking_speed", 5)
	return 1 / (metro_t / metro_kmh + walk_t / walk_kmh)


def avg_time_minutes(distance_m: int, speed_kmh: float) -> float:
	return distance_m / 1000 / speed_kmh * 60


def print_route(
	header: str,
	places: List[str],
	distance_matrix: List[List[int]],
	route: List[int],
	speed_kmh: float,
) -> None:
	total = sum(distance_matrix[route[i]][route[i + 1]] for i in range(len(route) - 1))
	print(header)
	for idx in route:
		print(places[idx])
	print(f"{total / 1000:.0f} km | {avg_time_minutes(total, speed_kmh):.0f} min")


def solve_route(
	places: List[str],
	coords: Dict[str, Tuple[float, float]],
	start_idx: int,
	workers: int,
	time_limit: int,
) -> List[int]:
	distance_matrix = haversine_distance_matrix([coords[p] for p in places])
	return tsp(distance_matrix, start_idx, workers, time_limit)


def plan_route(
	city_name: str,
	city_cfg: Dict[str, Any],
	workers: int,
	settings: Dict[str, Any],
) -> None:
	cache_path = Path(settings.get("cache_file", "geocode_cache.json"))
	cache = load_cache(cache_path)
	home = city_cfg["home"]
	places: List[str] = list(dict.fromkeys(city_cfg.get("places", [])))
	if home not in places:
		places.insert(0, home)
	coords = geocode(
		places,
		city_name,
		city_cfg.get("alt_addresses", {}),
		cache,
		settings.get("rate_limit_qps", 50),
		settings.get("http_timeout_s", 10),
		settings.get("probe_delay", 0.02),
	)
	save_cache(cache, cache_path)
	speed_kmh = city_cfg.get("avg_speed_kmh", avg_speed_kmh(settings))
	mandatory = city_cfg.get("mandatory_by_day", {})
	if mandatory:
		days = assign_days(coords, mandatory, home)
		for day_idx in sorted(days):
			places = list(dict.fromkeys(days[day_idx]))
			if home not in places:
				places.insert(0, home)
			start_idx = places.index(home)
			route = solve_route(
				places,
				coords,
				start_idx,
				workers,
				settings.get("tsp_time_limit", 6),
			)
			header = f"\n{city_name.upper()} – DAY {day_idx + 1}\nMust: " + ", ".join(
				mandatory[day_idx]
			)
			print_route(
				header,
				places,
				haversine_distance_matrix([coords[p] for p in places]),
				route,
				speed_kmh,
			)
	else:
		start_idx = places.index(home)
		route = solve_route(
			places,
			coords,
			start_idx,
			workers,
			settings.get("tsp_time_limit", 6),
		)
		print_route(
			f"\n{city_name.upper()}",
			places,
			haversine_distance_matrix([coords[p] for p in places]),
			route,
			speed_kmh,
		)
