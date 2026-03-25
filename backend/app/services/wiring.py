from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.services.species_store import SpeciesStore
from app.services.nlp_service import NlpService


@lru_cache(maxsize=1)
def get_species_store() -> SpeciesStore:
    return SpeciesStore(settings.data_path)


@lru_cache(maxsize=1)
def get_nlp_service() -> NlpService:
    store = get_species_store()
    return NlpService.build(store.all())

