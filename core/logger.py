"""
========================================
日志配置模块
========================================

📚 模块说明：
- 使用 loguru 进行日志管理（比标准logging更易用）
- 支持多种日志输出：控制台、文件、错误日志、查询日志
- 自动日志轮转和压缩，节省磁盘空间

🎯 核心功能：
1. 彩色控制台输出 - 方便开发调试
2. 文件日志 - 生产环境记录
3. 错误日志分离 - 快速定位问题
4. 查询日志 - 分析用户行为
5. 性能指标日志 - 系统监控

========================================
"""
import sys
from pathlib import Path
from loguru import logger
from core.config import settings
from core.constants import LogEvent


def setup_logger():
    """
    配置日志系统

    🎨 日志输出类型：
    ┌─────────────────────────────────────┐
    │ 1. 控制台 - 带颜色，方便调试         │
    │ 2. 通用日志文件 - 记录所有日志       │
    │ 3. 错误日志文件 - 只记录错误         │
    │ 4. 查询日志文件 - 记录用户查询       │
    │ 5. 性能日志文件 - 记录性能指标       │
    └─────────────────────────────────────┘

    📁 日志文件命名：
    - app_2024-01-01.log        # 通用日志
    - error_2024-01-01.log      # 错误日志
    - query_2024-01-01.log      # 查询日志
    - metrics_2024-01-01.log    # 性能日志
    """

    # =========================================
    # Step 1: 移除默认的logger配置
    # =========================================
    # loguru默认会输出到stderr，我们需要自定义
    logger.remove()

    # =========================================
    # Step 2: 配置控制台输出（开发环境）
    # =========================================
    # 🎨 控制台日志格式（带颜色，方便阅读）
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "  # 时间（绿色）
        "<level>{level: <8}</level> | "  # 日志级别（根据级别显示颜色）
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "  # 位置信息（青色）
        "<level>{message}</level>"  # 日志内容
    )

    logger.add(
        sys.stdout,  # 输出到标准输出
        format=console_format,  # 使用彩色格式
        level=settings.LOG_LEVEL,  # 从配置读取日志级别
        colorize=True,  # 启用颜色
        backtrace=True,  # 显示完整的堆栈追踪
        diagnose=True  # 显示变量值（帮助调试）
    )

    # =========================================
    # Step 3: 配置通用日志文件
    # =========================================
    # 📝 记录所有级别的日志，用于问题追踪
    general_log_path = settings.LOG_DIR / "app_{time:YYYY-MM-DD}.log"

    logger.add(
        general_log_path,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        level="DEBUG",  # 记录DEBUG及以上级别
        rotation=settings.LOG_FILE_ROTATION,  # 每天轮转（配置为"1 day"）
        retention=settings.LOG_FILE_RETENTION,  # 保留30天
        compression="zip",  # 压缩旧日志（节省空间）
        encoding="utf-8",  # UTF-8编码支持中文
        enqueue=True,  # 异步写入（不阻塞主线程）
        backtrace=True,
        diagnose=True
    )

    # =========================================
    # Step 4: 配置错误日志文件（单独记录）
    # =========================================
    # ❗ 只记录ERROR及以上级别，方便快速定位问题
    error_log_path = settings.LOG_DIR / "error_{time:YYYY-MM-DD}.log"

    logger.add(
        error_log_path,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        level="ERROR",  # 只记录ERROR和CRITICAL
        rotation=settings.LOG_FILE_ROTATION,
        retention=settings.LOG_FILE_RETENTION,
        compression="zip",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,  # 错误日志必须有堆栈追踪
        diagnose=True
    )

    # =========================================
    # Step 5: 配置查询日志文件（可选）
    # =========================================
    # 📊 专门记录用户查询，用于分析用户行为和优化系统
    if settings.ENABLE_QUERY_LOG:
        query_log_path = settings.LOG_DIR / "query_{time:YYYY-MM-DD}.log"

        logger.add(
            query_log_path,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {message}",
            level="INFO",
            rotation=settings.LOG_FILE_ROTATION,
            retention=settings.LOG_FILE_RETENTION,
            compression="zip",
            encoding="utf-8",
            enqueue=True,
            # 🔍 过滤器：只记录带"query"标记的日志
            filter=lambda record: "query" in record["extra"]
        )

    # =========================================
    # Step 6: 配置性能指标日志（可选）
    # =========================================
    # 📈 记录系统性能指标，用于监控和优化
    if settings.ENABLE_METRICS:
        metrics_log_path = settings.LOG_DIR / "metrics_{time:YYYY-MM-DD}.log"

        logger.add(
            metrics_log_path,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {message}",
            level="INFO",
            rotation=settings.LOG_FILE_ROTATION,
            retention=settings.LOG_FILE_RETENTION,
            compression="zip",
            encoding="utf-8",
            enqueue=True,
            # 🔍 过滤器：只记录带"metrics"标记的日志
            filter=lambda record: "metrics" in record["extra"]
        )

    # =========================================
    # 初始化完成提示
    # =========================================
    logger.info("=" * 50)
    logger.info("日志系统初始化完成")
    logger.info(f"日志级别: {settings.LOG_LEVEL}")
    logger.info(f"日志目录: {settings.LOG_DIR}")
    logger.info("=" * 50)


