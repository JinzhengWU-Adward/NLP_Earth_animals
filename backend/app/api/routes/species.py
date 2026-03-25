from __future__ import annotations

from fastapi import APIRouter, Depends

from app.models.species import Species
from app.services.species_store import SpeciesStore
from app.services.wiring import get_species_store

router = APIRouter()


@router.get("/species", response_model=list[Species])
def list_species(store: SpeciesStore = Depends(get_species_store)) -> list[Species]:
    return store.all()

