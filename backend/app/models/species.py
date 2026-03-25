from __future__ import annotations

from pydantic import BaseModel, Field


class Species(BaseModel):
    id: str = Field(..., description="Stable identifier for the species entry")
    species_name: str
    region: str
    latitude: float
    longitude: float
    habitat: str
    diet: str
    description: str

