from __future__ import annotations

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
    route: str
    citations: list[dict] = []


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
    return QueryResponse(answer=result.answer, route=result.route, citations=citations)

