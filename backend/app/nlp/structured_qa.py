from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.nlp.llm.deepseek_client import DeepSeekClient
from app.nlp.llm.prompt import build_system_prompt, build_user_prompt
from app.nlp.vector_index import RetrievalHit, SpeciesVectorIndex


@dataclass
class StructuredResult:
    answer: str
    route: str
    hits: list[RetrievalHit]
    map_actions: list[dict[str, Any]]


class StructuredRagQa:
    """
    RAG（本地向量检索）+ LLM（DeepSeek）：
    - hits: 供前端引用/调试
    - map_actions: 供前端 3D 世界执行
    """

    def __init__(self, *, index: SpeciesVectorIndex, llm: DeepSeekClient | None):
        self.index = index
        self.llm = llm

    def answer(self, query: str, top_k: int = 5) -> StructuredResult:
        hits = self.index.search(query=query, top_k=top_k)
        if not hits:
            return StructuredResult(
                answer="没有在当前数据集中找到足够相关的信息。",
                route="rag_vector_search",
                hits=[],
                map_actions=[],
            )

        knowledge = [self._hit_to_knowledge(h) for h in hits]

        if self.llm is None:
            # 降级：无外部 LLM key 时，仍返回可用的结构化结果（最相关物种高亮+飞行）
            best = hits[0].species
            return StructuredResult(
                answer=self._fallback_answer(hits),
                route="rag_vector_search_fallback_no_llm",
                hits=hits,
                map_actions=[
                    {"type": "highlight_species", "species_ids": [best.id], "species_names": [best.species_name]},
                    {"type": "camera_fly_to", "latitude": best.latitude, "longitude": best.longitude, "altitude": 2.5, "duration_ms": 1200},
                ],
            )

        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(question=query, knowledge=knowledge)

        try:
            out = self.llm.chat_json(system_prompt=system_prompt, user_prompt=user_prompt)
            validated = _validate_llm_json(out)
            return StructuredResult(
                answer=validated["answer"],
                route="rag_vector_search_deepseek_json",
                hits=hits,
                map_actions=validated["map_actions"],
            )
        except Exception:
            best = hits[0].species
            return StructuredResult(
                answer=self._fallback_answer(hits),
                route="rag_vector_search_fallback_llm_error",
                hits=hits,
                map_actions=[
                    {"type": "highlight_species", "species_ids": [best.id], "species_names": [best.species_name]},
                    {"type": "camera_fly_to", "latitude": best.latitude, "longitude": best.longitude, "altitude": 2.5, "duration_ms": 1200},
                ],
            )

    @staticmethod
    def _hit_to_knowledge(h: RetrievalHit) -> dict[str, Any]:
        s = h.species
        return {
            "score": h.score,
            "species": {
                "id": s.id,
                "species_name": s.species_name,
                "region": s.region,
                "habitat": s.habitat,
                "diet": s.diet,
                "description": s.description,
                "latitude": s.latitude,
                "longitude": s.longitude,
            },
        }

    @staticmethod
    def _fallback_answer(hits: list[RetrievalHit]) -> str:
        best = hits[0].species
        lines = [
            f"最相关物种：{best.species_name}",
            f"区域：{best.region}；栖息地：{best.habitat}；食性：{best.diet}",
            f"描述：{best.description}",
        ]
        if len(hits) > 1:
            related = "、".join(h.species.species_name for h in hits[1: min(5, len(hits))])
            lines.append(f"其它相关：{related}")
        return "\n".join(lines)


def _validate_llm_json(obj: Any) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise ValueError("LLM output must be a JSON object.")
    if "answer" not in obj or "map_actions" not in obj:
        raise ValueError("LLM output must contain keys: answer, map_actions.")
    answer = obj["answer"]
    actions = obj["map_actions"]
    if not isinstance(answer, str):
        raise ValueError("answer must be a string.")
    if not isinstance(actions, list):
        raise ValueError("map_actions must be a list.")

    validated_actions: list[dict[str, Any]] = []
    for a in actions:
        if not isinstance(a, dict):
            continue
        t = a.get("type")
        if t not in {"highlight_species", "filter", "camera_fly_to"}:
            continue
        if t == "camera_fly_to":
            if not isinstance(a.get("latitude"), (int, float)) or not isinstance(a.get("longitude"), (int, float)):
                continue
        validated_actions.append(a)

    return {"answer": answer, "map_actions": validated_actions}

