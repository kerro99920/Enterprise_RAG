"""
API v1 路由模块

包含所有 v1 版本的 API 路由
"""

from app.api.v1 import qa
from app.api.v1 import document
from app.api.v1 import admin

# 可选模块
try:
    from app.api.v1 import projects
except ImportError:
    projects = None

try:
    from app.api.v1 import drawing
except ImportError:
    drawing = None

try:
    from app.api.v1 import graph
except ImportError:
    graph = None

__all__ = [
    "qa",
    "document",
    "admin",
    "projects",
    "drawing",
    "graph",
]
