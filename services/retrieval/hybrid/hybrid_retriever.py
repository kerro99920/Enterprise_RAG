"""
========================================
混合检索器（BM25 + Vector + Rerank）
========================================

📚 模块说明：
- 整合多种检索方法
- 自动融合和重排序
- 提供统一检索接口

🎯 核心功能：
1. 多路检索（BM25 + 向量）
2. 结果融合（RRF/加权融合）
3. 重排序优化
4. 一站式检索服务

========================================
"""

from typing import List, Dict, Optional, Literal
from loguru import logger

from services.retrieval.bm25_retriever import BM25Retriever
from services.retrieval.vector_retriever import VectorRetriever
from services.rerank.reranker import Reranker


class HybridRetriever:
    """
    混合检索器

    🔧 检索策略：
    1. BM25关键词检索
    2. 向量语义检索
    3. RRF融合
    4. Rerank重排序

    💡 优势：
    - 结合精确匹配和语义理解
    - 提高召回率和准确率
    - 适应多种查询场景
    """

    def __init__(
            self,
            bm25_retriever: Optional[BM25Retriever] = None,
            vector_retriever: Optional[VectorRetriever] = None,
            reranker: Optional[Reranker] = None,
            fusion_method: Literal['rrf', 'weighted'] = 'rrf'
    ):
        """
        初始化混合检索器

        参数：
            bm25_retriever: BM25检索器实例
            vector_retriever: 向量检索器实例
            reranker: 重排序器实例
            fusion_method: 融合方法 ('rrf' 或 'weighted')
        """
        self.bm25_retriever = bm25_retriever
        self.vector_retriever = vector_retriever
        self.reranker = reranker
        self.fusion_method = fusion_method

        # 检查至少有一个检索器
        if not bm25_retriever and not vector_retriever:
            raise ValueError("至少需要提供一个检索器（BM25或向量）")

        logger.info(
            f"混合检索器初始化 | "
            f"BM25: {bm25_retriever is not None} | "
            f"Vector: {vector_retriever is not None} | "
            f"Rerank: {reranker is not None} | "
            f"融合方法: {fusion_method}"
        )

    def search(
            self,
            query: str,
            top_k: int = 10,
            bm25_top_k: Optional[int] = None,
            vector_top_k: Optional[int] = None,
            use_rerank: bool = True,
            rerank_top_k: Optional[int] = None,
            filters: Optional[str] = None,
            fusion_weights: Optional[Dict[str, float]] = None
    ) -> List[Dict]:
        """
        混合检索

        参数：
            query: 查询文本
            top_k: 最终返回数量
            bm25_top_k: BM25检索数量（默认top_k*2）
            vector_top_k: 向量检索数量（默认top_k*2）
            use_rerank: 是否使用重排序
            rerank_top_k: 重排序后保留数量
            filters: 过滤条件（用于向量检索）
            fusion_weights: 加权融合权重

        返回：
            检索结果列表

        流程：
        1. BM25检索 + 向量检索（并行）
        2. 结果融合（RRF或加权）
        3. 重排序（可选）
        4. 返回Top-K
        """
        logger.info(f"混合检索 | 查询: {query[:50]}... | top_k: {top_k}")

        # 设置默认检索数量（召回更多候选）
        if bm25_top_k is None:
            bm25_top_k = top_k * 2
        if vector_top_k is None:
            vector_top_k = top_k * 2

        # Step 1: 多路检索
        bm25_results = []
        vector_results = []

        if self.bm25_retriever:
            logger.debug(f"BM25检索 | top_k: {bm25_top_k}")
            bm25_results = self.bm25_retriever.search(
                query=query,
                top_k=bm25_top_k,
                return_scores=True
            )

        if self.vector_retriever:
            logger.debug(f"向量检索 | top_k: {vector_top_k}")
            vector_results = self.vector_retriever.search(
                query=query,
                top_k=vector_top_k,
                filters=filters
            )

        # 如果只有一个检索器，直接返回
        if not bm25_results:
            fused_results = vector_results
        elif not vector_results:
            fused_results = bm25_results
        else:
            # Step 2: 结果融合
            fused_results = self._fuse_results(
                bm25_results,
                vector_results,
                fusion_weights
            )

        # 限制候选数量（为重排序准备）
        if rerank_top_k is None:
            rerank_top_k = min(top_k * 3, len(fused_results))

        fused_results = fused_results[:rerank_top_k]

        # Step 3: 重排序
        if use_rerank and self.reranker and fused_results:
            logger.debug(f"重排序 | 候选数: {len(fused_results)}")
            fused_results = self.reranker.rerank(
                query=query,
                documents=fused_results,
                text_key='text',
                top_k=None,  # 保留所有
                return_scores=True
            )

        # Step 4: 返回Top-K
        final_results = fused_results[:top_k]

        logger.info(
            f"混合检索完成 | "
            f"BM25: {len(bm25_results)} | "
            f"Vector: {len(vector_results)} | "
            f"融合: {len(fused_results)} | "
            f"最终: {len(final_results)}"
        )

        return final_results

    def _fuse_results(
            self,
            bm25_results: List[Dict],
            vector_results: List[Dict],
            fusion_weights: Optional[Dict[str, float]] = None
    ) -> List[Dict]:
        """
        融合BM25和向量检索结果

        参数：
            bm25_results: BM25结果
            vector_results: 向量检索结果
            fusion_weights: 加权融合权重

        返回：
            融合后的结果列表
        """
        if self.fusion_method == 'rrf':
            # RRF融合
            return self._rrf_fusion(bm25_results, vector_results)

        elif self.fusion_method == 'weighted':
            # 加权融合
            return self._weighted_fusion(
                bm25_results,
                vector_results,
                fusion_weights
            )

        else:
            raise ValueError(f"不支持的融合方法: {self.fusion_method}")

    def _rrf_fusion(
            self,
            bm25_results: List[Dict],
            vector_results: List[Dict],
            k: int = 60
    ) -> List[Dict]:
        """
        倒数排名融合（RRF）

        使用Reranker的RRF方法
        """
        if not self.reranker:
            # 如果没有reranker，手动实现简化版RRF
            return self._simple_rrf(bm25_results, vector_results, k)

        return self.reranker.reciprocal_rank_fusion(
            ranked_lists=[bm25_results, vector_results],
            k=k,
            doc_id_key='doc_id'
        )

    def _simple_rrf(
            self,
            bm25_results: List[Dict],
            vector_results: List[Dict],
            k: int = 60
    ) -> List[Dict]:
        """简化版RRF（不依赖Reranker）"""
        doc_scores = {}
        doc_data = {}

        # BM25结果
        for rank, doc in enumerate(bm25_results, 1):
            doc_id = doc.get('doc_id', id(doc))
            rrf_score = 1.0 / (k + rank)
            doc_scores[doc_id] = rrf_score
            doc_data[doc_id] = doc.copy()
            doc_data[doc_id]['bm25_rank'] = rank

        # 向量结果
        for rank, doc in enumerate(vector_results, 1):
            doc_id = doc.get('doc_id', id(doc))
            rrf_score = 1.0 / (k + rank)

            if doc_id in doc_scores:
                doc_scores[doc_id] += rrf_score
                doc_data[doc_id]['vector_rank'] = rank
            else:
                doc_scores[doc_id] = rrf_score
                doc_data[doc_id] = doc.copy()
                doc_data[doc_id]['vector_rank'] = rank

        # 排序
        sorted_docs = sorted(
            doc_data.values(),
            key=lambda x: doc_scores[x.get('doc_id', id(x))],
            reverse=True
        )

        # 添加RRF分数和排名
        for rank, doc in enumerate(sorted_docs, 1):
            doc['rrf_score'] = doc_scores[doc.get('doc_id', id(doc))]
            doc['fusion_rank'] = rank

        return sorted_docs

    def _weighted_fusion(
            self,
            bm25_results: List[Dict],
            vector_results: List[Dict],
            fusion_weights: Optional[Dict[str, float]] = None
    ) -> List[Dict]:
        """
        加权融合

        参数：
            fusion_weights: {'bm25': 0.5, 'vector': 0.5}
        """
        if fusion_weights is None:
            fusion_weights = {'bm25': 0.5, 'vector': 0.5}

        # 合并所有文档
        all_docs = {}

        # BM25结果
        for doc in bm25_results:
            doc_id = doc.get('doc_id', id(doc))
            doc_copy = doc.copy()
            doc_copy['bm25_score'] = doc.get('score', 0)
            all_docs[doc_id] = doc_copy

        # 向量结果
        for doc in vector_results:
            doc_id = doc.get('doc_id', id(doc))
            if doc_id in all_docs:
                all_docs[doc_id]['vector_score'] = doc.get('score', 0)
            else:
                doc_copy = doc.copy()
                doc_copy['vector_score'] = doc.get('score', 0)
                doc_copy['bm25_score'] = 0
                all_docs[doc_id] = doc_copy

        # 归一化并计算加权分数
        docs_list = list(all_docs.values())

        # 提取分数
        bm25_scores = [d.get('bm25_score', 0) for d in docs_list]
        vector_scores = [d.get('vector_score', 0) for d in docs_list]

        # 归一化
        def normalize(scores):
            if not scores or max(scores) == min(scores):
                return [1.0] * len(scores)
            min_s, max_s = min(scores), max(scores)
            return [(s - min_s) / (max_s - min_s) for s in scores]

        norm_bm25 = normalize(bm25_scores)
        norm_vector = normalize(vector_scores)

        # 计算加权分数
        for i, doc in enumerate(docs_list):
            weighted_score = (
                    norm_bm25[i] * fusion_weights.get('bm25', 0.5) +
                    norm_vector[i] * fusion_weights.get('vector', 0.5)
            )
            doc['weighted_score'] = weighted_score

        # 排序
        docs_list.sort(key=lambda x: x['weighted_score'], reverse=True)

        # 添加排名
        for rank, doc in enumerate(docs_list, 1):
            doc['fusion_rank'] = rank

        return docs_list


