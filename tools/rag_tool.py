"""
RAG Tool
========

基于 `services.rag.pipeline.RagPipeline` 的一个简单工具封装，
给上层的 Agents 或 FastAPI 直接调用。
"""

from __future__ import annotations

from typing import Any, Optional

from services.rag import RagPipeline


async def run_rag(
    query: str,
    *,
    top_k: int = 5,
    project_id: Optional[str] = None,
    extra_context: Optional[str] = None,
    pipeline: RagPipeline | None = None,
) -> dict[str, Any]:
    """
    对外暴露的 RAG 调用工具。

    - `query`: 用户问题
    - `top_k`: 检索文档数量
    - `project_id`: 可选的项目 ID，用于限定检索范围
    - `extra_context`: 额外上下文（例如结构化指标、Agent 组装的说明）
    - `pipeline`: 可注入自定义 RagPipeline（方便测试或不同配置）
    """
    if pipeline is None:
        pipeline = RagPipeline()

    result = await pipeline.run(
        query=query,
        top_k=top_k,
        project_id=project_id,
        extra_context=extra_context,
    )
    return result

