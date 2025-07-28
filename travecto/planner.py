from __future__ import annotations
from typing import Dict, Any


def calculate_avg_speed(settings: Dict[str, Any]) -> float:
	metro_time = settings.get("metro_time", 0.5)
	metro_speed = settings.get("metro_speed", 30)
	walking_time = settings.get("walking_time", 0.5)
	walking_speed = settings.get("walking_speed", 5)
	return 1 / (metro_time / metro_speed + walking_time / walking_speed)


def minutes(distance_m: int, avg_speed_kmh: float) -> float:
	return distance_m / 1000 / avg_speed_kmh * 60
