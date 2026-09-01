from __future__ import annotations

import json
from pathlib import Path
from typing import Set


class ProcessedState:
    """Tracks message UIDs that have already been triaged, so re-runs don't duplicate work."""

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self._processed: Set[str] = set()
        self._load()

    def _load(self) -> None:
        if self.state_file.exists():
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            self._processed = set(data.get("processed_uids", []))

    def is_processed(self, uid: str) -> bool:
        return uid in self._processed

    def mark_processed(self, uid: str) -> None:
        self._processed.add(uid)

    def save(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps({"processed_uids": sorted(self._processed)}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
