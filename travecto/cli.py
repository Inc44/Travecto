from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

import uvicorn

from .config_loader import load_config
from .planner import plan_route
from .visualizer import visualize_route


def main() -> None:
	arg_parser = argparse.ArgumentParser(
		description=(
			"Optimizes travel routes using Google Maps Geocoding API, "
			"Google Maps Directions API, and "
			"a traveling salesman problem solver from OR-Tools"
		)
	)
	arg_parser.add_argument(
		"-i",
		"--input",
		default="demo.toml",
		help="Path to the TOML configuration file. Default: demo.toml.",
	)
	arg_parser.add_argument(
		"-o",
		"--output",
		default=str(Path.home() / ".cache/travecto/routes"),
		help="Directory for map files. Default: ~/.cache/travecto/routes.",
	)
	arg_parser.add_argument(
		"--maps",
		action="store_true",
		help="Generate interactive HTML maps for visualization.",
	)
	arg_parser.add_argument(
		"--workers",
		type=int,
		default=32,
		help="Number of OR-Tools search workers. Default: 32.",
	)
	arg_parser.add_argument(
		"--loglevel",
		type=str.upper,
		choices=["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
		default="ERROR",
		help="Set the logging level. Default: ERROR.",
	)
	arg_parser.add_argument(
		"--force",
		choices=["direct", "walking", "transit", "driving", "bicycling"],
		help="Override routing mode defined in the configuration.",
	)
	arg_parser.add_argument(
		"-q",
		"--quiet",
		action="store_true",
		help="Hide progress bars.",
	)
	arg_parser.add_argument(
		"--server",
		action="store_true",
		help="Run the server for interactive route planning",
	)
	args = arg_parser.parse_args()
	logging.basicConfig(level=args.loglevel, format="%(levelname)s: %(message)s")
	if args.server:
		uvicorn.run("travecto.server:app")
		return
	config = load_config(args.input)
	settings = config.get("settings", {})
	google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY") or settings.get(
		"google_maps_api_key"
	)
	if not google_maps_api_key:
		raise RuntimeError(
			"google_maps_api_key setting or GOOGLE_MAPS_API_KEY environment variable is required"
		)
	settings["google_maps_api_key"] = google_maps_api_key
	thunderforest_api_key = os.getenv("THUNDERFOREST_API_KEY") or settings.get(
		"thunderforest_api_key", ""
	)
	if thunderforest_api_key:
		settings["thunderforest_api_key"] = thunderforest_api_key
	quiet = args.quiet or settings.get("quiet", False)
	for city_name, city_cfg in config.get("cities", {}).items():
		if args.maps:
			visualize_route(
				city_name,
				city_cfg,
				args.workers,
				settings,
				args.output,
				args.force,
				quiet,
			)
		else:
			plan_route(
				city_name,
				city_cfg,
				args.workers,
				settings,
				args.force,
				quiet,
			)


if __name__ == "__main__":
	main()
