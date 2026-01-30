# RAG 智能工程知识问答系统

> **Enterprise RAG System** - 基于 Milvus + PostgreSQL + Redis + Neo4j + 大模型的私有化 RAG 问答系统
> 支持 **智能问答** + **Agent 智能分析** + **知识图谱** + **施工图处理**

---

## 目录

- [技术栈](#技术栈)
- [核心功能](#核心功能)
- [系统架构](#系统架构)
- [目录结构](#目录结构)
- [快速启动](#快速启动)
- [Agent 智能分析模块](#agent-智能分析模块)
- [知识图谱模块](#知识图谱模块)
- [API 接口](#api-接口)
- [RAG 问答流程](#rag-问答流程)
- [配置说明](#配置说明)
- [适用场景](#适用场景)

---

## 技术栈

| 类别 | 技术 | 说明 |
|------|------|------|
| **Web框架** | FastAPI | 高性能异步 API 框架 |
| **ORM** | SQLAlchemy 2.0 | 数据库操作 |
| **关系数据库** | PostgreSQL 15 | 文档元数据、用户、日志 |
| **向量数据库** | Milvus 2.3 | 文档向量存储与检索 |
| **图数据库** | Neo4j 5.0 | 知识图谱存储与查询 |
| **缓存** | Redis 7 | Query 缓存、会话管理 |
| **大模型** | OpenAI / Qwen / GLM / Ollama | 可替换的 LLM 接口 |
| **向量化** | BGE / text2vec / OpenAI | Embedding 模型 |
| **OCR** | PaddleOCR | 扫描件文字识别 |
| **容器化** | Docker Compose | 一键部署 |

---

## 核心功能

### 1. 文档处理（Document Pipeline）

| 功能 | 说明 |
|------|------|
| **格式支持** | PDF、Word（.doc/.docx）、扫描件（OCR）、文本 |
| **处理流程** | 加载 → 解析 → 清洗 → 分块 → 向量化 |
| **元数据管理** | 自动提取标题、作者、日期等信息 |

### 2. 向量化（Embedding）

- 支持批量文本向量生成
- 向量与 Chunk 元数据解耦存储
- 可替换不同 Embedding 模型（BGE / text2vec / OpenAI）

### 3. 检索系统（Retrieval）

| 检索方式 | 说明 |
|----------|------|
| **向量检索** | 基于 Milvus，支持 TopK、相似度阈值 |
| **关键词检索** | 基于 BM25，提升专业术语召回率 |
| **混合检索** | 向量 + BM25 结果合并、去重、加权 |
| **图增强检索** | 结合知识图谱的语义检索 |
| **重排序** | Cross-Encoder 精排，减少无关上下文 |

### 4. 大模型生成（LLM）

- Prompt 模板化管理
- 强约束回答来源：未检索到内容 → 明确返回「文档中未找到」
- 支持私有化模型和云端 API
- 支持 OpenAI / 通义千问 / 智谱GLM / Ollama / vLLM

### 5. 缓存与日志

| 组件 | 用途 |
|------|------|
| **Redis** | Query → Answer 缓存，降低 LLM 调用成本 |
| **PostgreSQL** | 文档信息、Chunk 元数据、问答日志 |

### 6. Agent 智能分析

| Agent | 功能 | 核心指标 |
|-------|------|----------|
| **WeeklyReportAgent** | 自动生成项目周报 | 进度、成本、风险汇总 |
| **RiskAnalysisAgent** | 风险识别与预警 | 多维度风险评估 |
| **CostAnalysisAgent** | 成本分析与预测 | CPI、EAC、超支识别 |
| **ProgressAnalysisAgent** | 进度分析与预测 | SPI、延期预警、完工预测 |
| **SafetyAnalysisAgent** | 安全合规分析 | 合格率、隐患统计、整改计划 |

### 7. 知识图谱

| 功能 | 说明 |
|------|------|
| **实体提取** | 从文档中提取结构化实体 |
| **关系抽取** | 识别实体间的关联关系 |
| **图谱存储** | Neo4j 图数据库存储 |
| **图谱查询** | 支持路径查找、邻居查询 |
| **图增强RAG** | 结合图谱进行语义增强检索 |

### 8. 施工图处理

| 功能 | 说明 |
|------|------|
| **图纸解析** | 解析施工图纸文件 |
| **实体提取** | 提取图纸中的构件、材料、尺寸等 |
| **关系抽取** | 识别构件间的连接和包含关系 |
| **知识入图** | 将图纸信息存入知识图谱 |

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Client (Web / API)                            │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────┐
│                        FastAPI API Layer                             │
│  ┌───────┐ ┌────────┐ ┌───────┐ ┌────────┐ ┌───────┐ ┌───────────┐ │
│  │  /qa  │ │/document│ │/admin │ │/agents │ │/graph │ │ /drawing  │ │
│  └───────┘ └────────┘ └───────┘ └────────┘ └───────┘ └───────────┘ │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────┐
│                        Business Layer                                │
│  ┌─────────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │    RAG Pipeline     │  │ Agent Orchestra  │  │  Graph Service │  │
│  │ Query→Retrieve→     │  │ Weekly│Risk│Cost │  │ Entity│Relation│  │
│  │ Rerank→Generate     │  │ Progress│Safety  │  │  Query│Path    │  │
│  └─────────────────────┘  └──────────────────┘  └────────────────┘  │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────┐
│                        Service Layer                                 │
│  Document │ Embedding │ Retrieval │ LLM │ Cache │ Graph │ Drawing   │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────┐
│                        Infrastructure                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │PostgreSQL│ │  Milvus  │ │  Redis   │ │  Neo4j   │ │ LLM API  │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 目录结构

```
enterprise_rag/
├── app/                           # 主应用
│   ├── main.py                    # 项目入口
│   ├── api/v1/                    # API 接口层
│   │   ├── qa.py                  # 问答接口
│   │   ├── document.py            # 文档管理接口
│   │   ├── admin.py               # 管理接口
│   │   ├── projects.py            # 项目管理接口
│   │   ├── drawing.py             # 施工图处理接口
│   │   └── graph.py               # 知识图谱接口
│   └── schemas/                   # Pydantic 模型
│
├── agents/                        # Agent 智能分析模块
│   ├── weekly_report_agent.py     # 周报生成 Agent
│   ├── risk_agent.py              # 风险分析 Agent
│   ├── cost_agent.py              # 成本分析 Agent
│   ├── progress_agent.py          # 进度分析 Agent
│   ├── safety_agent.py            # 安全分析 Agent
│   └── api/v1/agents.py           # Agent API 路由
│
├── tools/                         # 专业分析工具
│   ├── cost_tools.py              # 成本分析工具（8个）
│   ├── progress_tools.py          # 进度分析工具（8个）
│   ├── safety_tools.py            # 安全分析工具（9个）
│   └── rag_tool.py                # RAG 检索工具
│
├── core/                          # 核心模块
│   ├── config.py                  # 配置中心
│   ├── logger.py                  # 日志管理
│   ├── database.py                # 数据库连接
│   ├── constants.py               # 全局常量
│   └── security.py                # 安全工具
│
├── models/                        # 数据模型
│   ├── document.py                # 文档模型
│   ├── project.py                 # 项目模型
│   ├── query.py                   # 查询模型
│   ├── user.py                    # 用户模型
│   ├── construction_drawing.py    # 施工图模型
│   └── graph_models.py            # 图数据模型
│
├── services/                      # 核心业务服务
│   ├── document/                  # 文档处理子系统
│   │   └── construction_drawing/  # 施工图处理
│   ├── embedding/                 # 向量化子系统
│   ├── retrieval/                 # 检索子系统
│   │   ├── vector/                # 向量检索
│   │   ├── bm25/                  # BM25检索
│   │   ├── hybrid/                # 混合检索
│   │   └── graph/                 # 图增强检索
│   ├── llm/                       # LLM 子系统
│   ├── cache/                     # 缓存子系统
│   ├── graph/                     # 知识图谱服务
│   ├── rag/                       # RAG Pipeline
│   ├── permission/                # 权限管理
│   └── project_service.py         # 项目服务
│
├── repository/                    # 数据访问层
│   ├── document_repo.py           # 文档 DAO
│   ├── vector_repo.py             # 向量 DAO
│   ├── query_log_repo.py          # 日志 DAO
│   └── graph_repo.py              # 图数据 DAO
│
├── docker/                        # Docker 配置
│   └── docker-compose.yml         # 一键部署配置
│
├── scripts/                       # 辅助脚本
│   ├── init_db.py                 # 数据库初始化
│   ├── init_milvus.py             # Milvus 初始化
│   └── ingest_docs.py             # 文档入库
│
├── tests/                         # 测试用例
│   ├── test_agents.py             # Agent 测试
│   └── test_agents_api.py         # API 测试
│
├── docs/                          # 项目文档
│   └── DEPLOYMENT_GUIDE.md        # 部署指南
│
├── .env                           # 环境变量配置
├── requirements.txt               # Python 依赖
└── README.md                      # 项目说明
```

---

## 快速启动

### 环境要求

- Windows / Linux / macOS
- Docker & Docker Compose
- Python >= 3.9

### 1. 启动基础服务

```bash
cd docker
docker-compose up -d
```

启动服务：PostgreSQL、Milvus、Redis、Etcd、MinIO

### 2. 配置 Python 环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活（Windows）
venv\Scripts\activate

# 激活（Linux/Mac）
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 编辑 .env 文件，配置数据库和 LLM API
```

主要配置项：
- `POSTGRES_PASSWORD` - 数据库密码
- `OPENAI_API_KEY` - LLM API 密钥
- `OPENAI_API_BASE` - LLM API 地址
- `NEO4J_PASSWORD` - 图数据库密码（如使用知识图谱）

### 4. 初始化数据库

```bash
python scripts/init_db.py
```

### 5. 启动 API 服务

```bash
# 开发模式
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 6. 访问系统

- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **系统信息**: http://localhost:8000/info

> 详细部署说明请参考 [部署指南](docs/DEPLOYMENT_GUIDE.md)

---

## Agent 智能分析模块

### Agent 列表

| Agent | 端点 | 功能 |
|-------|------|------|
| **成本分析** | `POST /api/v1/agents/cost-analysis` | CPI计算、超支识别、成本预测 |
| **进度分析** | `POST /api/v1/agents/progress-analysis` | SPI计算、延期预警、完工预测 |
| **安全分析** | `POST /api/v1/agents/safety-analysis` | 合格率、隐患统计、整改计划 |
| **风险分析** | `POST /api/v1/agents/risk-analysis` | 多维度风险评估 |
| **周报生成** | `POST /api/v1/agents/weekly-report` | 自动周报生成 |

### 快速检查接口

```bash
# 成本快速检查
GET /api/v1/agents/cost-analysis/{project_id}/quick-check

# 进度快速检查
GET /api/v1/agents/progress-analysis/{project_id}/quick-check

# 安全快速检查
GET /api/v1/agents/safety-analysis/{project_id}/quick-check

# 风险快速扫描
GET /api/v1/agents/risk-analysis/{project_id}/quick-scan

# 项目仪表盘（综合概览）
GET /api/v1/agents/dashboard/{project_id}
```

### 使用示例

```python
import requests

# 成本分析
response = requests.post(
    "http://localhost:8000/api/v1/agents/cost-analysis",
    json={
        "project_id": "P001",
        "analysis_months": 3,
        "include_prediction": True
    }
)
print(response.json())

# 项目仪表盘
response = requests.get(
    "http://localhost:8000/api/v1/agents/dashboard/P001"
)
print(response.json())
```

### 关键指标说明

| 指标 | 计算公式 | 判定标准 |
|------|----------|----------|
| **CPI** (成本绩效指数) | 挣值 / 实际成本 | >1 节约, <0.9 超支 |
| **SPI** (进度绩效指数) | 挣值 / 计划值 | >1 超前, <0.9 滞后 |
| **合格率** | 合格数 / 总检查数 | >=95% 良好, <90% 风险 |

---

## 知识图谱模块

### 功能概述

知识图谱模块基于 Neo4j 图数据库，支持从文档和施工图中提取结构化知识，并提供图谱查询和图增强检索能力。

### API 端点

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/v1/graph/nodes` | 查询节点 |
| GET | `/api/v1/graph/relationships` | 查询关系 |
| GET | `/api/v1/graph/paths` | 路径查找 |
| GET | `/api/v1/graph/stats` | 图谱统计 |

### 施工图处理 API

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/v1/drawing/upload` | 上传施工图 |
| GET | `/api/v1/drawing/status` | 处理状态查询 |
| GET | `/api/v1/drawing/entities/{id}` | 获取提取的实体 |

### 节点类型

| 类型 | 说明 |
|------|------|
| Document | 文档节点 |
| Drawing | 图纸节点 |
| Component | 构件节点 |
| Material | 材料节点 |
| Specification | 规范节点 |
| Dimension | 尺寸节点 |
| Location | 位置节点 |

### 关系类型

| 关系 | 说明 |
|------|------|
| CONTAINS | 包含关系 |
| USES_MATERIAL | 使用材料 |
| REFERS_TO | 引用关系 |
| HAS_DIMENSION | 具有尺寸 |
| LOCATED_AT | 位于位置 |
| CONNECTED_TO | 连接关系 |
| BELONGS_TO | 属于关系 |

---

## API 接口

### 接口总览

| 模块 | 前缀 | 说明 |
|------|------|------|
| **问答** | `/api/v1/qa` | RAG 智能问答 |
| **文档** | `/api/v1/document` | 文档上传/管理 |
| **项目** | `/api/v1/projects` | 项目 CRUD |
| **Agent** | `/api/v1/agents` | 智能分析 |
| **图谱** | `/api/v1/graph` | 知识图谱查询 |
| **施工图** | `/api/v1/drawing` | 施工图处理 |
| **管理** | `/api/v1/admin` | 系统管理 |

### Agent API 详细

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/agents/weekly-report` | 生成周报 |
| POST | `/agents/risk-analysis` | 风险分析 |
| GET | `/agents/risk-analysis/{id}/quick-scan` | 快速风险扫描 |
| POST | `/agents/cost-analysis` | 成本分析 |
| GET | `/agents/cost-analysis/{id}/quick-check` | 快速成本检查 |
| POST | `/agents/progress-analysis` | 进度分析 |
| GET | `/agents/progress-analysis/{id}/quick-check` | 快速进度检查 |
| POST | `/agents/safety-analysis` | 安全分析 |
| GET | `/agents/safety-analysis/{id}/quick-check` | 快速安全检查 |
| GET | `/agents/dashboard/{id}` | 项目仪表盘 |
| GET | `/agents/workflows` | 工作流列表 |
| GET | `/agents/workflows/{log_id}` | 工作流详情 |

---

## RAG 问答流程

```
用户提问
   ↓
Query 预处理（分词、意图识别）
   ↓
混合检索（向量检索 + BM25 + 图增强）
   ↓
Rerank 精排（Cross-Encoder）
   ↓
构造 Prompt（仅使用检索内容）
   ↓
LLM 生成答案
   ↓
缓存 & 日志记录
```

**关键设计点：**

- 没检索到内容 → 不调用 LLM，明确告知用户
- Prompt 明确限制模型不得编造
- 检索与生成完全解耦，便于扩展 Agent
- 图增强检索提供更丰富的上下文

---

## 配置说明

### 环境变量 (.env)

```env
# 应用配置
APP_NAME=Enterprise RAG System
DEBUG=false
ENVIRONMENT=production

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=rag_user
POSTGRES_PASSWORD=your_secure_password

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Neo4j（知识图谱）
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# LLM
OPENAI_API_KEY=your-api-key
OPENAI_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo

# Embedding
EMBEDDING_MODEL_NAME=BAAI/bge-large-zh-v1.5
```

### Docker 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| FastAPI | 8000 | API 服务 |
| PostgreSQL | 5432 | 关系数据库 |
| Milvus | 19530 | 向量数据库 |
| Redis | 6379 | 缓存 |
| Neo4j | 7687 | 图数据库 |
| MinIO | 9000/9001 | 对象存储 |

---

## 适用场景

- 企业内部知识库
- 工程 / 运维 / 法律 / 制度问答
- 私有文档智能检索
- 项目管理智能分析
- 施工图纸知识管理
- 私有化大模型应用

---

## 扩展方向

- 多知识库 / 多租户
- SSO / 权限控制
- Query 质量评估与自动调优
- 微调 / RAG 评测闭环
- 更多 Agent 扩展
- 流式输出支持

---

## 相关文档

- [部署指南](docs/DEPLOYMENT_GUIDE.md)

---

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.2.0 | 2026-01 | 新增知识图谱模块、施工图处理、权限管理 |
| v1.1.0 | 2025 | 新增 Agent 智能分析模块（成本/进度/安全） |
| v1.0.0 | 2025 | 初始版本，RAG 问答系统 |

---

## License

MIT License

---

**Made with by Kerro**
