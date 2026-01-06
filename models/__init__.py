"""
========================================
Models 模块初始化
========================================

📚 模块说明：
- 导入所有数据模型
- 提供统一的导入接口
- 管理数据库基类

========================================
"""

# ===== 导入基类 =====
from models.document import Base

# ===== 导入文档相关模型 =====
from models.document import (
    Document,  # 文档主表
    DocumentChunk,  # 文档分块表
    DocumentMetadata,  # 文档元数据表
)

# ===== 导入查询相关模型 =====
from models.query import (
    QueryLog,  # 查询日志表
    QueryFeedback,  # 查询反馈表
)

# ===== 导入用户相关模型 =====
from models.user import (
    User,  # 用户表
    UserPermission,  # 用户权限表
    UserSearchHistory,  # 用户搜索历史表
)

# ===== 导出列表 =====
__all__ = [
    # 基类
    "Base",

    # 文档模型
    "Document",
    "DocumentChunk",
    "DocumentMetadata",

    # 查询模型
    "QueryLog",
    "QueryFeedback",

    # 用户模型
    "User",
    "UserPermission",
    "UserSearchHistory",
]


# ===== 便捷函数 =====
def get_all_models():
    """
    获取所有模型类

    返回：
        list: 所有模型类的列表
    """
    return [
        Document,
        DocumentChunk,
        DocumentMetadata,
        QueryLog,
        QueryFeedback,
        User,
        UserPermission,
        UserSearchHistory,
    ]


def get_table_names():
    """
    获取所有表名

    返回：
        list: 所有表名的列表
    """
    return [model.__tablename__ for model in get_all_models()]


# =========================================
# 💡 使用示例
# =========================================
"""
# 方式1：统一导入
from models import Document, QueryLog, User

# 方式2：从具体模块导入
from models.document import Document
from models.query import QueryLog
from models.user import User

# 方式3：获取所有模型
from models import get_all_models

all_models = get_all_models()
for model in all_models:
    print(model.__tablename__)
"""