# =========================================
# 日志辅助函数
# =========================================

def log_query(query: str, user_id: str, event: str, **kwargs):
    """
    记录查询日志

    📊 用途：
    - 分析用户搜索习惯
    - 统计热门查询
    - 优化检索效果

    参数：
        query: 查询内容
        user_id: 用户ID
        event: 事件类型（如"query_start", "query_end"）
        **kwargs: 其他附加信息（如检索结果数、耗时等）

    示例：
        log_query(
            query="防水规范",
            user_id="user_123",
            event="query_end",
            results_count=5,
            time_taken=1.2
        )
    """
    log_data = {
        "query": query,
        "user_id": user_id,
        "event": event,
        **kwargs
    }
    # bind(query=True) 标记这是查询日志，会被过滤器捕获
    logger.bind(query=True).info(f"QUERY | {log_data}")


def log_metrics(metric_name: str, value: float, **kwargs):
    """
    记录性能指标

    📈 用途：
    - 监控系统性能
    - 发现性能瓶颈
    - 生成性能报告

    参数：
        metric_name: 指标名称（如"retrieval_time", "embedding_time"）
        value: 指标值（通常是时间或计数）
        **kwargs: 其他附加信息

    示例：
        log_metrics(
            metric_name="retrieval_time",
            value=0.5,
            user_id="user_123",
            query="防水规范"
        )
    """
    log_data = {
        "metric": metric_name,
        "value": value,
        **kwargs
    }
    logger.bind(metrics=True).info(f"METRICS | {log_data}")


def log_document_processing(doc_id: str, status: str, **kwargs):
    """
    记录文档处理日志

    📄 用途：
    - 跟踪文档处理状态
    - 定位处理失败的文档
    - 统计处理效率

    参数：
        doc_id: 文档ID
        status: 处理状态（pending/processing/completed/failed）
        **kwargs: 其他信息（如错误原因、处理时间）

    示例：
        log_document_processing(
            doc_id="doc_001",
            status="completed",
            chunks_created=10,
            time_taken=2.5
        )
    """
    log_data = {
        "doc_id": doc_id,
        "status": status,
        **kwargs
    }
    logger.info(f"DOCUMENT | {log_data}")


def log_retrieval(query: str, retrieved_count: int, time_taken: float, **kwargs):
    """
    记录检索日志

    🔍 用途：
    - 监控检索性能
    - 分析检索质量
    - 优化检索策略

    参数：
        query: 查询内容
        retrieved_count: 检索到的文档数量
        time_taken: 检索耗时（秒）
        **kwargs: 其他信息（如检索模式、向量库）

    示例：
        log_retrieval(
            query="防水规范",
            retrieved_count=5,
            time_taken=0.3,
            mode="hybrid",
            collection="rag_standards"
        )
    """
    log_data = {
        "query": query,
        "retrieved_count": retrieved_count,
        "time_taken": time_taken,
        **kwargs
    }
    logger.bind(query=True).info(f"RETRIEVAL | {log_data}")


def log_error(error_type: str, error_message: str, **kwargs):
    """
    记录错误日志

    ❗ 用途：
    - 快速定位问题
    - 统计错误类型
    - 告警通知

    参数：
        error_type: 错误类型（如"DatabaseError", "APIError"）
        error_message: 错误详细信息
        **kwargs: 上下文信息

    示例：
        log_error(
            error_type="VectorDBError",
            error_message="Milvus连接失败",
            host="localhost",
            port=19530
        )
    """
    log_data = {
        "error_type": error_type,
        "error_message": error_message,
        **kwargs
    }
    logger.error(f"ERROR | {log_data}")


# =========================================
# 日志上下文管理器
# =========================================

