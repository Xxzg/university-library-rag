# 高校图书馆馆藏文献智能问答系统

基于 **LangChain + RAG** 的检索增强生成系统，面向高校图书馆纸质书与电子文献的检索痛点，解决传统关键词检索无法精准定位文献片段、无法直接返回自然语言答案的问题。

## 一、系统架构

```
① 离线索引管线（数据准备）        ② 在线问答链路（RAG）
馆藏文献 → 批量解析 → 文档切分 → 向量化入库 → 向量数据库
                                              ↑ 检索召回
              用户提问 → 历史改写 → 检索 → 重排 → LLM 生成 → 溯源回答
③ 系统功能层：内容溯源标注 / 问答历史管理 / 角色权限分配（RBAC）
```

### 技术栈

| 层 | 技术 |
|----|------|
| 后端 | FastAPI + SQLAlchemy + SQLite + JWT |
| 检索增强 | LangChain + Chroma（向量库）+ OpenAI 兼容 Embedding/Rerank |
| 大模型 | OpenAI 兼容接口（默认硅基流动，可切本地 Ollama） |
| 前端 | Vue 3 + Vite + Element Plus + Pinia + Vue Router |
| 文献解析 | PyMuPDF（PDF）+ python-docx（Word）|

## 二、目录结构

```
backend/
├── app/
│   ├── main.py              FastAPI 入口
│   ├── config.py            配置加载（.env）
│   ├── database.py          SQLAlchemy 引擎
│   ├── models.py            ORM 模型（用户/文献/会话/消息）
│   ├── schemas.py           Pydantic 模型
│   ├── auth.py              JWT + PBKDF2 + RBAC 三级角色
│   ├── routers/             路由（auth/users/documents/sessions/chat）
│   └── services/
│       ├── vectorstore.py   Chroma + Embedding 封装
│       ├── ingestion.py     文献解析→切分→向量化→入库
│       └── rag.py           多轮改写→检索→重排→流式生成→溯源
├── scripts/
│   ├── seed.py              初始化演示账号
│   ├── gen_test_docs.py     生成模拟馆藏文献（5 份）
│   ├── test_e2e.sh          端到端联调脚本
│   └── evaluate.py          RAG 准确率评测脚本
├── data/                    SQLite + Chroma + 测试文献
├── requirements.txt
└── .env / .env.example

frontend/  Vue3 前端（src/{views,layouts,router,api,stores}）
```

## 三、三个核心功能

1. **文献内容溯源标注**：每个 chunk 元数据携带书名/页码，LLM 生成答案时标注 `[1][2]` 引用编号，前端渲染为可点击的溯源卡片。
2. **问答历史管理**：会话与消息持久化到 SQLite，支持多轮对话上下文恢复、重命名、删除，按用户隔离。
3. **角色权限分配**：学生（问答+历史）/ 教师（+文献上传）/ 管理员（+用户管理）三级 RBAC，JWT 鉴权。

## 四、快速启动

### 后端

```bash
cd backend
python -m venv venv
venv/Scripts/python.exe -m pip install -r requirements.txt
# 配置 .env（复制 .env.example，填入 API Key）
venv/Scripts/python.exe scripts/seed.py          # 初始化账号
venv/Scripts/python.exe scripts/gen_test_docs.py # 生成测试文献
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

## 五、模型接入（可切换）

`.env` 中配置，全部走 OpenAI 兼容接口，切换厂商无需改代码：

| 接入方式 | LLM_API_BASE | LLM_MODEL | EMBEDDING_MODEL |
|----------|--------------|-----------|-----------------|
| 硅基流动（推荐） | https://api.siliconflow.cn/v1 | THUDM/GLM-4-9B-0414 | BAAI/bge-m3 |
| 本地 Ollama | http://localhost:11434/v1 | qwen3:8b | bge-m3 |

**临时用本地 Ollama 跑联调**（无需 API Key）：

```bash
# 先拉取 embedding 模型（约 1.2GB）
ollama pull bge-m3
# 环境变量覆盖启动（不污染 .env）
LLM_API_BASE=http://localhost:11434/v1 LLM_API_KEY=ollama \
LLM_MODEL=qwen3:8b EMBEDDING_MODEL=bge-m3 RERANK_MODEL= \
uvicorn app.main:app --port 8000
```

## 六、演示账号

| 用户名 | 密码 | 角色 | 权限 |
|--------|------|------|------|
| admin | admin123 | 管理员 | 全部 + 用户管理 |
| teacher | teacher123 | 教师 | + 文献上传/删除 |
| student | student123 | 学生 | 问答 + 历史 |
