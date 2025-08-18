from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any, Dict


def hash_json(obj: Any) -> str:
	payload = json.dumps(obj, indent="\t", sort_keys=True, ensure_ascii=False)
	hashed = hashlib.sha256(payload.encode("utf-8")).digest()
	encoded = base64.urlsafe_b64encode(hashed).decode("ascii")
	return encoded[:11]


def load_json(path: Path) -> Dict[str, Any]:
	if path.exists():
		return json.loads(path.read_text(encoding="utf-8"))
	return {}


def save_json(obj: Any, path: Path) -> None:
	path.write_text(
		json.dumps(obj, indent="\t", sort_keys=True, ensure_ascii=False),
		encoding="utf-8",
	)
