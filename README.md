# GeoBioMap：全球生物多样性知识图谱 + NLP 问答（MVP）

GeoBioMap 是一个最小可用产品（MVP），用于：

- 在 3D 地球上展示物种地理分布（前端：React + Three.js）
- 提供物种数据浏览与点击查看
- 支持自然语言提问（后端：FastAPI），后续将接入：
  - 信息抽取（IE）
  - 向量检索（Embeddings + FAISS/Chroma）
  - 知识图谱查询（Neo4j 或 NetworkX）
  - （可选）简单路由 agent

## 目录结构

```text
GeoBioMap/
  backend/                 # FastAPI + NLP/图谱模块
  frontend/                # React + Three.js 3D 地球
  data/                    # MVP 数据集（JSON）
```

## 先跑起来（当前阶段：数据集 + 后端骨架）

### 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

（可选）启用更强语义检索（会安装较大的 torch 依赖）：

```bash
pip install -r requirements-ml.txt
```

访问：

- `GET http://localhost:8000/health`
- `GET http://localhost:8000/species`

## API（MVP）

- `GET /species`：返回全部物种条目（来自 `data/species.json`）
- `POST /query`：NLP 查询入口（当前为占位；后续接入 RAG/图谱路由）

