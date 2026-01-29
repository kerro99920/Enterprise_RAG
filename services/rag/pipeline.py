"""
========================================
RAG Pipeline - 核心流程编排
========================================

📚 模块说明：
- 整合检索、重排、LLM 调用的完整 RAG 流程
- 提供统一的问答接口
- 支持异步调用

🎯 核心功能：
1. 查询预处理
2. 混合检索（向量 + BM25）
3. 重排序
4. LLM 答案生成
5. 结果后处理

========================================
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from loguru import logger

# 导入核心组件
from core.config import settings
from services.retrieval.hybrid.hybrid_retriever import HybridRetriever
from services.retrieval.bm25.bm25_engine import BM25Retriever
from services.retrieval.vector.vector_engine import VectorRetriever
from services.rerank.reranker import Reranker
from services.embedding.embedder import Embedder
from services.embedding.embedding_model import EmbeddingModel
from services.llm.llm_client import LLMClient
from services.llm.prompt.qa_prompt import QAPromptFactory
from services.cache.redis_client import redis_client

# 图谱增强检索组件
try:
    from services.retrieval.graph.graph_retriever import GraphRetriever
    from services.retrieval.graph_enhanced_retriever import GraphEnhancedRetriever
    GRAPH_RETRIEVAL_AVAILABLE = True
except ImportError:
    GRAPH_RETRIEVAL_AVAILABLE = False
    logger.warning("图谱检索组件未加载，图谱增强功能不可用")


class RagPipeline:
    """
    RAG 流程编排器

    🔧 核心流程：
    1. 查询预处理（Query Preprocessing）
    2. 缓存检查（Cache Check）
    3. 混合检索（Hybrid Retrieval）
    4. 重排序（Reranking）
    5. Prompt 构建（Prompt Building）
    6. LLM 生成（Answer Generation）
    7. 结果缓存（Result Caching）

    💡 特性：
    - 支持同步/异步调用
    - 可配置的检索策略
    - 自动缓存管理
    - 详细的日志记录
    """

    def __init__(
        self,
        embedding_model: Optional[EmbeddingModel] = None,
        llm_client: Optional[LLMClient] = None,
        bm25_retriever: Optional[BM25Retriever] = None,
        vector_retriever: Optional[VectorRetriever] = None,
        reranker: Optional[Reranker] = None,
        use_cache: bool = True,
        language: str = 'zh',
        enable_graph: bool = True,
        graph_weight: float = 0.3
    ):
        """
        初始化 RAG Pipeline

        参数：
            embedding_model: Embedding 模型实例
            llm_client: LLM 客户端实例
            bm25_retriever: BM25 检索器实例
            vector_retriever: 向量检索器实例
            reranker: 重排序器实例
            use_cache: 是否使用缓存
            language: 回答语言 ('zh' 或 'en')
            enable_graph: 是否启用图谱增强检索
            graph_weight: 图谱检索结果权重 (0.0-1.0)
        """
        self.use_cache = use_cache
        self.language = language
        self.enable_graph = enable_graph and GRAPH_RETRIEVAL_AVAILABLE
        self.graph_weight = graph_weight

        # 初始化组件（懒加载）
        self._embedding_model = embedding_model
        self._llm_client = llm_client
        self._bm25_retriever = bm25_retriever
        self._vector_retriever = vector_retriever
        self._reranker = reranker
        self._hybrid_retriever = None

        # 图谱增强组件
        self._graph_retriever = None
        self._graph_enhanced_retriever = None

        # 组件初始化标志
        self._initialized = False

        logger.info(
            f"RAG Pipeline 创建 | "
            f"缓存: {use_cache} | "
            f"语言: {language} | "
            f"图谱增强: {self.enable_graph}"
        )

    def _lazy_init(self):
        """
        懒加载初始化所有组件

        只在第一次调用时初始化，避免启动时的开销
        """
        if self._initialized:
            return

        logger.info("初始化 RAG Pipeline 组件...")

        # 1. 初始化 Embedding 模型
        if self._embedding_model is None:
            self._embedding_model = EmbeddingModel(
                model_name=settings.EMBEDDING_MODEL_NAME
            )

        # 2. 初始化 Embedder
        self._embedder = Embedder(
            embedding_model=self._embedding_model,
            batch_size=settings.EMBEDDING_BATCH_SIZE
        )

        # 3. 初始化 LLM 客户端
        if self._llm_client is None:
            self._llm_client = LLMClient()

        # 4. 初始化 BM25 检索器
        if self._bm25_retriever is None:
            self._bm25_retriever = BM25Retriever()

        # 5. 初始化向量检索器
        if self._vector_retriever is None:
            self._vector_retriever = VectorRetriever(
                collection_name=settings.MILVUS_COLLECTION_STANDARD,
                embedder=self._embedder,
                host=settings.MILVUS_HOST,
                port=str(settings.MILVUS_PORT),
                dim=settings.VECTOR_DIM
            )

        # 6. 初始化重排序器
        if self._reranker is None:
            try:
                self._reranker = Reranker()
            except Exception as e:
                logger.warning(f"Reranker 初始化失败，将不使用重排序: {e}")
                self._reranker = None

        # 7. 初始化混合检索器
        self._hybrid_retriever = HybridRetriever(
            bm25_retriever=self._bm25_retriever,
            vector_retriever=self._vector_retriever,
            reranker=self._reranker,
            fusion_method='rrf'
        )

        # 8. 初始化图谱增强组件（如果启用）
        if self.enable_graph and GRAPH_RETRIEVAL_AVAILABLE:
            try:
                # 图谱检索器
                self._graph_retriever = GraphRetriever()

                # 图谱增强检索器（三路融合）
                self._graph_enhanced_retriever = GraphEnhancedRetriever(
                    bm25_retriever=self._bm25_retriever,
                    vector_retriever=self._vector_retriever,
                    graph_retriever=self._graph_retriever,
                    reranker=self._reranker,
                    graph_weight=self.graph_weight
                )
                logger.info(f"图谱增强检索器已启用 | 图谱权重: {self.graph_weight}")
            except Exception as e:
                logger.warning(f"图谱增强组件初始化失败: {e}")
                self._graph_retriever = None
                self._graph_enhanced_retriever = None
                self.enable_graph = False

        self._initialized = True
        logger.info("RAG Pipeline 组件初始化完成")

    async def run(
        self,
        query: str,
        *,
        top_k: int = 5,
        project_id: Optional[str] = None,
        extra_context: Optional[str] = None,
        use_rerank: bool = True,
        skip_cache: bool = False,
        use_graph: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        执行 RAG 流程（异步）

        参数：
            query: 用户问题
            top_k: 检索文档数量
            project_id: 项目 ID（用于限定检索范围）
            extra_context: 额外上下文
            use_rerank: 是否使用重排序
            skip_cache: 是否跳过缓存
            use_graph: 是否使用图谱增强（None 表示使用默认配置）

        返回：
            {
                'answer': str,           # 生成的答案
                'sources': List[Dict],   # 来源文档
                'query': str,            # 原始问题
                'cached': bool,          # 是否来自缓存
                'graph_context': str,    # 图谱上下文（如果启用）
                'metadata': {
                    'retrieval_count': int,
                    'response_time': float,
                    'model': str,
                    'timestamp': str,
                    'graph_enhanced': bool
                }
            }
        """
        start_time = datetime.now()

        logger.info(f"RAG Pipeline 开始 | 问题: {query[:50]}...")

        # 懒加载初始化
        self._lazy_init()

        # Step 1: 检查缓存
        if self.use_cache and not skip_cache:
            cached_result = self._check_cache(query)
            if cached_result:
                cached_result['cached'] = True
                logger.info("命中缓存，直接返回")
                return cached_result

        # Step 2: 查询预处理
        processed_query = self._preprocess_query(query)

        # 确定是否使用图谱增强
        should_use_graph = use_graph if use_graph is not None else self.enable_graph

        # Step 3: 混合检索（支持图谱增强）
        retrieved_docs, graph_context = await self._retrieve(
            query=processed_query,
            top_k=top_k,
            project_id=project_id,
            use_rerank=use_rerank,
            use_graph=should_use_graph
        )

        # Step 4: 检查是否有检索结果
        if not retrieved_docs:
            logger.warning("未检索到相关文档")
            return self._generate_no_result_response(query, start_time)

        # Step 5: 构建 Prompt（包含图谱上下文）
        prompt = self._build_prompt(
            query=query,
            contexts=retrieved_docs,
            extra_context=extra_context,
            graph_context=graph_context
        )

        # Step 6: LLM 生成答案
        answer = await self._generate_answer(prompt)

        # Step 7: 构建结果
        result = self._build_result(
            query=query,
            answer=answer,
            sources=retrieved_docs,
            start_time=start_time,
            graph_context=graph_context,
            graph_enhanced=should_use_graph and graph_context is not None
        )

        # Step 8: 缓存结果
        if self.use_cache:
            self._cache_result(query, result)

        logger.info(
            f"RAG Pipeline 完成 | "
            f"检索: {len(retrieved_docs)} 条 | "
            f"耗时: {result['metadata']['response_time']:.2f}s"
        )

        return result

    def run_sync(
        self,
        query: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行 RAG 流程（同步）

        参数与 run() 相同
        """
        return asyncio.run(self.run(query, **kwargs))

    def _preprocess_query(self, query: str) -> str:
        """
        查询预处理

        处理：
        1. 去除多余空白
        2. 标准化标点符号
        3. 可选：查询扩展
        """
        # 基础清理
        processed = query.strip()
        processed = ' '.join(processed.split())

        return processed

    def _check_cache(self, query: str) -> Optional[Dict[str, Any]]:
        """检查缓存"""
        try:
            return redis_client.get_cached_query_result(query)
        except Exception as e:
            logger.warning(f"缓存检查失败: {e}")
            return None

    def _cache_result(self, query: str, result: Dict[str, Any]):
        """缓存结果"""
        try:
            # 不缓存某些字段
            cache_data = {
                'answer': result['answer'],
                'sources': result['sources'],
                'query': result['query']
            }
            redis_client.cache_query_result(query, cache_data)
        except Exception as e:
            logger.warning(f"结果缓存失败: {e}")

    async def _retrieve(
        self,
        query: str,
        top_k: int,
        project_id: Optional[str],
        use_rerank: bool,
        use_graph: bool = False
    ) -> tuple[List[Dict], Optional[str]]:
        """
        执行混合检索（支持图谱增强）

        参数：
            query: 查询文本
            top_k: 返回结果数量
            project_id: 项目过滤
            use_rerank: 是否重排序
            use_graph: 是否使用图谱增强

        返回：
            (检索结果列表, 图谱上下文)
        """
        try:
            # 构建过滤条件
            filters = None
            if project_id:
                filters = f"project_id == '{project_id}'"

            graph_context = None

            # 判断是否使用图谱增强检索
            if use_graph and self._graph_enhanced_retriever is not None:
                logger.info("使用图谱增强三路检索")

                # 使用图谱增强检索器（三路融合）
                results = await self._graph_enhanced_retriever.search_async(
                    query=query,
                    top_k=top_k,
                    use_rerank=use_rerank,
                    filters=filters,
                    enhance_with_graph=True
                )

                # 从检索结果中提取图谱上下文
                graph_context = self._graph_enhanced_retriever.get_graph_context_for_prompt(results)

                if graph_context:
                    logger.info(f"图谱上下文生成完成 | 长度: {len(graph_context)}")
            else:
                # 使用标准混合检索
                results = self._hybrid_retriever.search(
                    query=query,
                    top_k=top_k,
                    use_rerank=use_rerank,
                    filters=filters
                )

            return results, graph_context

        except Exception as e:
            logger.error(f"检索失败: {e}")
            return [], None

    def _build_prompt(
        self,
        query: str,
        contexts: List[Dict],
        extra_context: Optional[str],
        graph_context: Optional[str] = None
    ) -> str:
        """
        构建 LLM Prompt

        使用 QAPromptFactory 构建标准化的 Prompt
        支持图谱上下文增强
        """
        # 提取上下文文本
        context_items = []
        for i, doc in enumerate(contexts, 1):
            text = doc.get('text', '')
            source = doc.get('doc_id', f'文档{i}')
            score = doc.get('rerank_score', doc.get('score', 0))

            context_items.append({
                'text': text,
                'metadata': {
                    'source': source,
                    'score': score
                }
            })

        # 构建 Prompt
        prompt = QAPromptFactory.build_rag_prompt(
            query=query,
            contexts=context_items,
            language=self.language,
            max_context_length=3000,
            include_metadata=True
        )

        # 添加图谱知识上下文（优先级最高）
        if graph_context:
            graph_section = self._format_graph_context(graph_context)
            prompt = f"{graph_section}\n\n{prompt}"

        # 添加额外上下文
        if extra_context:
            prompt = f"{prompt}\n\n【额外信息】\n{extra_context}"

        return prompt

    def _format_graph_context(self, graph_context: str) -> str:
        """
        格式化图谱上下文

        将图谱知识以结构化方式嵌入 Prompt
        """
        if self.language == 'zh':
            return f"""【知识图谱参考】
以下是从工程知识图谱中提取的结构化信息，请优先参考：

{graph_context}

---"""
        else:
            return f"""【Knowledge Graph Reference】
The following structured information is extracted from the engineering knowledge graph. Please prioritize this:

{graph_context}

---"""

    async def _generate_answer(self, prompt: str) -> str:
        """
        调用 LLM 生成答案
        """
        try:
            # 构建消息
            messages = [
                {
                    "role": "system",
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            # 调用 LLM
            answer = await self._llm_client.chat_async(messages=messages)

            return answer

        except Exception as e:
            logger.error(f"LLM 生成失败: {e}")
            return self._get_fallback_answer()

    def _get_system_prompt(self) -> str:
        """获取系统 Prompt"""
        if self.language == 'zh':
            return """你是一个专业的知识问答助手。请基于提供的参考资料准确回答用户问题。

回答要求：
1. 必须基于参考资料回答，不要编造信息
2. 如果参考资料不足以回答问题，请明确说明
3. 引用具体内容时，标注来源
4. 回答要准确、专业、易懂"""
        else:
            return """You are a professional knowledge assistant. Answer questions accurately based on provided references.

Requirements:
1. Must answer based on references, do not fabricate
2. Clearly state if references are insufficient
3. Cite sources when quoting content
4. Be accurate, professional, and clear"""

    def _get_fallback_answer(self) -> str:
        """获取降级答案"""
        if self.language == 'zh':
            return "抱歉，系统暂时无法生成答案，请稍后重试。"
        else:
            return "Sorry, the system is temporarily unable to generate an answer. Please try again later."

    def _build_result(
        self,
        query: str,
        answer: str,
        sources: List[Dict],
        start_time: datetime,
        graph_context: Optional[str] = None,
        graph_enhanced: bool = False
    ) -> Dict[str, Any]:
        """构建返回结果"""
        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds()

        result = {
            'answer': answer,
            'sources': [
                {
                    'doc_id': doc.get('doc_id', ''),
                    'text': doc.get('text', '')[:500],  # 截断
                    'score': doc.get('rerank_score', doc.get('score', 0)),
                    'metadata': doc.get('metadata', {}),
                    'from_graph': doc.get('from_graph', False)  # 标记是否来自图谱
                }
                for doc in sources
            ],
            'query': query,
            'cached': False,
            'metadata': {
                'retrieval_count': len(sources),
                'response_time': response_time,
                'model': self._llm_client.model if self._llm_client else 'unknown',
                'timestamp': end_time.isoformat(),
                'graph_enhanced': graph_enhanced
            }
        }

        # 添加图谱上下文摘要
        if graph_context:
            result['graph_context'] = graph_context[:500] if len(graph_context) > 500 else graph_context

        return result

    def _generate_no_result_response(
        self,
        query: str,
        start_time: datetime
    ) -> Dict[str, Any]:
        """生成无结果的响应"""
        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds()

        if self.language == 'zh':
            answer = "抱歉，未能在知识库中找到与您问题相关的内容。请尝试换一种问法，或确认问题是否在知识库覆盖范围内。"
        else:
            answer = "Sorry, no relevant content was found in the knowledge base. Please try rephrasing your question."

        return {
            'answer': answer,
            'sources': [],
            'query': query,
            'cached': False,
            'metadata': {
                'retrieval_count': 0,
                'response_time': response_time,
                'model': 'none',
                'timestamp': end_time.isoformat(),
                'no_result': True,
                'graph_enhanced': False
            }
        }


# =========================================
# 💡 使用示例
# =========================================
"""
# 1. 基础使用（异步）
from services.rag.pipeline import RagPipeline
import asyncio

pipeline = RagPipeline()

async def main():
    result = await pipeline.run(
        query="建筑结构荷载如何计算？",
        top_k=5
    )
    print(f"答案: {result['answer']}")
    print(f"来源数: {len(result['sources'])}")

asyncio.run(main())


# 2. 同步调用
result = pipeline.run_sync(
    query="什么是恒荷载？",
    top_k=5
)
print(result['answer'])


# 3. 限定项目范围
result = await pipeline.run(
    query="项目进度如何？",
    top_k=5,
    project_id="project_001"
)


# 4. 跳过缓存
result = await pipeline.run(
    query="最新的规范要求是什么？",
    skip_cache=True
)


# 5. 添加额外上下文
result = await pipeline.run(
    query="如何计算楼面荷载？",
    extra_context="当前项目为住宅楼，地上20层"
)


# 6. 自定义组件
from services.llm.llm_client import LLMClient
from services.embedding.embedding_model import EmbeddingModel

custom_llm = LLMClient(
    api_base="http://localhost:8000/v1",
    model="qwen-plus"
)

custom_embedding = EmbeddingModel(
    model_name="BAAI/bge-large-zh-v1.5"
)

pipeline = RagPipeline(
    llm_client=custom_llm,
    embedding_model=custom_embedding,
    use_cache=False,
    language='zh'
)

result = await pipeline.run(query="...")


# 7. 图谱增强检索（默认启用）
pipeline = RagPipeline(
    enable_graph=True,      # 启用图谱增强
    graph_weight=0.3        # 图谱结果权重
)

result = await pipeline.run(
    query="KL-1 框架梁使用什么材料？",
    top_k=5
)
print(f"答案: {result['answer']}")
print(f"图谱增强: {result['metadata']['graph_enhanced']}")
if 'graph_context' in result:
    print(f"图谱上下文: {result['graph_context']}")


# 8. 禁用图谱增强（单次查询）
result = await pipeline.run(
    query="什么是剪力墙？",
    use_graph=False  # 本次查询不使用图谱
)


# 9. 完全禁用图谱增强
pipeline = RagPipeline(
    enable_graph=False  # 完全禁用图谱
)
"""
