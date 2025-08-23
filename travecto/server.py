from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from .planner import calculate_time_minutes, compute_routes
from .visualizer import build_path, create_map, extract_places_coords
from .utils import hash_json

app = FastAPI(title="Travecto Server")
output_dir = Path.home() / ".cache/travecto/routes"
output_dir_path = Path(output_dir).expanduser().resolve()
output_dir_path.mkdir(parents=True, exist_ok=True)


class CityConfig(BaseModel):
	home: str | None = None
	places: List[str]
	mandatory_by_day: Dict[str, List[str]] = Field(default_factory=dict)
	alt_addresses: Dict[str, str] = Field(default_factory=dict)
	mode: Literal["direct", "walking", "transit", "driving", "bicycling"] = "direct"
	avg_speed_kmh: float | None = None

	@field_validator("home")
	@classmethod
	def home_len(cls, home: str | None) -> str | None:
		if home is not None and len(home) > 256:
			raise ValueError("home must be at most 256 characters.")
		return home

	@field_validator("places")
	@classmethod
	def places_len(cls, places: List[str]) -> List[str]:
		if len(places) > 256:
			raise ValueError("places must have at most 256 items.")
		for place in places:
			if len(place) > 256:
				raise ValueError("place must be at most 256 characters.")
		return places

	@field_validator("mandatory_by_day")
	@classmethod
	def mandatory_by_day_len(
		cls, mandatory_by_day: Dict[str, List[str]]
	) -> Dict[str, List[str]]:
		if sum(len(lst) for lst in mandatory_by_day.values()) > 256:
			raise ValueError("mandatory_by_day must have at most 256 items.")
		for day, lst in mandatory_by_day.items():
			for place in lst:
				if len(place) > 256:
					raise ValueError(
						"mandatory_by_day place must be at most 256 characters."
					)
		return mandatory_by_day

	@field_validator("alt_addresses")
	@classmethod
	def alt_addresses_len(cls, alt_addresses: Dict[str, str]) -> Dict[str, str]:
		if len(alt_addresses) > 256:
			raise ValueError("alt_addresses must have at most 256 items.")
		for original, replacement in alt_addresses.items():
			if len(original) > 256:
				raise ValueError(
					"alt_addresses original must be at most 256 characters."
				)
			if len(replacement) > 256:
				raise ValueError(
					"alt_addresses replacement must be at most 256 characters."
				)
		return alt_addresses


class PlanRequest(BaseModel):
	city_name: str = "custom"
	config: CityConfig
	workers: int = 32
	settings: Dict[str, Any] = Field(default_factory=dict)


def render_map(
	info,
	settings: Dict[str, Any],
	output_dir: str = str(Path.home() / ".cache/travecto/routes"),
) -> str:
	places = [info.places[i] for i in info.route]
	filename = f"{hash_json({'places': places, 'mode': info.mode})}.html"
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
	return f"/routes/{output_path.name}"


@app.post("/plan")
def plan(req: PlanRequest) -> JSONResponse:
	google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
	if google_maps_api_key:
		req.settings["google_maps_api_key"] = google_maps_api_key
	if "google_maps_api_key" not in req.settings:
		raise HTTPException(400, "GOOGLE_MAPS_API_KEY environment variable is required")
	thunderforest_api_key = os.getenv("THUNDERFOREST_API_KEY")
	if thunderforest_api_key:
		req.settings["thunderforest_api_key"] = thunderforest_api_key
	city_cfg = req.config.model_dump()
	if city_cfg.get("home") is None and city_cfg["places"]:
		city_cfg["home"] = city_cfg["places"][0]
	routes = compute_routes(
		req.city_name,
		city_cfg,
		req.workers,
		req.settings,
		city_cfg.get("mode", "direct"),
		quiet=True,
	)
	payload: List[Dict[str, Any]] = []
	for info in routes:
		places = [info.places[i] for i in info.route]
		total_distance_m = sum(
			info.distance_matrix[info.route[i]][info.route[i + 1]]
			for i in range(len(info.route) - 1)
		)
		payload.append(
			dict(
				day=info.day_idx,
				places=places,
				distance_m=total_distance_m,
				time_minutes=round(
					calculate_time_minutes(total_distance_m, info.speed_kmh), 1
				),
				mode=info.mode,
				map_path=render_map(info, req.settings),
			)
		)
	return JSONResponse({"routes": payload})


app.mount(
	"/routes",
	StaticFiles(directory=str(Path.home() / ".cache/travecto/routes")),
	name="routes",
)
app.mount(
	"/",
	StaticFiles(directory=str(Path(__file__).parent / "static"), html=True),
	name="static",
)
