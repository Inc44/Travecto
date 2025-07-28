from __future__ import annotations
from pathlib import Path
from typing import Dict, Any

import toml


def load_config(config_path: str) -> Dict[str, Any]:
	config_file = Path(config_path)
	if not config_file.exists():
		raise FileNotFoundError(f"Configuration file not found: {config_path}")
	with open(config_file, "r", encoding="utf-8") as f:
		config = toml.load(f)
	settings = config.pop("settings", {})
	return {"settings": settings, "cities": config}
