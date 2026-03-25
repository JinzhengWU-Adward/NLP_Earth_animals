from __future__ import annotations

from dataclasses import dataclass

from app.nlp.vector_index import RetrievalHit, SpeciesVectorIndex


@dataclass
class RagResult:
    answer: str
    route: str
    hits: list[RetrievalHit]


class SimpleRagQa:
    """
    MVP 版本：不依赖外部 LLM。
    - 用向量检索找相关物种
    - 用轻量模板把结构化信息拼成“可读答案”
    """

    def __init__(self, index: SpeciesVectorIndex):
        self.index = index

    def answer(self, query: str, top_k: int = 5) -> RagResult:
        hits = self.index.search(query=query, top_k=top_k)
        if not hits:
            return RagResult(
                answer="没有在当前MVP数据集中找到足够相关的信息。",
                route="rag_vector_search",
                hits=[],
            )

        best = hits[0].species
        lines = [
            f"最相关物种：{best.species_name}",
            f"区域：{best.region}；栖息地：{best.habitat}；食性：{best.diet}",
            f"描述：{best.description}",
        ]

        # 额外给出若干相关物种，便于前端展示与用户追问
        if len(hits) > 1:
            related = "、".join(h.species.species_name for h in hits[1: min(5, len(hits))])
            lines.append(f"其它相关：{related}")

        return RagResult(answer="\n".join(lines), route="rag_vector_search", hits=hits)

