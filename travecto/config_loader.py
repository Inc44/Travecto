from __future__ import annotations
from pathlib import Path
from typing import Any, Dict

import toml


def load_config(config_path: str) -> Dict[str, Any]:
	config_file = Path(config_path)
	if not config_file.exists():
		raise FileNotFoundError(f"Configuration file not found: {config_path}")
	config = toml.loads(config_file.read_text(encoding="utf-8"))
	settings = config.pop("settings", {})
	return {"settings": settings, "cities": config}