class LoggerContext:
    """
    日志上下文管理器

    🎯 用途：
    自动记录代码块的执行时间和状态

    💡 使用场景：
    - 记录函数执行时间
    - 自动捕获异常
    - 统一日志格式

    示例：
        with LoggerContext("文档处理", doc_id="doc_001"):
            # 处理文档的代码
            process_document()

        # 输出：
        # 开始 文档处理 | {'doc_id': 'doc_001'}
        # 完成 文档处理 | 耗时: 2.50s | {'doc_id': 'doc_001'}
    """

    def __init__(self, operation: str, **kwargs):
        """
        初始化上下文管理器

        参数：
            operation: 操作名称（如"文档处理", "向量检索"）
            **kwargs: 附加信息，会包含在日志中
        """
        self.operation = operation
        self.context = kwargs
        self.start_time = None

    def __enter__(self):
        """
        进入上下文时调用
        记录开始时间和日志
        """
        import time
        self.start_time = time.time()
        logger.info(f"▶ 开始 {self.operation} | {self.context}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        退出上下文时调用
        记录结束日志和耗时

        参数：
            exc_type: 异常类型（如果有）
            exc_val: 异常值
            exc_tb: 异常追踪
        """
        import time
        elapsed = time.time() - self.start_time

        if exc_type is None:
            # 成功完成
            logger.info(f"✓ 完成 {self.operation} | 耗时: {elapsed:.2f}s | {self.context}")

            # 记录性能指标
            if settings.ENABLE_METRICS:
                log_metrics(f"{self.operation}_time", elapsed, **self.context)
        else:
            # 发生异常
            logger.error(
                f"✗ 失败 {self.operation} | 耗时: {elapsed:.2f}s | "
                f"错误: {exc_val} | {self.context}"
            )

        # 返回False表示不抑制异常（让异常继续抛出）
        return False


# =========================================
# 装饰器：自动记录函数执行
# =========================================

def log_execution(operation_name: str = None):
    """
    装饰器：自动记录函数执行时间和状态

    🎯 用途：
    - 无需手动写日志代码
    - 统一日志格式
    - 自动记录性能指标

    参数：
        operation_name: 操作名称（默认使用函数名）

    示例：
        @log_execution("文档处理")
        def process_document(doc_id):
            # 处理文档...
            return result

        # 自动输出：
        # 开始执行: 文档处理
        # 执行完成: 文档处理 | 耗时: 2.30s

    💡 支持异步函数：
        @log_execution("异步查询")
        async def query_database(query):
            # 异步查询...
            return results
    """

    def decorator(func):
        import functools
        import time

        # =========================================
        # 异步函数包装器
        # =========================================
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            op_name = operation_name or func.__name__
            start = time.time()

            try:
                logger.info(f"▶ 开始执行: {op_name}")
                result = await func(*args, **kwargs)
                elapsed = time.time() - start
                logger.info(f"✓ 执行完成: {op_name} | 耗时: {elapsed:.2f}s")

                # 记录性能指标
                if settings.ENABLE_METRICS:
                    log_metrics(f"{op_name}_time", elapsed)

                return result
            except Exception as e:
                elapsed = time.time() - start
                logger.error(f"✗ 执行失败: {op_name} | 耗时: {elapsed:.2f}s | 错误: {str(e)}")
                raise

        # =========================================
        # 同步函数包装器
        # =========================================
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            op_name = operation_name or func.__name__
            start = time.time()

            try:
                logger.info(f"▶ 开始执行: {op_name}")
                result = func(*args, **kwargs)
                elapsed = time.time() - start
                logger.info(f"✓ 执行完成: {op_name} | 耗时: {elapsed:.2f}s")

                # 记录性能指标
                if settings.ENABLE_METRICS:
                    log_metrics(f"{op_name}_time", elapsed)

                return result
            except Exception as e:
                elapsed = time.time() - start
                logger.error(f"✗ 执行失败: {op_name} | 耗时: {elapsed:.2f}s | 错误: {str(e)}")
                raise

        # 检查函数是否是协程函数
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# =========================================
# 导出
# =========================================
__all__ = [
    "logger",  # loguru的logger实例
    "setup_logger",  # 初始化日志系统
    "log_query",  # 记录查询日志
    "log_metrics",  # 记录性能指标
    "log_document_processing",  # 记录文档处理日志
    "log_retrieval",  # 记录检索日志
    "log_error",  # 记录错误日志
    "LoggerContext",  # 上下文管理器
    "log_execution"  # 装饰器
]

# =========================================
# 💡 完整使用示例
# =========================================
"""
# 1. 基础日志
from core.logger import logger

logger.debug("调试信息")
logger.info("正常信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")


# 2. 使用上下文管理器
from core.logger import LoggerContext

with LoggerContext("文档处理", doc_id="doc_001"):
    # 你的代码
    process_document()


# 3. 使用装饰器
from core.logger import log_execution

@log_execution("查询数据库")
def query_db(query):
    # 查询代码
    return results


# 4. 记录查询日志
from core.logger import log_query

log_query(
    query="防水规范",
    user_id="user_123",
    event="query_end",
    results_count=5,
    time_taken=1.2
)


# 5. 记录性能指标
from core.logger import log_metrics

log_metrics(
    metric_name="retrieval_time",
    value=0.5,
    query="防水规范"
)
"""