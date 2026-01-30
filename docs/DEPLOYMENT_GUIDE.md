# 企业级 RAG 系统 - 部署指南

## 目录

- [环境要求](#环境要求)
- [快速部署](#快速部署)
- [详细部署步骤](#详细部署步骤)
- [配置说明](#配置说明)
- [生产环境部署](#生产环境部署)
- [常见问题](#常见问题)
- [维护与监控](#维护与监控)

---

## 环境要求

### 硬件要求

| 配置项 | 最低要求 | 推荐配置 |
|--------|---------|---------|
| CPU | 4 核 | 8 核+ |
| 内存 | 8 GB | 16 GB+ |
| 磁盘 | 50 GB SSD | 200 GB+ SSD |
| GPU | 无 | NVIDIA GPU (用于本地模型) |

### 软件要求

| 软件 | 版本要求 | 说明 |
|------|---------|------|
| Python | 3.9+ | 推荐 3.10 或 3.11 |
| Docker | 20.10+ | 用于启动依赖服务 |
| Docker Compose | 2.0+ | 容器编排 |
| Git | 2.0+ | 版本控制 |

### 依赖服务

| 服务 | 版本 | 端口 | 用途 |
|------|------|------|------|
| PostgreSQL | 15+ | 5432 | 关系数据库 |
| Milvus | 2.3+ | 19530 | 向量数据库 |
| Redis | 7+ | 6379 | 缓存服务 |
| Neo4j | 5.0+ | 7687 | 图数据库 (可选) |

---

## 快速部署

### 一键启动（开发环境）

```bash
# 1. 克隆项目
git clone <repository-url>
cd Enterprise_RAG

# 2. 启动依赖服务
cd docker
docker-compose up -d

# 3. 创建 Python 虚拟环境
cd ..
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置数据库密码和 LLM API

# 6. 初始化数据库
python scripts/init_db.py

# 7. 启动应用
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 8. 访问系统
# API 文档: http://localhost:8000/docs
# 健康检查: http://localhost:8000/health
```

---

## 详细部署步骤

### 步骤 1: 启动依赖服务

使用 Docker Compose 一键启动所有依赖服务：

```bash
cd docker
docker-compose up -d
```

查看服务状态：

```bash
docker-compose ps
```

预期输出：

```
NAME            STATUS    PORTS
rag_postgres    Up        0.0.0.0:5432->5432/tcp
rag_redis       Up        0.0.0.0:6379->6379/tcp
rag_milvus      Up        0.0.0.0:19530->19530/tcp
rag_etcd        Up        2379/tcp
rag_minio       Up        0.0.0.0:9000-9001->9000-9001/tcp
```

### 步骤 2: 配置 Python 环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows PowerShell
.\venv\Scripts\Activate.ps1
# Windows CMD
venv\Scripts\activate.bat
# Linux/Mac
source venv/bin/activate

# 升级 pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

**注意：** 如果安装 `paddlepaddle` 失败，可以尝试：

```bash
# CPU 版本
pip install paddlepaddle -i https://pypi.tuna.tsinghua.edu.cn/simple

# GPU 版本 (CUDA 11.8)
pip install paddlepaddle-gpu -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 步骤 3: 配置环境变量

复制示例配置文件并修改：

```bash
cp .env.example .env
```

**必须配置的项目：**

```bash
# 数据库密码（生产环境必须修改）
POSTGRES_PASSWORD=your_secure_password_here

# LLM API 配置
OPENAI_API_KEY=your_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo

# JWT 密钥（生产环境必须修改）
JWT_SECRET_KEY=your_random_secret_key_here

# Neo4j（如果使用知识图谱）
NEO4J_PASSWORD=your_neo4j_password_here
```

**LLM 配置示例：**

```bash
# 使用 OpenAI
OPENAI_API_KEY=sk-your-api-key
OPENAI_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo

# 使用通义千问
OPENAI_API_KEY=sk-your-qwen-api-key
OPENAI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus

# 使用本地 Ollama
OPENAI_API_KEY=ollama
OPENAI_API_BASE=http://localhost:11434/v1
LLM_MODEL=llama2

# 使用本地 vLLM
OPENAI_API_KEY=vllm
OPENAI_API_BASE=http://localhost:8000/v1
LLM_MODEL=Qwen/Qwen2-7B-Instruct
```

### 步骤 4: 初始化数据库

```bash
# 初始化 PostgreSQL 表结构
python scripts/init_db.py

# 初始化 Milvus 集合
python scripts/init_milvus.py
```

### 步骤 5: 导入文档（可选）

```bash
# 将文档放入 data/raw_docs/ 目录
# 执行文档导入
python scripts/ingest_docs.py --input data/raw_docs/
```

### 步骤 6: 启动应用

**开发模式：**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**生产模式：**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 配置说明

### 核心配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `APP_NAME` | Enterprise RAG System | 应用名称 |
| `DEBUG` | false | 调试模式 |
| `ENVIRONMENT` | production | 运行环境 |
| `HOST` | 0.0.0.0 | 绑定地址 |
| `PORT` | 8000 | 服务端口 |
| `WORKERS` | 4 | Worker 进程数 |

### 数据库配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `POSTGRES_HOST` | localhost | PostgreSQL 地址 |
| `POSTGRES_PORT` | 5432 | PostgreSQL 端口 |
| `POSTGRES_USER` | rag_user | 数据库用户名 |
| `POSTGRES_PASSWORD` | - | 数据库密码 |
| `POSTGRES_DB` | enterprise_rag | 数据库名称 |

### 向量数据库配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `MILVUS_HOST` | localhost | Milvus 地址 |
| `MILVUS_PORT` | 19530 | Milvus 端口 |
| `VECTOR_DIM` | 1024 | 向量维度 |
| `MILVUS_INDEX_TYPE` | IVF_FLAT | 索引类型 |

### 检索配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `BM25_WEIGHT` | 0.3 | BM25 权重 |
| `VECTOR_WEIGHT` | 0.4 | 向量检索权重 |
| `RERANK_WEIGHT` | 0.3 | 重排序权重 |
| `INITIAL_RETRIEVAL_COUNT` | 100 | 初始召回数量 |
| `RERANK_TOP_K` | 20 | 重排序后保留数量 |
| `FINAL_TOP_K` | 5 | 最终返回数量 |

---

## 生产环境部署

### 使用 Gunicorn + Uvicorn

```bash
# 安装 Gunicorn
pip install gunicorn

# 启动（推荐配置）
gunicorn app.main:app \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    -b 0.0.0.0:8000 \
    --timeout 120 \
    --keep-alive 5 \
    --access-logfile - \
    --error-logfile -
```

### 使用 Systemd 管理服务

创建服务文件 `/etc/systemd/system/rag-api.service`：

```ini
[Unit]
Description=Enterprise RAG API Service
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/enterprise_rag
Environment="PATH=/opt/enterprise_rag/venv/bin"
EnvironmentFile=/opt/enterprise_rag/.env
ExecStart=/opt/enterprise_rag/venv/bin/gunicorn app.main:app \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    -b 0.0.0.0:8000 \
    --timeout 120
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启用并启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable rag-api
sudo systemctl start rag-api
sudo systemctl status rag-api
```

### Nginx 反向代理配置

```nginx
upstream rag_api {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name your-domain.com;

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL 证书
    ssl_certificate /etc/ssl/certs/your-cert.pem;
    ssl_certificate_key /etc/ssl/private/your-key.pem;

    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # 文件上传大小限制
    client_max_body_size 100M;

    location / {
        proxy_pass http://rag_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    # 健康检查
    location /health {
        proxy_pass http://rag_api/health;
        access_log off;
    }
}
```

### Docker 生产部署

创建 `Dockerfile`：

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
```

构建并运行：

```bash
# 构建镜像
docker build -t enterprise-rag:latest .

# 运行容器
docker run -d \
    --name rag-api \
    -p 8000:8000 \
    --env-file .env \
    --network rag_network \
    enterprise-rag:latest
```

---

## 常见问题

### Q1: Milvus 连接失败

**错误信息：** `Connection refused` 或 `Failed to connect to Milvus`

**解决方案：**

```bash
# 检查 Milvus 状态
docker-compose ps milvus

# 查看日志
docker-compose logs milvus

# 重启 Milvus
docker-compose restart milvus

# 等待服务就绪（约 30 秒）
sleep 30
```

### Q2: PostgreSQL 认证失败

**错误信息：** `password authentication failed`

**解决方案：**

1. 确认 `.env` 中的密码与 `docker-compose.yml` 一致
2. 如果修改了密码，需要删除数据卷重新创建：

```bash
docker-compose down -v
docker-compose up -d
```

### Q3: Embedding 模型下载慢

**解决方案：**

```bash
# 使用镜像源
export HF_ENDPOINT=https://hf-mirror.com

# 或手动下载模型到本地
# 然后配置 EMBEDDING_MODEL_PATH=/path/to/model
```

### Q4: 内存不足

**错误信息：** `Out of memory` 或 `Killed`

**解决方案：**

1. 减少 Worker 数量：`WORKERS=2`
2. 减小批处理大小：`EMBEDDING_BATCH_SIZE=16`
3. 使用更小的模型：`EMBEDDING_MODEL_NAME=BAAI/bge-base-zh-v1.5`

### Q5: LLM API 调用失败

**错误信息：** `API key invalid` 或 `Rate limit exceeded`

**解决方案：**

1. 检查 API Key 是否正确
2. 检查 API Base URL 是否匹配
3. 确认账户余额充足
4. 考虑使用本地模型（Ollama/vLLM）

---

## 维护与监控

### 日志查看

```bash
# 应用日志
tail -f logs/app.log

# Docker 服务日志
docker-compose logs -f

# 特定服务日志
docker-compose logs -f postgres
docker-compose logs -f milvus
```

### 健康检查

```bash
# API 健康检查
curl http://localhost:8000/health

# 系统信息
curl http://localhost:8000/info

# PostgreSQL 检查
docker-compose exec postgres pg_isready -U rag_user

# Redis 检查
docker-compose exec redis redis-cli ping

# Milvus 检查
curl http://localhost:9091/healthz
```

### 备份与恢复

**PostgreSQL 备份：**

```bash
# 备份
docker-compose exec postgres pg_dump -U rag_user enterprise_rag > backup.sql

# 恢复
docker-compose exec -T postgres psql -U rag_user enterprise_rag < backup.sql
```

**Milvus 备份：**

```bash
# Milvus 数据存储在 Docker Volume 中
# 备份 Volume
docker run --rm -v milvus_data:/data -v $(pwd):/backup alpine \
    tar czf /backup/milvus_backup.tar.gz /data
```

### 性能优化建议

1. **数据库索引**：确保常用查询字段有索引
2. **缓存配置**：调整 Redis 内存和 TTL
3. **向量索引**：根据数据量选择合适的索引类型
4. **Worker 数量**：CPU 核心数 * 2 + 1
5. **连接池**：配置合适的数据库连接池大小

---

## 服务端口汇总

| 服务 | 端口 | 说明 |
|------|------|------|
| RAG API | 8000 | 主应用 API |
| PostgreSQL | 5432 | 关系数据库 |
| Redis | 6379 | 缓存服务 |
| Milvus | 19530 | 向量数据库 gRPC |
| Milvus Metrics | 9091 | Milvus 监控 |
| MinIO API | 9000 | 对象存储 API |
| MinIO Console | 9001 | 对象存储控制台 |
| Neo4j Bolt | 7687 | 图数据库 |
| Neo4j HTTP | 7474 | 图数据库 Web UI |

---

## 联系与支持

如有问题，请通过以下方式获取帮助：

- 提交 Issue
- 查看项目 README.md
- 查阅 API 文档：`http://localhost:8000/docs`
