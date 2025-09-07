from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(slots=True)
class PricingCache:
    path: Path

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, data: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)


def default_cache_path() -> Path:
    return Path.cwd() / "pricing_cache" / "baselines.json"


def load_baselines_from_cache(path: Optional[Path] = None) -> Dict[str, Any]:
    cache = PricingCache(path or default_cache_path())
    return cache.load()

