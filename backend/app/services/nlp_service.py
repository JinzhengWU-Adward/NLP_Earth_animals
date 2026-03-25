from __future__ import annotations

from dataclasses import dataclass

from app.models.species import Species
from app.nlp.embedder import build_embedder
from app.nlp.rag import SimpleRagQa
from app.nlp.vector_index import SpeciesVectorIndex


@dataclass
class NlpService:
    index: SpeciesVectorIndex
    qa: SimpleRagQa

    @classmethod
    def build(cls, species: list[Species]) -> "NlpService":
        embedder = build_embedder()
        index = SpeciesVectorIndex(embedder=embedder)
        index.build(species)
        qa = SimpleRagQa(index=index)
        return cls(index=index, qa=qa)

