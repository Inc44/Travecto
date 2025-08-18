from __future__ import annotations

import math
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import folium
from folium.plugins import LocateControl

from .directions import directions_polyline, build_direction_cache_key
from .planner import RouteInfo, compute_routes
from .utils import load_json, save_json

EARTH_RADIUS_M = 6_371_008
EARTH_RADIUS_KM = EARTH_RADIUS_M / 1_000
RAD_TO_DEG = 180.0 / math.pi
KM_TO_LAT = RAD_TO_DEG / EARTH_RADIUS_KM


def km_to_lat(km: float) -> float:
	return km * KM_TO_LAT


def km_to_lng(km: float, lat: float) -> float:
	return km * KM_TO_LAT / math.cos(math.radians(lat))


def calculate_bounding_box(
	coords: List[Tuple[float, float]], margin_km: float = 1.0
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
	lats, lngs = zip(*coords)
	margin_lat = km_to_lat(margin_km)
	margin_lng = km_to_lng(margin_km, sum(lats) / len(lats))
	return (
		(min(lats) - margin_lat, min(lngs) - margin_lng),
		(max(lats) + margin_lat, max(lngs) + margin_lng),
	)


def create_map(
	path_coords: List[Tuple[float, float]],
	marker_coords: List[Tuple[float, float]],
	names: List[str],
	thunderforest_api_key: str = "",
) -> folium.Map:
	center_lat = sum(coord[0] for coord in marker_coords) / len(marker_coords)
	center_lng = sum(coord[1] for coord in marker_coords) / len(marker_coords)
	folium_map = folium.Map(
		location=[center_lat, center_lng], tiles=None, max_bounds=True
	)
	folium.TileLayer(
		tiles="https://a.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png",
		name="Map",
		attr="OpenStreetMap France",
	).add_to(folium_map)
	folium.TileLayer(
		tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
		name="Satellite",
		attr="Esri",
		show=False,
	).add_to(folium_map)
	if thunderforest_api_key:
		folium.TileLayer(
			tiles=(
				"https://tile.thunderforest.com/transport/"
				"{z}/{x}/{y}.png?apikey=" + thunderforest_api_key
			),
			name="Transport",
			attr="Thunderforest",
			show=False,
		).add_to(folium_map)
	folium.LayerControl(position="topright").add_to(folium_map)
	LocateControl(auto_start=False, flyTo=True).add_to(folium_map)
	sw, ne = calculate_bounding_box(path_coords)
	folium_map.fit_bounds([sw, ne])
	folium.PolyLine(path_coords, color="blue", weight=4, opacity=0.75).add_to(
		folium_map
	)
	for idx, (lat, lng) in enumerate(marker_coords):
		folium.Marker(
			location=[lat, lng],
			tooltip=f"{idx} {names[idx]}",
			icon=folium.Icon(color="red" if idx == 0 else "blue"),
		).add_to(folium_map)
	return folium_map


def extract_places_coords(
	info: RouteInfo,
) -> Tuple[List[str], List[Tuple[float, float]]]:
	places = [info.places[i] for i in info.route]
	coords = [info.coords[place] for place in places]
	return places, coords


def build_path(
	coords: List[Tuple[float, float]],
	mode: str,
	settings: Dict[str, Any],
) -> List[Tuple[float, float]]:
	if mode == "direct":
		return coords
	http_timeout_s = settings.get("http_timeout_s", 6)
	polyline_cache_path = Path(
		settings.get("polyline_cache_file", "cache/polyline_cache.json")
	)
	polyline_cache = load_json(polyline_cache_path)
	path = []
	for i in range(len(coords) - 1):
		cache_key = build_direction_cache_key(coords[i], coords[i + 1], mode)
		if cache_key in polyline_cache:
			segment = polyline_cache[cache_key]
		else:
			segment = directions_polyline(
				coords[i], coords[i + 1], mode, http_timeout_s
			)
			polyline_cache[cache_key] = segment
		if not segment:
			continue
		if path:
			path.extend(segment[1:])
		else:
			path.extend(segment)
	save_json(polyline_cache, polyline_cache_path)
	return path or coords


def visualize_route(
	city_name: str,
	city_cfg: Dict,
	workers: int,
	settings: Dict,
	output_dir: str = "routes",
	mode: Optional[str] = None,
	quiet: bool = False,
) -> None:
	for info in compute_routes(city_name, city_cfg, workers, settings, mode, quiet):
		header = city_name.capitalize()
		if info.day_idx is not None:
			header += f" Day {info.day_idx}"
		filename = f"{header}.html"
		output_dir_path = Path(output_dir).expanduser().resolve()
		output_dir_path.mkdir(parents=True, exist_ok=True)
		output_path = output_dir_path / filename
		if not output_path.exists():
			places, marker_coords = extract_places_coords(info)
			path_coords = build_path(marker_coords, info.mode, settings)
			folium_map = create_map(
				path_coords,
				marker_coords,
				places,
				settings.get("thunderforest_api_key", ""),
			)
			folium_map.save(output_path)
		webbrowser.open(output_path.as_uri())
