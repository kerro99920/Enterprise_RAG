"""
========================================
FastAPI主应用
========================================

📚 模块说明：
- FastAPI应用入口
- 路由注册
- 中间件配置
- 全局错误处理

🎯 核心功能：
1. 应用初始化
2. 路由管理
3. CORS配置
4. 健康检查

========================================
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import time
from typing import Dict

from loguru import logger
from core.config import settings

# 导入API路由
from app.api.v1 import qa, document, admin


# =========================================
# 生命周期管理
# =========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    启动时：
    - 初始化数据库连接
    - 加载模型
    - 预热缓存

    关闭时：
    - 关闭数据库连接
    - 清理资源
    """
    # ===== 启动 =====
    logger.info("🚀 应用启动中...")

    # 这里可以添加启动时的初始化逻辑
    # 例如：连接数据库、加载模型等
    logger.info("✅ 应用启动完成")

    yield

    # ===== 关闭 =====
    logger.info("🛑 应用关闭中...")

    # 这里可以添加关闭时的清理逻辑
    logger.info("✅ 应用关闭完成")


# =========================================
# 创建FastAPI应用
# =========================================

app = FastAPI(
    title=settings.APP_NAME,
    description="企业级RAG知识问答系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# =========================================
# 中间件配置
# =========================================

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该设置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有HTTP请求"""
    start_time = time.time()

    # 记录请求
    logger.info(
        f"📥 {request.method} {request.url.path} | "
        f"Client: {request.client.host}"
    )

    # 处理请求
    response = await call_next(request)

    # 计算耗时
    process_time = time.time() - start_time

    # 记录响应
    logger.info(
        f"📤 {request.method} {request.url.path} | "
        f"Status: {response.status_code} | "
        f"Time: {process_time:.2f}s"
    )

    # 添加响应头
    response.headers["X-Process-Time"] = str(process_time)

    return response


# =========================================
# 全局异常处理
# =========================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError
):
    """处理参数验证错误"""
    logger.warning(f"参数验证失败: {exc.errors()}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "参数验证失败",
            "errors": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(
        request: Request,
        exc: Exception
):
    """处理所有未捕获的异常"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "服务器内部错误",
            "error": str(exc) if settings.DEBUG else "请联系管理员"
        }
    )


# =========================================
# 根路由
# =========================================

@app.get("/", tags=["Root"])
async def root() -> Dict:
    """
    根路径

    返回API基本信息
    """
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "message": "欢迎使用企业级RAG知识问答系统"
    }


@app.get("/health", tags=["Health"])
async def health_check() -> Dict:
    """
    健康检查

    用于监控系统状态
    """
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "environment": settings.APP_ENV
    }


# =========================================
# 注册API路由
# =========================================

# V1 API路由
app.include_router(
    qa.router,
    prefix="/api/v1/qa",
    tags=["问答"]
)

app.include_router(
    document.router,
    prefix="/api/v1/documents",
    tags=["文档管理"]
)

app.include_router(
    admin.router,
    prefix="/api/v1/admin",
    tags=["系统管理"]
)


# =========================================
# 启动信息
# =========================================

@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    logger.info("=" * 60)
    logger.info(f"🎉 {settings.APP_NAME} 启动成功")
    logger.info(f"📚 API文档: http://localhost:8000/docs")
    logger.info(f"🔧 环境: {settings.APP_ENV}")
    logger.info(f"🐛 调试模式: {settings.DEBUG}")
    logger.info("=" * 60)


# =========================================
# 运行应用（仅用于开发调试）
# =========================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式下自动重载
        log_level="info"
    )

# =========================================
# 💡 使用说明
# =========================================
"""
# 1. 开发环境启动
python app/main.py

# 或使用uvicorn
uvicorn app.main:app --reload --port 8000


# 2. 生产环境启动
gunicorn app.main:app \\
    --workers 4 \\
    --worker-class uvicorn.workers.UvicornWorker \\
    --bind 0.0.0.0:8000 \\
    --timeout 120


# 3. 访问API文档
打开浏览器访问: http://localhost:8000/docs


# 4. 测试健康检查
curl http://localhost:8000/health


# 5. 查看API信息
curl http://localhost:8000/
"""