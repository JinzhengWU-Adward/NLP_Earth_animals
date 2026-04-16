from __future__ import annotations

from typing import Annotated, Literal, Union

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.services.nlp_service import NlpService
from app.services.wiring import get_nlp_service

router = APIRouter()


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class QueryResponse(BaseModel):
    answer: str
    map_actions: list[
        Annotated[
            Union[
                "HighlightSpeciesAction",
                "FilterAction",
                "CameraFlyToAction",
            ],
            Field(discriminator="type"),
        ]
    ] = []
    route: str
    citations: list[dict] = []


class HighlightSpeciesAction(BaseModel):
    type: Literal["highlight_species"] = "highlight_species"
    species_ids: list[str] = []
    species_names: list[str] = []


class FilterAction(BaseModel):
    type: Literal["filter"] = "filter"
    regions: list[str] | None = None
    habitats: list[str] | None = None
    diets: list[str] | None = None
    species_ids: list[str] | None = None
    species_names: list[str] | None = None


class CameraFlyToAction(BaseModel):
    type: Literal["camera_fly_to"] = "camera_fly_to"
    latitude: float
    longitude: float
    altitude: float | None = None
    duration_ms: int | None = None


@router.post("/query", response_model=QueryResponse)
def query(req: QueryRequest, nlp: NlpService = Depends(get_nlp_service)) -> QueryResponse:
    result = nlp.qa.answer(query=req.query, top_k=req.top_k)
    citations = [
        {
            "id": h.species.id,
            "species_name": h.species.species_name,
            "region": h.species.region,
            "habitat": h.species.habitat,
            "diet": h.species.diet,
            "latitude": h.species.latitude,
            "longitude": h.species.longitude,
            "score": h.score,
        }
        for h in result.hits
    ]
    return QueryResponse(
        answer=result.answer,
        map_actions=result.map_actions,
        route=result.route,
        citations=citations,
    )

