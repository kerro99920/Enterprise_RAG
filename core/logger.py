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