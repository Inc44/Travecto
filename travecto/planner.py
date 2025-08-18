from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .directions import directions_distance_matrix
from .geocoder import geocode
from .solver import tsp
from .utils import hash_json, load_json, save_json

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
	delta_lat = lat2 - lat1
	delta_lng = lng2 - lng1
	haversine_formula = (
		math.sin(delta_lat / 2) ** 2
		+ math.cos(lat1) * math.cos(lat2) * math.sin(delta_lng / 2) ** 2
	)
	return int(
		earth_radius_m
		* 2
		* math.atan2(math.sqrt(haversine_formula), math.sqrt(1 - haversine_formula))
	)


def haversine_distance_matrix(coords: List[Tuple[float, float]]) -> List[List[int]]:
	size = len(coords)
	return [
		[0 if i == j else haversine_distance(coords[i], coords[j]) for j in range(size)]
		for i in range(size)
	]


def centroid(coords: List[Tuple[float, float]]) -> Tuple[float, float]:
	total_lat = sum(coord[0] for coord in coords) / len(coords)
	total_lng = sum(coord[1] for coord in coords) / len(coords)
	return total_lat, total_lng


def assign_days(
	coords: Dict[str, Tuple[float, float]],
	mandatory: Dict[str, List[str]],
	home: str,
) -> Dict[str, List[str]]:
	days = {str(day): list(places) for day, places in mandatory.items()}
	anchors = {
		day: centroid([coords[place] for place in places])
		for day, places in days.items()
	}
	for place in coords:
		if place == home or any(place in group for group in days.values()):
			continue
		nearest_day = min(
			anchors,
			key=lambda day: haversine_distance(coords[place], anchors[day]),
		)
		days[nearest_day].append(place)
	return days


def calculate_average_speed_kmh(settings: Dict[str, Any]) -> float:
	metro_time_fraction = settings.get("metro_time", 0.5)
	metro_speed_kmh = settings.get("metro_speed", 30)
	walking_time_fraction = settings.get("walking_time", 0.5)
	walking_speed_kmh = settings.get("walking_speed", 5)
	return 1 / (
		metro_time_fraction / metro_speed_kmh
		+ walking_time_fraction / walking_speed_kmh
	)


def calculate_time_minutes(distance_m: int, speed_kmh: Optional[float]) -> float:
	if not speed_kmh:
		return 0.0
	return distance_m / 1000 / speed_kmh * 60


def print_route(
	header: str,
	places: List[str],
	distance_matrix: List[List[int]],
	route: List[int],
	speed_kmh: float,
) -> None:
	total_distance_m = sum(
		distance_matrix[route[i]][route[i + 1]] for i in range(len(route) - 1)
	)
	print(header)
	for idx in route:
		print(places[idx])
	print(
		f"{total_distance_m / 1000:.1f} km | {calculate_time_minutes(total_distance_m, speed_kmh):.0f} min"
	)


def build_distance_matrix(
	places: List[str],
	coords: Dict[str, Tuple[float, float]],
	mode: str,
	settings: Dict[str, Any],
	quiet: bool,
) -> List[List[int]]:
	if mode == "direct":
		return haversine_distance_matrix([coords[place] for place in places])
	directions_cache_path = Path(
		settings.get("directions_cache_file", "directions_cache.json")
	)
	rate_limit_qps = settings.get("rate_limit_qps", 50)
	http_timeout_s = settings.get("http_timeout_s", 6)
	return directions_distance_matrix(
		[coords[place] for place in places],
		mode,
		rate_limit_qps,
		http_timeout_s,
		quiet,
		directions_cache_path,
	)


def build_tsp_cache_key(
	distance_matrix: List[List[int]],
	start_idx: int,
) -> str:
	obj = {
		"distance_matrix": distance_matrix,
		"start_idx": start_idx,
	}
	return hash_json(obj)


def compute_routes(
	city_name: str,
	city_cfg: Dict[str, Any],
	workers: int,
	settings: Dict[str, Any],
	mode: Optional[str] = None,
	quiet: bool = False,
) -> List[RouteInfo]:
	geocode_cache_path = Path(settings.get("geocode_cache_file", "geocode_cache.json"))
	geocode_cache = load_json(geocode_cache_path)
	home = city_cfg["home"]
	places = list(dict.fromkeys(city_cfg.get("places", [])))
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
	save_json(geocode_cache, geocode_cache_path)
	speed_kmh = city_cfg.get("avg_speed_kmh") or calculate_average_speed_kmh(settings)
	time_limit_s = settings.get("tsp_time_limit_s", 1)
	routing_mode = mode or city_cfg.get("mode", "direct")
	mandatory = city_cfg.get("mandatory_by_day", {})
	routes = []
	tsp_cache_path = Path(settings.get("tsp_cache_file", "tsp_cache.json"))
	tsp_cache = load_json(tsp_cache_path)
	if mandatory:
		days = assign_days(coords, mandatory, home)
		for day_idx in sorted(days):
			day_places = list(dict.fromkeys(days[day_idx]))
			if home not in day_places:
				day_places.insert(0, home)
			distance_matrix = build_distance_matrix(
				day_places, coords, routing_mode, settings, quiet
			)
			start_idx = day_places.index(home)
			cache_key = build_tsp_cache_key(distance_matrix, start_idx)
			if cache_key in tsp_cache:
				route = tsp_cache[cache_key]
			else:
				route = tsp(distance_matrix, start_idx, workers, time_limit_s)
				tsp_cache[cache_key] = route
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
					routing_mode,
				)
			)
	else:
		distance_matrix = build_distance_matrix(
			places, coords, routing_mode, settings, quiet
		)
		start_idx = places.index(home)
		cache_key = build_tsp_cache_key(distance_matrix, start_idx)
		if cache_key in tsp_cache:
			route = tsp_cache[cache_key]
		else:
			route = tsp(distance_matrix, start_idx, workers, time_limit_s)
			tsp_cache[cache_key] = route
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
				routing_mode,
			)
		)
	save_json(tsp_cache, tsp_cache_path)
	return routes


def plan_route(
	city_name: str,
	city_cfg: Dict[str, Any],
	workers: int,
	settings: Dict[str, Any],
	mode: Optional[str] = None,
	quiet: bool = False,
) -> None:
	routes = compute_routes(city_name, city_cfg, workers, settings, mode, quiet)
	for info in routes:
		print_route(
			info.header, info.places, info.distance_matrix, info.route, info.speed_kmh
		)
