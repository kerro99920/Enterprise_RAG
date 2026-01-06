# RAG 智能知识问答系统

Windows + Docker + Python  
基于 Milvus + MySQL + Redis + 大模型的私有化 RAG 问答系统

## 技术栈
- Python
- Docker / Docker Compose
- Milvus
- MySQL
- Redis
- LLM

## 目录结构
enterprise_rag/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── qa.py              # 问答接口
│   │       ├── document.py        # 文档上传 / 管理
│   │       └── admin.py           # 管理接口（预留）
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # 配置中心
│   │   ├── logger.py              # 日志
│   │   ├── security.py            # 权限 / SSO（预留）
│   │   └── constants.py           # 全局常量
│   │
│   ├── services/
│   │   ├── __init__.py
│   │
│   │   ├── document/              # 文档处理子系统
│   │   │   ├── __init__.py
│   │   │   ├── loader.py           # 文档加载调度
│   │   │   ├── pdf_parser.py
│   │   │   ├── word_parser.py
│   │   │   ├── ocr_parser.py
│   │   │   ├── cleaner.py          # 文本清洗
│   │   │   ├── splitter.py         # Chunk 切分
│   │   │   └── metadata.py         # 元数据封装
│   │
│   │   ├── embedding/             # 向量化子系统
│   │   │   ├── __init__.py
│   │   │   ├── embedding_model.py  # 模型加载
│   │   │   └── embedder.py         # 批量向量生成
│   │
│   │   ├── retrieval/             # 检索子系统（RAG 核心）
│   │   │   ├── __init__.py
│   │   │   ├── bm25/
│   │   │   │   ├── __init__.py
│   │   │   │   └── bm25_engine.py
│   │   │   ├── vector/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── milvus_client.py
│   │   │   │   └── vector_engine.py
│   │   │   ├── rerank/
│   │   │   │   ├── __init__.py
│   │   │   │   └── reranker.py
│   │   │   └── hybrid_retriever.py # 混合检索入口
│   │
│   │   ├── llm/                   # 大模型子系统
│   │   │   ├── __init__.py
│   │   │   ├── prompt/
│   │   │   │   ├── base_prompt.py
│   │   │   │   └── qa_prompt.py
│   │   │   ├── llm_client.py
│   │   │   └── generator.py
│   │
│   │   ├── permission/            # 权限子系统（预留）
│   │   │   ├── __init__.py
│   │   │   └── permission_checker.py
│   │
│   │   └── cache/                 # 缓存子系统
│   │       ├── __init__.py
│   │       └── redis_client.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── document.py            # 文档 / Chunk 数据模型
│   │   ├── query.py               # Query / Response 模型
│   │   └── user.py
│   │
│   ├── repository/                # 数据访问层（DAO）
│   │   ├── __init__.py
│   │   ├── document_repo.py
│   │   ├── vector_repo.py
│   │   └── query_log_repo.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── file_utils.py
│       ├── text_utils.py
│       └── hash_utils.py
│
├── docker/
│   ├── docker-compose.yml
│   └── milvus/
│
├── data/
│   ├── raw_docs/                  # 原始文档
│   └── processed/                 # 处理后的中间数据
│
├── scripts/
│   ├── init_milvus.py
│   ├── ingest_docs.py
│   └── rebuild_index.py
│
├── tests/
│
├── .env
├── requirements.txt
└── README.md