# =========================================
# 💡 使用示例
# =========================================
"""
from services.retrieval.hybrid_retriever import HybridRetriever
from services.retrieval.bm25_retriever import BM25Retriever
from services.retrieval.vector_retriever import VectorRetriever
from services.rerank.reranker import Reranker

# 1. 初始化各组件
bm25 = BM25Retriever()
vector = VectorRetriever(collection_name='docs', embedder=embedder)
reranker = Reranker()

# 2. 创建混合检索器
hybrid = HybridRetriever(
    bm25_retriever=bm25,
    vector_retriever=vector,
    reranker=reranker,
    fusion_method='rrf'  # 或 'weighted'
)

# 3. 检索
query = "建筑结构荷载如何计算？"
results = hybrid.search(
    query=query,
    top_k=10,
    use_rerank=True
)

for result in results:
    print(f"排名: {result.get('fusion_rank', result.get('rerank_rank'))}")
    print(f"文档: {result['text'][:100]}")
    if 'rerank_score' in result:
        print(f"Rerank分数: {result['rerank_score']:.4f}")
    print("---")


# 4. 使用加权融合
hybrid_weighted = HybridRetriever(
    bm25_retriever=bm25,
    vector_retriever=vector,
    reranker=reranker,
    fusion_method='weighted'
)

results = hybrid_weighted.search(
    query=query,
    top_k=10,
    fusion_weights={'bm25': 0.4, 'vector': 0.6}
)


# 5. 只使用BM25（无向量库时）
hybrid_bm25_only = HybridRetriever(
    bm25_retriever=bm25,
    vector_retriever=None
)

results = hybrid_bm25_only.search(query, top_k=10)
"""