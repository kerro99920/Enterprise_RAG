"""
========================================
Redis 缓存服务
========================================

📚 模块说明：
- 封装Redis的所有缓存操作
- 提供连接池管理
- 实现常用缓存模式

🎯 核心功能：
1. Redis连接池管理
2. 基本缓存操作（get/set/delete）
3. 查询结果缓存
4. 用户权限缓存
5. 热门查询统计

========================================
"""
import json
import hashlib
from typing import Optional, Any, List, Dict
import redis
from redis.connection import ConnectionPool

from core.config import settings
from core.constants import CacheKey
from core.logger import logger, log_execution


class RedisClient:
    """
    Redis缓存客户端

    🎯 职责：
    - 管理Redis连接池
    - 提供缓存操作接口
    - 实现业务级缓存方法

    💡 设计理念：
    - 单例模式：全局共享一个Redis连接池
    - 自动序列化：自动处理Python对象和JSON的转换
    - 键命名规范：使用统一的前缀管理
    """

    _instance = None
    _pool = None

    def __new__(cls):
        """单例模式：确保只有一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """
        初始化Redis客户端

        📌 连接池的好处：
        - 复用连接，减少开销
        - 自动管理连接生命周期
        - 支持并发访问
        """
        if self._pool is None:
            self._init_pool()

    def _init_pool(self):
        """初始化Redis连接池"""
        try:
            # 创建连接池
            self._pool = ConnectionPool(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                db=settings.REDIS_DB,
                decode_responses=True,  # 自动解码为字符串
                max_connections=50,  # 最大连接数
                socket_timeout=5,  # 连接超时
                socket_connect_timeout=5  # 连接建立超时
            )

            # 测试连接
            client = redis.Redis(connection_pool=self._pool)
            client.ping()

            logger.info(f"Redis连接池初始化成功: {settings.REDIS_HOST}:{settings.REDIS_PORT}")

        except Exception as e:
            logger.error(f"Redis连接池初始化失败: {str(e)}")
            raise

    def get_client(self) -> redis.Redis:
        """
        获取Redis客户端实例

        返回：
            redis.Redis: Redis客户端
        """
        if self._pool is None:
            self._init_pool()
        return redis.Redis(connection_pool=self._pool)

    # =========================================
    # 基础缓存操作
    # =========================================

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        参数：
            key: 缓存键

        返回：
            Any: 缓存值（自动反序列化JSON），不存在返回None

        示例：
            value = redis_client.get("user:123:profile")
        """
        try:
            client = self.get_client()
            value = client.get(key)

            if value is None:
                return None

            # 尝试反序列化JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except Exception as e:
            logger.error(f"获取缓存失败: key={key}, error={str(e)}")
            return None

    def set(
            self,
            key: str,
            value: Any,
            expire: Optional[int] = None
    ) -> bool:
        """
        设置缓存值

        参数：
            key: 缓存键
            value: 缓存值（自动序列化为JSON）
            expire: 过期时间（秒），None表示永不过期

        返回：
            bool: 设置成功返回True

        示例：
            # 缓存6小时
            redis_client.set("user:123:profile", user_data, expire=21600)
        """
        try:
            client = self.get_client()

            # 序列化值
            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)

            # 设置缓存
            if expire is None:
                expire = settings.REDIS_CACHE_TTL  # 使用默认过期时间

            client.setex(key, expire, value)
            return True

        except Exception as e:
            logger.error(f"设置缓存失败: key={key}, error={str(e)}")
            return False

    def delete(self, key: str) -> bool:
        """
        删除缓存

        参数：
            key: 缓存键

        返回：
            bool: 删除成功返回True
        """
        try:
            client = self.get_client()
            result = client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"删除缓存失败: key={key}, error={str(e)}")
            return False

    def exists(self, key: str) -> bool:
        """
        检查缓存键是否存在

        参数：
            key: 缓存键

        返回：
            bool: 存在返回True
        """
        try:
            client = self.get_client()
            return client.exists(key) > 0
        except Exception as e:
            logger.error(f"检查缓存存在失败: key={key}, error={str(e)}")
            return False

    def expire(self, key: str, seconds: int) -> bool:
        """
        设置缓存过期时间

        参数：
            key: 缓存键
            seconds: 过期时间（秒）

        返回：
            bool: 设置成功返回True
        """
        try:
            client = self.get_client()
            return client.expire(key, seconds)
        except Exception as e:
            logger.error(f"设置过期时间失败: key={key}, error={str(e)}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        删除匹配模式的所有键

        参数：
            pattern: 键模式（支持通配符*）

        返回：
            int: 删除的键数量

        示例：
            # 删除所有用户缓存
            count = redis_client.delete_pattern("user:*")
        """
        try:
            client = self.get_client()
            keys = client.keys(pattern)
            if keys:
                return client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"批量删除缓存失败: pattern={pattern}, error={str(e)}")
            return 0

    # =========================================
    # 业务级缓存方法
    # =========================================

    def cache_query_result(
            self,
            query: str,
            result: Dict[str, Any],
            expire: Optional[int] = None
    ) -> bool:
        """
        缓存查询结果

        参数：
            query: 查询问题
            result: 查询结果
            expire: 过期时间（秒）

        返回：
            bool: 缓存成功返回True

        💡 设计理念：
        - 使用查询内容的MD5作为键
        - 避免键过长
        - 相同查询自动命中缓存
        """
        try:
            # 生成缓存键（使用查询的MD5）
            query_hash = hashlib.md5(query.encode()).hexdigest()
            cache_key = f"{CacheKey.QUERY_RESULT}{query_hash}"

            # 缓存结果
            return self.set(cache_key, result, expire)

        except Exception as e:
            logger.error(f"缓存查询结果失败: error={str(e)}")
            return False

    def get_cached_query_result(self, query: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存的查询结果

        参数：
            query: 查询问题

        返回：
            Dict: 查询结果，不存在返回None
        """
        try:
            query_hash = hashlib.md5(query.encode()).hexdigest()
            cache_key = f"{CacheKey.QUERY_RESULT}{query_hash}"

            return self.get(cache_key)

        except Exception as e:
            logger.error(f"获取缓存查询结果失败: error={str(e)}")
            return None

    def cache_user_permissions(
            self,
            user_id: str,
            permissions: List[str],
            expire: int = 3600
    ) -> bool:
        """
        缓存用户权限

        参数：
            user_id: 用户ID
            permissions: 权限列表
            expire: 过期时间（秒），默认1小时

        返回：
            bool: 缓存成功返回True

        💡 为什么缓存权限？
        - 权限检查频繁
        - 减少数据库查询
        - 提升响应速度
        """
        try:
            cache_key = f"{CacheKey.USER_PERMISSIONS}{user_id}"
            return self.set(cache_key, permissions, expire)
        except Exception as e:
            logger.error(f"缓存用户权限失败: error={str(e)}")
            return False

    def get_user_permissions(self, user_id: str) -> Optional[List[str]]:
        """
        获取缓存的用户权限

        参数：
            user_id: 用户ID

        返回：
            List[str]: 权限列表，不存在返回None
        """
        try:
            cache_key = f"{CacheKey.USER_PERMISSIONS}{user_id}"
            return self.get(cache_key)
        except Exception as e:
            logger.error(f"获取用户权限缓存失败: error={str(e)}")
            return None

    def add_search_history(
            self,
            user_id: str,
            query: str,
            max_history: int = 50
    ) -> bool:
        """
        添加用户搜索历史

        参数：
            user_id: 用户ID
            query: 查询内容
            max_history: 最大保存数量

        返回：
            bool: 添加成功返回True

        💡 使用Redis List：
        - LPUSH：从左侧插入（最新的在前）
        - LTRIM：保留最新的N条
        """
        try:
            client = self.get_client()
            cache_key = f"{CacheKey.USER_SEARCH_HISTORY}{user_id}"

            # 添加到列表头部
            client.lpush(cache_key, query)

            # 只保留最新的max_history条
            client.ltrim(cache_key, 0, max_history - 1)

            # 设置过期时间（30天）
            client.expire(cache_key, 30 * 24 * 3600)

            return True

        except Exception as e:
            logger.error(f"添加搜索历史失败: error={str(e)}")
            return False

    def get_search_history(
            self,
            user_id: str,
            limit: int = 10
    ) -> List[str]:
        """
        获取用户搜索历史

        参数：
            user_id: 用户ID
            limit: 返回的最大数量

        返回：
            List[str]: 搜索历史列表（最新的在前）
        """
        try:
            client = self.get_client()
            cache_key = f"{CacheKey.USER_SEARCH_HISTORY}{user_id}"

            # 获取最新的limit条
            history = client.lrange(cache_key, 0, limit - 1)
            return history

        except Exception as e:
            logger.error(f"获取搜索历史失败: error={str(e)}")
            return []

    def increment_hot_query(self, query: str) -> int:
        """
        增加热门查询计数

        参数：
            query: 查询内容

        返回：
            int: 当前计数

        💡 使用Redis Sorted Set：
        - ZINCRBY：增加分数（计数）
        - 自动按分数排序
        """
        try:
            client = self.get_client()

            # 使用有序集合统计热门查询
            score = client.zincrby(
                CacheKey.HOT_QUERIES,
                1,
                query
            )

            return int(score)

        except Exception as e:
            logger.error(f"增加热门查询计数失败: error={str(e)}")
            return 0

    def get_hot_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取热门查询

        参数：
            limit: 返回的最大数量

        返回：
            List[Dict]: 热门查询列表，包含query和count

        示例返回：
            [
                {"query": "防水规范", "count": 150},
                {"query": "混凝土强度", "count": 120},
                ...
            ]
        """
        try:
            client = self.get_client()

            # 获取分数最高的N个（降序）
            hot_queries = client.zrevrange(
                CacheKey.HOT_QUERIES,
                0,
                limit - 1,
                withscores=True
            )

            # 格式化结果
            result = []
            for query, count in hot_queries:
                result.append({
                    "query": query,
                    "count": int(count)
                })

            return result

        except Exception as e:
            logger.error(f"获取热门查询失败: error={str(e)}")
            return []

    def cache_document_metadata(
            self,
            doc_id: str,
            metadata: Dict[str, Any],
            expire: int = 3600
    ) -> bool:
        """
        缓存文档元数据

        参数：
            doc_id: 文档ID
            metadata: 元数据
            expire: 过期时间（秒）

        返回：
            bool: 缓存成功返回True
        """
        try:
            cache_key = f"{CacheKey.DOCUMENT_METADATA}{doc_id}"
            return self.set(cache_key, metadata, expire)
        except Exception as e:
            logger.error(f"缓存文档元数据失败: error={str(e)}")
            return False

    def get_document_metadata(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存的文档元数据

        参数：
            doc_id: 文档ID

        返回：
            Dict: 文档元数据，不存在返回None
        """
        try:
            cache_key = f"{CacheKey.DOCUMENT_METADATA}{doc_id}"
            return self.get(cache_key)
        except Exception as e:
            logger.error(f"获取文档元数据缓存失败: error={str(e)}")
            return None

    # =========================================
    # 工具方法
    # =========================================

    def clear_all(self) -> bool:
        """
        清空所有缓存

        ⚠️ 谨慎使用！只在开发/测试环境使用

        返回：
            bool: 清空成功返回True
        """
        try:
            client = self.get_client()
            client.flushdb()
            logger.warning("已清空所有Redis缓存")
            return True
        except Exception as e:
            logger.error(f"清空缓存失败: error={str(e)}")
            return False

    def get_info(self) -> Dict[str, Any]:
        """
        获取Redis服务器信息

        返回：
            Dict: Redis服务器信息
        """
        try:
            client = self.get_client()
            info = client.info()
            return {
                "redis_version": info.get("redis_version"),
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace": info.get("db0", {})
            }
        except Exception as e:
            logger.error(f"获取Redis信息失败: error={str(e)}")
            return {}

    def ping(self) -> bool:
        """
        测试Redis连接

        返回：
            bool: 连接正常返回True
        """
        try:
            client = self.get_client()
            return client.ping()
        except Exception as e:
            logger.error(f"Redis连接测试失败: error={str(e)}")
            return False


# =========================================
# 创建全局单例实例
# =========================================
redis_client = RedisClient()

# =========================================
# 💡 使用示例
# =========================================
"""
# 1. 使用全局实例
from services.cache.redis_client import redis_client

# 基础操作
redis_client.set("key", "value", expire=3600)
value = redis_client.get("key")
redis_client.delete("key")


# 2. 缓存查询结果
query = "防水规范是什么？"
result = {
    "answer": "根据规范...",
    "sources": ["doc_1", "doc_2"]
}

# 缓存
redis_client.cache_query_result(query, result)

# 获取
cached_result = redis_client.get_cached_query_result(query)
if cached_result:
    print("命中缓存！")


# 3. 用户搜索历史
redis_client.add_search_history("user_123", "防水规范")
redis_client.add_search_history("user_123", "混凝土强度")

history = redis_client.get_search_history("user_123", limit=10)
print(f"搜索历史: {history}")


# 4. 热门查询统计
redis_client.increment_hot_query("防水规范")
redis_client.increment_hot_query("防水规范")
redis_client.increment_hot_query("混凝土强度")

hot_queries = redis_client.get_hot_queries(limit=10)
for item in hot_queries:
    print(f"{item['query']}: {item['count']}次")


# 5. 用户权限缓存
permissions = ["read:standard", "write:project"]
redis_client.cache_user_permissions("user_123", permissions)

cached_perms = redis_client.get_user_permissions("user_123")
print(f"用户权限: {cached_perms}")


# 6. 检查Redis状态
if redis_client.ping():
    print("Redis连接正常")

info = redis_client.get_info()
print(f"Redis版本: {info['redis_version']}")
print(f"内存使用: {info['used_memory_human']}")
"""