"""
========================================
API v1 路由模块
========================================

📚 模块说明：
- 导出所有 API v1 路由
- 提供统一的导入接口

🎯 包含路由：
1. qa - 问答接口
2. document - 文档管理
3. admin - 系统管理
4. agents - Agent 智能体
5. projects - 项目管理

========================================
"""

# ===== 导入路由模块 =====
from app.api.v1 import qa
from app.api.v1 import document
from app.api.v1 import admin
import agents

# 尝试导入可选路由
try:
    from app.api.v1 import projects
    _has_projects = True
except ImportError:
    _has_projects = False

# ===== 导出列表 =====
__all__ = [
    "qa",
    "document",
    "admin",
    "agents",
]

if _has_projects:
    __all__.append("projects")


# =========================================
# 💡 使用示例
# =========================================
"""
# 在 main.py 中使用
from app.api.v1 import qa, document, admin, agents

app.include_router(qa.router, prefix="/api/v1/qa")
app.include_router(document.router, prefix="/api/v1/document")
app.include_router(admin.router, prefix="/api/v1/admin")
app.include_router(agents.router, prefix="/api/v1/agents")
"""