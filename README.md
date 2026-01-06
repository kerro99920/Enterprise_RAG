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
```
enterprise_rag/
├── app/
│ ├── main.py                # 项目入口
│ ├── api/                   # API 接口
│ │ └── v1/
│ │ ├── qa.py                    # 问答接口
│ │ ├── document.py              # 文档上传 / 管理接口
│ │ └── admin.py                 # 管理接口（预留）
│ │
│ ├── core/                      # 核心模块
│ │ ├── config.py                # 配置中心
│ │ ├── logger.py                # 日志管理
│ │ ├── security.py              # 权限 / SSO（预留）
│ │ └── constants.py             # 全局常量
│ │
│ ├── services/                  # 核心业务服务
│ │ ├── document/                # 文档处理子系统
│ │ │ ├── loader.py              # 文档加载调度
│ │ │ ├── pdf_parser.py          # PDF 解析
│ │ │ ├── word_parser.py         # Word 解析
│ │ │ ├── ocr_parser.py          # OCR 文字识别
│ │ │ ├── cleaner.py             # 文本清洗
│ │ │ ├── splitter.py            # 文档切分为 Chunk
│ │ │ └── metadata.py            # 元数据封装
│ │ │
│ │ ├── embedding/               # 向量化子系统
│ │ │ ├── embedding_model.py     # 模型加载
│ │ │ └── embedder.py            # 批量向量生成
│ │ │
│ │ ├── retrieval/               # 检索子系统（RAG 核心）
│ │ │ ├── bm25/                  # BM25 检索
│ │ │ │ └── bm25_engine.py
│ │ │ ├── vector/                # 向量检索
│ │ │ │ ├── milvus_client.py
│ │ │ │ └── vector_engine.py
│ │ │ ├── rerank/                # 重排序
│ │ │ │ └── reranker.py
│ │ │ └── hybrid_retriever.py    # 混合检索入口
│ │ │
│ │ ├── llm/                     # 大模型子系统
│ │ │ ├── prompt/
│ │ │ │ ├── base_prompt.py
│ │ │ │ └── qa_prompt.py
│ │ │ ├── llm_client.py
│ │ │ └── generator.py
│ │ │
│ │ ├── permission/             # 权限子系统（预留）
│ │ │ └── permission_checker.py
│ │ │
│ │ └── cache/                  # 缓存子系统
│ │ └── redis_client.py
│ │
│ ├── models/                   # 数据模型
│ │ ├── document.py             # 文档 / Chunk 模型
│ │ ├── query.py                # Query / Response 模型
│ │ └── user.py
│ │
│ ├── repository/               # 数据访问层（DAO）
│ │ ├── document_repo.py
│ │ ├── vector_repo.py
│ │ └── query_log_repo.py
│ │
│ └── utils/                    # 工具函数
│ ├── file_utils.py
│ ├── text_utils.py
│ └── hash_utils.py
│
├── docker/                     # 容器相关
│ ├── docker-compose.yml
│ └── milvus/
│
├── data/                       # 数据目录
│ ├── raw_docs/                 # 原始文档
│ └── processed/                # 处理后的中间数据
│
├── scripts/                    # 辅助脚本
│ ├── init_milvus.py
│ ├── ingest_docs.py
│ └── rebuild_index.py
│
├── tests/                      # 测试用例
│
├── .env                        # 环境变量配置
├── requirements.txt            # Python 依赖
└── README.md
```

