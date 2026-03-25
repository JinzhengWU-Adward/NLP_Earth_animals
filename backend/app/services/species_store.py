from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models.species import Species


class SpeciesStore:
    def __init__(self, data_path: Path):
        self.data_path = data_path
        self._species: list[Species] | None = None

    def load(self) -> list[Species]:
        if self._species is not None:
            return self._species

        raw = self.data_path.read_text(encoding="utf-8")
        payload: Any = json.loads(raw)
        self._species = [Species.model_validate(item) for item in payload]
        return self._species

    def all(self) -> list[Species]:
        return self.load()

    def by_region(self, region: str) -> list[Species]:
        r = region.strip().lower()
        return [s for s in self.load() if s.region.strip().lower() == r]

