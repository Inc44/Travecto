from __future__ import annotations
from pathlib import Path
from typing import Dict, Tuple
import json
import logging

log = logging.getLogger(__name__)


def load_cache(cache_file: Path) -> Dict[str, Tuple[float, float]]:
	if cache_file.exists():
		return json.loads(cache_file.read_text())
	return {}


def save_cache(cache: Dict[str, Tuple[float, float]], cache_file: Path) -> None:
	cache_file.write_text(json.dumps(cache, indent="\t", sort_keys=True))
