from __future__ import annotations
import argparse
import logging


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
	logging.basicConfig(level=args.loglevel, format="%(levelname)s: %(message)s")


if __name__ == "__main__":
	main()
