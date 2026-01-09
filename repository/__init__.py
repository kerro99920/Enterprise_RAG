"""
========================================
Repository 模块初始化
========================================

📚 模块说明：
- 导入所有数据访问层
- 提供统一的导入接口

========================================
"""

# ===== 导入Repository类 =====
from repository.document_repo import DocumentRepository
from repository.query_log_repo import QueryLogRepository
from repository.vector_repo import VectorRepository

# ===== 导出列表 =====
__all__ = [
    "DocumentRepository",      # 文档数据访问
    "QueryLogRepository",       # 查询日志数据访问
    "VectorRepository",         # Milvus向量数据库访问
]


# =========================================
# 💡 使用示例
# =========================================
"""
# 方式1：统一导入
from repository import DocumentRepository, QueryLogRepository, VectorRepository

# 创建Repository实例
doc_repo = DocumentRepository(session)
query_repo = QueryLogRepository(session)
vector_repo = VectorRepository()


# 方式2：从具体模块导入
from repository.document_repo import DocumentRepository
from repository.query_log_repo import QueryLogRepository
from repository.vector_repo import VectorRepository
"""