from __future__ import annotations

from dataclasses import dataclass

from app.models.species import Species
from app.core.config import settings
from app.nlp.embedder import build_embedder
from app.nlp.llm.deepseek_client import DeepSeekClient, DeepSeekConfig
from app.nlp.structured_qa import StructuredRagQa
from app.nlp.vector_index import SpeciesVectorIndex


@dataclass
class NlpService:
    index: SpeciesVectorIndex
    qa: StructuredRagQa

    @classmethod
    def build(cls, species: list[Species]) -> "NlpService":
        embedder = build_embedder()
        index = SpeciesVectorIndex(embedder=embedder)
        index.build(species)
        llm = None
        if settings.deepseek_api_key:
            llm = DeepSeekClient(
                DeepSeekConfig(
                    api_key=settings.deepseek_api_key,
                    base_url=settings.deepseek_base_url,
                    model=settings.deepseek_model,
                    timeout_s=settings.deepseek_timeout_s,
                    max_tokens=settings.deepseek_max_tokens,
                )
            )
        qa = StructuredRagQa(index=index, llm=llm)
        return cls(index=index, qa=qa)

