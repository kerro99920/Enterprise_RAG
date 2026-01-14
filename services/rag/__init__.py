"""
RAG (Retrieval-Augmented Generation) 高层流程模块。

这里主要负责把检索、重排、LLM 调用等能力编排成一个完整的 RAG Pipeline，
供上层的 tools 和 agents 调用。
"""

from .pipeline import RagPipeline

__all__ = ["RagPipeline"]

