from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple
import math
import webbrowser

import folium

from .planner import RouteInfo, compute_routes

EARTH_RADIUS_M = 6_371_008
EARTH_RADIUS_KM = EARTH_RADIUS_M / 1_000
RAD_TO_DEG = 180.0 / math.pi
KM_TO_LAT = RAD_TO_DEG / EARTH_RADIUS_KM


def km_to_lat(km: float) -> float:
	return km * KM_TO_LAT


def km_to_lng(km: float, lat: float) -> float:
	return km * KM_TO_LAT / math.cos(math.radians(lat))


def bounding_box(
	coords: List[Tuple[float, float]], margin_km: float = 4.0
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
	lats, lngs = zip(*coords)
	margin_lat = km_to_lat(margin_km)
	margin_lng = km_to_lng(margin_km, sum(lats) / len(lats))
	return (
		(min(lats) - margin_lat, min(lngs) - margin_lng),
		(max(lats) + margin_lat, max(lngs) + margin_lng),
	)


def create_map(
	coords: List[Tuple[float, float]], names: List[str], thunderforest_api_key: str = ""
) -> folium.Map:
	center_lat = sum(c[0] for c in coords) / len(coords)
	center_lng = sum(c[1] for c in coords) / len(coords)
	fmap = folium.Map(
		location=[center_lat, center_lng],
		tiles=None,
		max_bounds=True,
		zoom_control=True,
	)
	folium.TileLayer(
		tiles="https://a.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png",
		name="Map",
		attr="OpenStreetMap France",
	).add_to(fmap)
	folium.TileLayer(
		tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
		name="Satellite",
		attr="Esri",
		show=False,
	).add_to(fmap)
	if thunderforest_api_key:
		folium.TileLayer(
			tiles="https://tile.thunderforest.com/transport/{z}/{x}/{y}.png?apikey="
			+ thunderforest_api_key,
			name="Transport",
			attr="Thunderforest",
			show=False,
		).add_to(fmap)
	folium.LayerControl(position="topright").add_to(fmap)
	sw, ne = bounding_box(coords)
	fmap.fit_bounds([sw, ne])
	folium.PolyLine(coords, color="blue", weight=4, opacity=0.75).add_to(fmap)
	for index, (lat, lng) in enumerate(coords):
		folium.Marker(
			location=[lat, lng],
			tooltip=f"{index} {names[index]}",
			icon=folium.Icon(color="red" if index == 0 else "blue"),
		).add_to(fmap)
	return fmap


def get_places_coords(info: RouteInfo) -> Tuple[List[str], List[Tuple[float, float]]]:
	places = [info.places[i] for i in info.route]
	coords = [info.coords[p] for p in places]
	return places, coords


def visualize_route(
	city_name: str,
	city_cfg: Dict,
	workers: int,
	settings: Dict,
	output_dir: str = "routes",
) -> None:
	for info in compute_routes(city_name, city_cfg, workers, settings):
		places, coords = get_places_coords(info)
		fmap = create_map(coords, places, settings.get("thunderforest_api_key", ""))
		header = f"{city_name.capitalize()}"
		if info.day_idx is not None:
			header += f" Day {int(info.day_idx) + 1}"
		filename = header + ".html"
		output_dir_path = Path(output_dir).expanduser().resolve()
		output_dir_path.mkdir(parents=True, exist_ok=True)
		output_path = output_dir_path / filename
		fmap.save(output_path)
		webbrowser.open(output_path.as_uri())
