"""In-memory cache over JSON files in data/. Files are parsed once with orjson
and served from memory; with hot reload enabled they're re-read on mtime change."""

from pathlib import Path
from threading import Lock
from typing import Any

import orjson

from .config import settings


class JsonStore:
    def __init__(self, root: Path, hot_reload: bool) -> None:
        self.root = root
        self.hot_reload = hot_reload
        self._cache: dict[Path, tuple[float, Any, bytes]] = {}
        self._lock = Lock()

    def _resolve(self, rel: str) -> Path:
        path = (self.root / rel).resolve()
        if self.root.resolve() not in path.parents:
            raise FileNotFoundError(rel)
        if not path.is_file():
            raise FileNotFoundError(rel)
        return path

    def _entry(self, rel: str) -> tuple[float, Any, bytes]:
        path = self._resolve(rel)
        mtime = path.stat().st_mtime
        cached = self._cache.get(path)
        if cached and (not self.hot_reload or cached[0] == mtime):
            return cached
        with self._lock:
            raw = path.read_bytes()
            entry = (mtime, orjson.loads(raw), raw)
            self._cache[path] = entry
            return entry

    def get(self, rel: str) -> Any:
        """Parsed object (for filtering/aggregation in Python)."""
        return self._entry(rel)[1]

    def raw(self, rel: str) -> bytes:
        """Raw bytes (zero-cost passthrough for whole-file responses)."""
        return self._entry(rel)[2]

    def list(self, subdir: str) -> list[str]:
        base = self.root / subdir
        return sorted(p.stem for p in base.glob("*.json")) if base.is_dir() else []


store = JsonStore(settings.data_dir, settings.json_hot_reload)
