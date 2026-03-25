# 数据集（MVP）

`species.json` 包含一组小而有信息量的物种样本（约 50–200 条），用于驱动：

- 前端地球点位渲染（`latitude`/`longitude`）
- 后端 `/species` 列表接口
- 后续的向量检索与 RAG（使用 `description` 字段做 embedding）

