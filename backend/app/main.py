from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.query import router as query_router
from app.api.routes.species import router as species_router
from app.core.config import settings


app = FastAPI(title=settings.project_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(species_router)
app.include_router(query_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

