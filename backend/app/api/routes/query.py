from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter

router = APIRouter()


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)


class QueryResponse(BaseModel):
    answer: str
    route: str
    citations: list[dict] = []


@router.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    # MVP 占位：后续会接入向量检索（RAG）与知识图谱查询，并由 router/agent 决策。
    return QueryResponse(
        answer=f"收到你的问题：{req.query}（当前为MVP占位回答）",
        route="stub",
        citations=[],
    )

