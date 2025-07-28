from __future__ import annotations
import argparse
import os

from .config_loader import load_config
from .planner import plan_route
from .visualizer import visualize_route


def main() -> None:
	arg_parser = argparse.ArgumentParser(
		description="Optimizes travel routes using Google Maps Geocoding API and the traveling salesman problem solver from OR-Tools"
	)
	arg_parser.add_argument(
		"-i",
		"--input",
		default="config.toml",
		help="Path to the TOML configuration file. Default: `config.toml`.",
	)
	arg_parser.add_argument(
		"-o",
		"--output",
		default="routes",
		help="Directory for map files. Default: `routes`.",
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
	args = arg_parser.parse_args()
	google_maps_api_key = os.getenv("GOOGLE_API_KEY")
	if not google_maps_api_key:
		raise RuntimeError("GOOGLE_API_KEY environment variable is required")
	config = load_config(args.input)
	settings = config.get("settings", {})
	cities = config.get("cities", {})
	for city_name, city_cfg in cities.items():
		if args.maps:
			visualize_route(city_name, city_cfg, args.workers, settings, args.output)
		else:
			plan_route(city_name, city_cfg, args.workers, settings)


if __name__ == "__main__":
	main()
