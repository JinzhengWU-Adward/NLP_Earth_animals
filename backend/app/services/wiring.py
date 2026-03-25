from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.services.species_store import SpeciesStore


@lru_cache(maxsize=1)
def get_species_store() -> SpeciesStore:
    return SpeciesStore(settings.data_path)

