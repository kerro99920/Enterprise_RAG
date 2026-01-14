"""
========================================
企业级 RAG 系统 - 主入口
========================================

📚 模块说明：
- FastAPI 应用入口
- 路由注册
- 中间件配置
- 生命周期管理

🚀 启动方式：
    # 开发模式
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

    # 生产模式
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

========================================
"""

import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager

# 添加项目根目录到 Python 路径
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# 导入配置和核心模块
from core.config import settings
from core.logger import logger

# 导入路由
from app.api.v1 import qa, document, admin


# =========================================
# 生命周期管理
# =========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    启动时：
    - 初始化日志
    - 检查数据库连接
    - 预热模型（可选）

    关闭时：
    - 清理资源
    - 关闭连接
    """
    # ===== 启动阶段 =====
    logger.info("=" * 60)
    logger.info(f"🚀 启动 {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 60)

    # 日志系统已在导入时自动初始化

    # 检查关键服务连接
    await check_services()

    logger.info("✅ 应用启动完成")
    logger.info(f"📡 API 地址: http://{settings.HOST}:{settings.PORT}")
    logger.info(f"📚 API 文档: http://{settings.HOST}:{settings.PORT}/docs")

    yield  # 应用运行中

    # ===== 关闭阶段 =====
    logger.info("🛑 应用正在关闭...")

    # 清理资源
    await cleanup_resources()

    logger.info("👋 应用已关闭")


async def check_services():
    """检查关键服务连接"""
    logger.info("检查服务连接...")

    # 检查 Redis
    try:
        from services.cache.redis_client import redis_client
        if redis_client.ping():
            logger.info("  ✓ Redis 连接正常")
        else:
            logger.warning("  ⚠ Redis 连接失败")
    except Exception as e:
        logger.warning(f"  ⚠ Redis 检查异常: {e}")

    # 检查 Milvus
    try:
        from pymilvus import connections, utility
        connections.connect(
            alias="default",
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT
        )
        logger.info("  ✓ Milvus 连接正常")
    except Exception as e:
        logger.warning(f"  ⚠ Milvus 检查异常: {e}")

    # 检查 PostgreSQL
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(settings.postgres_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("  ✓ PostgreSQL 连接正常")
    except Exception as e:
        logger.warning(f"  ⚠ PostgreSQL 检查异常: {e}")


async def cleanup_resources():
    """清理资源"""
    try:
        # 断开 Milvus 连接
        from pymilvus import connections
        connections.disconnect("default")
        logger.info("  ✓ Milvus 连接已断开")
    except Exception as e:
        logger.warning(f"  ⚠ Milvus 断开异常: {e}")


# =========================================
# 创建 FastAPI 应用
# =========================================

app = FastAPI(
    title=settings.APP_NAME,
    description="""
## 🎯 企业级 RAG 智能知识问答系统

基于 Milvus + PostgreSQL + Redis + 大模型的私有化 RAG 问答系统。

### 主要功能

- **📄 文档管理**: 上传、解析、向量化文档
- **🔍 智能检索**: 混合检索（向量 + BM25）+ 重排序
- **💬 智能问答**: 基于检索的增强生成（RAG）
- **📊 系统管理**: 索引管理、缓存管理、统计分析

### 技术栈

- FastAPI + Uvicorn
- Milvus (向量数据库)
- PostgreSQL (关系数据库)
- Redis (缓存)
- 大模型 (可配置)
    """,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)


# =========================================
# 中间件配置
# =========================================

# CORS 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    import time

    start_time = time.time()

    # 处理请求
    response = await call_next(request)

    # 计算耗时
    process_time = time.time() - start_time

    # 记录日志
    logger.info(
        f"{request.method} {request.url.path} "
        f"| Status: {response.status_code} "
        f"| Time: {process_time:.3f}s"
    )

    # 添加响应头
    response.headers["X-Process-Time"] = str(process_time)

    return response


# =========================================
# 全局异常处理
# =========================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.status_code,
                "message": exc.detail
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": 500,
                "message": "服务器内部错误" if settings.ENVIRONMENT == "production" else str(exc)
            }
        }
    )


# =========================================
# 注册路由
# =========================================

# API v1 路由
app.include_router(
    qa.router,
    prefix=f"{settings.API_PREFIX}/qa",
    tags=["问答接口"]
)

app.include_router(
    document.router,
    prefix=f"{settings.API_PREFIX}/document",
    tags=["文档管理"]
)

app.include_router(
    admin.router,
    prefix=f"{settings.API_PREFIX}/admin",
    tags=["系统管理"]
)


# =========================================
# 根路由
# =========================================

@app.get("/", tags=["根路由"])
async def root():
    """
    根路由 - 返回系统信息
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "api_prefix": settings.API_PREFIX
    }


@app.get("/health", tags=["健康检查"])
async def health_check():
    """
    健康检查接口

    用于负载均衡器和容器编排的健康检查
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


@app.get("/info", tags=["系统信息"])
async def system_info():
    """
    获取系统信息
    """
    import platform

    return {
        "app": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG
        },
        "system": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor()
        },
        "config": {
            "api_prefix": settings.API_PREFIX,
            "milvus_host": settings.MILVUS_HOST,
            "redis_host": settings.REDIS_HOST,
            "postgres_host": settings.POSTGRES_HOST
        }
    }


# =========================================
# 启动入口
# =========================================

def main():
    """主函数 - 启动应用"""
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.WORKERS,
        log_level="info" if settings.DEBUG else "warning"
    )


if __name__ == "__main__":
    main()


# =========================================
# 💡 使用说明
# =========================================
"""
# 1. 开发模式启动（自动重载）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 2. 生产模式启动（多 worker）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# 3. 使用 Python 直接启动
python app/main.py

# 4. 指定配置文件
ENVIRONMENT=production python app/main.py

# 5. 访问 API 文档
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc

# 6. 健康检查
curl http://localhost:8000/health

# 7. 系统信息
curl http://localhost:8000/info
"""
