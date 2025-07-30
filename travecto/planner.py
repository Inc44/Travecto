from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .directions import (
	directions_distance_matrix,
	load_directions_cache,
	save_directions_cache,
)
from .geocoder import geocode, load_geocode_cache, save_geocode_cache
from .solver import tsp

log = logging.getLogger(__name__)


@dataclass
class RouteInfo:
	city_name: str
	places: List[str]
	coords: Dict[str, Tuple[float, float]]
	speed_kmh: float
	day_idx: Optional[str]
	route: List[int]
	header: str
	distance_matrix: List[List[int]]
	mode: str


def haversine_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> int:
	earth_radius_m = 6_371_008
	lat1, lng1 = map(math.radians, coord1)
	lat2, lng2 = map(math.radians, coord2)
	dlat = lat2 - lat1
	dlng = lng2 - lng1
	hav = (
		math.sin(dlat / 2) ** 2
		+ math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
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
	lng = sum(c[1] for c in coords) / len(coords)
	return lat, lng


def assign_days(
	coords: Dict[str, Tuple[float, float]],
	mandatory: Dict[str, List[str]],
	home: str,
) -> Dict[str, List[str]]:
	days: Dict[str, List[str]] = {str(d): list(lst) for d, lst in mandatory.items()}
	anchors = {d: centroid([coords[p] for p in lst]) for d, lst in days.items()}
	for place in coords:
		if place == home or any(place in grp for grp in days.values()):
			continue
		nearest = min(
			anchors,
			key=lambda d: haversine_distance(coords[place], anchors[d]),
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
	total_m = sum(
		distance_matrix[route[i]][route[i + 1]] for i in range(len(route) - 1)
	)
	print(header)
	for idx in route:
		print(places[idx])
	print(f"{total_m / 1000:.1f} km | {avg_time_minutes(total_m, speed_kmh):.0f} min")


def get_distance_matrix(
	places: List[str],
	coords: Dict[str, Tuple[float, float]],
	mode: str,
	settings: Dict[str, Any],
	quiet: bool,
) -> List[List[int]]:
	if mode == "direct":
		return haversine_distance_matrix([coords[n] for n in places])
	directions_cache_file = settings.get(
		"directions_cache_file", "directions_cache.json"
	)
	rate_limit_qps = settings.get("rate_limit_qps", 50)
	http_timeout_s = settings.get("http_timeout_s", 6)
	return directions_distance_matrix(
		[coords[n] for n in places],
		mode,
		rate_limit_qps,
		http_timeout_s,
		quiet,
		directions_cache_file,
	)


def compute_routes(
	city_name: str,
	city_cfg: Dict[str, Any],
	workers: int,
	settings: Dict[str, Any],
	mode: Optional[str] = None,
	quiet: bool = False,
) -> List[RouteInfo]:
	geocode_cache_path = Path(settings.get("cache_file", "geocode_cache.json"))
	geocode_cache = load_geocode_cache(geocode_cache_path)
	home = city_cfg["home"]
	places: List[str] = list(dict.fromkeys(city_cfg.get("places", [])))
	if home not in places:
		places.insert(0, home)
	coords = geocode(
		places,
		city_name,
		city_cfg.get("alt_addresses", {}),
		geocode_cache,
		settings.get("rate_limit_qps", 50),
		settings.get("http_timeout_s", 6),
		settings.get("probe_delay", 0.02),
		quiet,
	)
	save_geocode_cache(geocode_cache, geocode_cache_path)
	speed_kmh = city_cfg.get("avg_speed_kmh", avg_speed_kmh(settings))
	time_limit_s = settings.get("tsp_time_limit_s", 6)
	mode = mode or city_cfg.get("mode", "direct")
	mandatory = city_cfg.get("mandatory_by_day", {})
	routes: List[RouteInfo] = []
	if mandatory:
		days = assign_days(coords, mandatory, home)
		for day_idx in sorted(days):
			day_places = list(dict.fromkeys(days[day_idx]))
			if home not in day_places:
				day_places.insert(0, home)
			distance_matrix = get_distance_matrix(
				day_places, coords, mode, settings, quiet
			)
			route = tsp(distance_matrix, day_places.index(home), workers, time_limit_s)
			header = (
				f"\n{city_name.capitalize()} - Day {day_idx}"
				f"\nMust: {', '.join(mandatory[day_idx])}"
			)
			routes.append(
				RouteInfo(
					city_name,
					day_places,
					coords,
					speed_kmh,
					day_idx,
					route,
					header,
					distance_matrix,
					mode,
				)
			)
	else:
		distance_matrix = get_distance_matrix(places, coords, mode, settings, quiet)
		route = tsp(distance_matrix, places.index(home), workers, time_limit_s)
		header = f"\n{city_name.upper()}"
		routes.append(
			RouteInfo(
				city_name,
				places,
				coords,
				speed_kmh,
				None,
				route,
				header,
				distance_matrix,
				mode,
			)
		)
	return routes


def plan_route(
	city_name: str,
	city_cfg: Dict[str, Any],
	workers: int,
	settings: Dict[str, Any],
	mode: Optional[str] = None,
	quiet: bool = False,
) -> None:
	for info in compute_routes(city_name, city_cfg, workers, settings, mode, quiet):
		print_route(
			info.header, info.places, info.distance_matrix, info.route, info.speed_kmh
		)
