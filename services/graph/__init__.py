"""
========================================
图数据库服务模块
========================================

提供 Neo4j 图数据库的连接和操作服务

导出：
- Neo4jClient: Neo4j 客户端类
- neo4j_client: 全局单例实例
"""

from services.graph.neo4j_client import Neo4jClient, neo4j_client

__all__ = [
    "Neo4jClient",
    "neo4j_client",
]
