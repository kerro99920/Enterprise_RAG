"""
========================================
Cache 服务模块初始化
========================================

📚 模块说明：
- 导入缓存服务
- 提供统一的缓存接口

========================================
"""

# ===== 导入Redis客户端 =====
from services.cache.redis_client import RedisClient, redis_client

# ===== 导出列表 =====
__all__ = [
    "RedisClient",      # Redis客户端类
    "redis_client",     # 全局Redis客户端实例（单例）
]


# =========================================
# 💡 使用示例
# =========================================
"""
# 方式1：使用全局单例实例（推荐）
from services.cache import redis_client

# 基础缓存操作
redis_client.set("key", "value")
value = redis_client.get("key")

# 业务缓存操作
redis_client.cache_query_result(query, result)
cached = redis_client.get_cached_query_result(query)


# 方式2：创建新实例（通常不需要）
from services.cache import RedisClient

client = RedisClient()  # 实际上返回的还是单例
client.set("key", "value")
"""