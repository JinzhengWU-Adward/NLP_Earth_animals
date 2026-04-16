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
- `POST /query`：NLP 查询入口（RAG + 可选 DeepSeek 结构化输出）

### DeepSeek 配置（可选）

如果你希望 `/query` 使用 DeepSeek 生成结构化回答，请设置环境变量：

```bash
export DEEPSEEK_API_KEY="你的key"
export DEEPSEEK_MODEL="deepseek-chat"          # 可选
export DEEPSEEK_BASE_URL="https://api.deepseek.com"  # 可选
```

未设置 `DEEPSEEK_API_KEY` 时，会自动降级为本地模板回答，并仍返回可用的 `map_actions`（基于最相关物种的高亮+飞行）。

### `/query` 返回格式（关键）

后端会返回一个对象，核心字段为：

```json
{
  "answer": "...",
  "map_actions": [
    {"type": "highlight_species", "species_ids": ["..."], "species_names": ["..."]},
    {"type": "filter", "regions": ["..."]},
    {"type": "camera_fly_to", "latitude": 0, "longitude": 0, "altitude": 2.5, "duration_ms": 1200}
  ]
}
```

### CLI test prompts (English)

These prompts are designed to be copy-pasted into CLI tests and to reliably trigger `map_actions` such as
`highlight_species`, `filter`, and `camera_fly_to`.

#### Quick curl test

```bash
curl -s http://127.0.0.1:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"What is the most relevant species for bamboo forest ecosystems?","top_k":5}' | jq .
```

If you don't have `jq`, just remove the `| jq .`.

#### Prompt templates (copy & edit)

- **Single target (LLM decides actions)**:
  - `What is the most relevant species for: <YOUR TOPIC>?`
  - `Tell me about <SPECIES NAME>.`

- **Multiple candidates / comparison (LLM decides actions)**:
  - `List the top 3 most relevant species for: <YOUR TOPIC>, and briefly compare them.`
  - `Compare <SPECIES A> vs <SPECIES B>.`

- **Region (LLM infers filter)**:
  - `What species are most relevant in region: <REGION>?`
  - `Compare biodiversity between regions: <REGION 1> and <REGION 2>.`

- **Habitat (LLM infers filter)**:
  - `What are the most relevant species in habitat: <HABITAT>?`

- **Diet (LLM infers filter)**:
  - `Show the most relevant Carnivore species.`
  - `In region: <REGION>, what are the most relevant Herbivore species?`

#### Batch test (multiple queries)

```bash
python - <<'PY'
import json, urllib.request

URL = "http://127.0.0.1:8000/query"
queries = [
  "What is the most relevant species for bamboo forest ecosystems?",
  "What species are most relevant in region: Central Asia?",
  "Show the most relevant Carnivore species.",
]

for q in queries:
  data = json.dumps({"query": q, "top_k": 5}).encode("utf-8")
  req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
  with urllib.request.urlopen(req, timeout=15) as resp:
    body = resp.read().decode("utf-8")
  print("\n--- QUERY ---")
  print(q)
  print("--- RESPONSE ---")
  print(body)
PY
```

