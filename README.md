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

## `/query` 处理流程（当前代码实现）

后端当前实现的是“**本地向量检索（FAISS）+ 可选 LLM（DeepSeek JSON mode）**”的结构化 RAG。

### 1) 启动时预热：构建向量索引

服务启动后会在 `startup` 阶段预热（避免第一次查询卡顿）：

- `backend/app/main.py` 在启动时调用 `get_nlp_service()`
- `backend/app/services/wiring.py` 里用 `lru_cache(maxsize=1)` 缓存单例：
  - `SpeciesStore(settings.data_path)` 读取 `data/species.json`
  - `NlpService.build(store.all())` 构建 NLP 服务

`NlpService.build()` 做的事：

- **Embedder 选择**：`backend/app/nlp/embedder.py`
  - 优先 `sentence-transformers/all-MiniLM-L6-v2`（需要安装 `requirements-ml.txt`）
  - 不可用时自动回退为 **TF-IDF**（轻量，保证 MVP 可跑）
- **向量索引构建**：`backend/app/nlp/vector_index.py`
  - 把每个物种拼成可检索“文档文本”（包含 `species_name/region/habitat/diet/description`）
  - 生成 embeddings（必要时 TF-IDF 会先 `fit`）
  - 用 `faiss.IndexFlatIP` 建索引（因为 embeddings 已做 normalize，所以 inner product 等价余弦相似度）

### 2) 请求进入 `/query`：先检索，再生成结构化输出

接口入口：`backend/app/api/routes/query.py`

- 调用：`nlp.qa.answer(query=req.query, top_k=req.top_k)`
- 返回：`answer + map_actions + route`，并附带 `citations`（命中的物种及相似度 score）

问答核心：`backend/app/nlp/structured_qa.py`

- **Step A：向量检索**：`index.search(query, top_k)` 得到 `hits`
- **Step B：组装 knowledge**：把 hits 的结构化字段整理为 LLM 可用的上下文
- **Step C：生成答案与地图动作**：
  - **如果未配置 `DEEPSEEK_API_KEY`**：走本地降级策略
    - 返回基于最相关物种的简短回答
    - `map_actions` 默认输出：`highlight_species + camera_fly_to`
  - **如果配置了 `DEEPSEEK_API_KEY`**：
    - 用 `backend/app/nlp/llm/prompt.py` 的 system/user prompt 约束 LLM **只输出严格 JSON**
    - 对 JSON 做校验与清洗，只保留合法 `map_actions`（`highlight_species` / `filter` / `camera_fly_to`）
    - 如果 LLM 调用失败/输出不合法：自动回退到本地降级策略

### 3) 数据更新对 RAG 的影响（很重要）

当前实现里 `SpeciesStore` 与 `NlpService` 都是 **进程内缓存单例**（`lru_cache`），向量索引只在构建时生成一次。

- **你新增/修改了 `data/species.json` 后**：
  - **需要重启后端进程**，让它重新加载数据并 `index.build(...)` 重建向量索引
  - 这不是“训练模型”，而是 **重新计算 embeddings 并重建索引**

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

