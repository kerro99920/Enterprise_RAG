"""
========================================
Rerank重排序器
========================================

📚 模块说明：
- 对初步检索结果进行精准重排序
- 使用交叉编码器提高准确率
- 提升Top-K结果质量

🎯 核心功能：
1. 交叉编码器重排序
2. 分数归一化
3. 批量重排序
4. 结果融合

========================================
"""

from typing import List, Dict, Tuple, Optional
import numpy as np

from FlagEmbedding import FlagReranker
from loguru import logger


class Reranker:
    """
    重排序器（基于BGE Reranker）

    🔧 技术特点：
    - BGE Reranker模型（BAAI）
    - 交叉编码器架构
    - 精准相关性评分

    💡 使用场景：
    - 提升Top-K精度
    - 混合检索融合
    - 二次精排
    """

    def __init__(
            self,
            model_name: str = 'BAAI/bge-reranker-large',
            device: Optional[str] = None,
            batch_size: int = 32,
            max_length: int = 512
    ):
        """
        初始化重排序器

        参数：
            model_name: 重排序模型名称
                - 'BAAI/bge-reranker-large': 大模型，精度最高
                - 'BAAI/bge-reranker-base': 基础模型，速度快
            device: 设备 ('cuda', 'cpu', None自动选择)
            batch_size: 批处理大小
            max_length: 最大文本长度
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.max_length = max_length

        # 自动选择设备
        if device is None:
            import torch
            if torch.cuda.is_available():
                device = 'cuda'
            else:
                device = 'cpu'

        self.device = device

        logger.info(
            f"初始化Reranker | "
            f"模型: {model_name} | "
            f"设备: {device}"
        )

        # 加载模型
        self.model = self._load_model()

        logger.info("Reranker加载完成")

    def _load_model(self) -> FlagReranker:
        """加载重排序模型"""
        try:
            model = FlagReranker(
                self.model_name,
                use_fp16=True if self.device == 'cuda' else False
            )
            return model
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise

    def rerank(
            self,
            query: str,
            documents: List[Dict],
            text_key: str = 'text',
            top_k: Optional[int] = None,
            return_scores: bool = True
    ) -> List[Dict]:
        """
        重排序文档

        参数：
            query: 查询文本
            documents: 文档列表
                [
                    {'text': '文档内容', 'score': 0.8, ...},
                    ...
                ]
            text_key: 文本字段键名
            top_k: 返回前K个（None则返回全部）
            return_scores: 是否返回重排序分数

        返回：
            重排序后的文档列表
        """
        if not documents:
            return []

        if not query or not query.strip():
            logger.warning("查询为空，返回原始排序")
            return documents

        logger.debug(f"重排序 | 查询: {query[:50]}... | 文档数: {len(documents)}")

        # 提取文本
        texts = [doc.get(text_key, '') for doc in documents]

        # 构建query-document对
        pairs = [[query, text] for text in texts]

        # 批量计算相关性分数
        try:
            scores = self.model.compute_score(
                pairs,
                batch_size=self.batch_size,
                max_length=self.max_length
            )

            # 确保scores是列表
            if isinstance(scores, (int, float)):
                scores = [scores]
            elif not isinstance(scores, list):
                scores = scores.tolist()

        except Exception as e:
            logger.error(f"重排序计算失败: {e}")
            return documents

        # 组合结果
        reranked_docs = []
        for doc, score in zip(documents, scores):
            doc_copy = doc.copy()
            if return_scores:
                doc_copy['rerank_score'] = float(score)
            reranked_docs.append(doc_copy)

        # 按重排序分数降序排序
        reranked_docs.sort(
            key=lambda x: x.get('rerank_score', 0),
            reverse=True
        )

        # 更新排名
        for rank, doc in enumerate(reranked_docs, 1):
            doc['rerank_rank'] = rank

        # 截取Top-K
        if top_k is not None:
            reranked_docs = reranked_docs[:top_k]

        logger.debug(f"重排序完成 | 返回: {len(reranked_docs)} 个结果")

        return reranked_docs

    def fuse_scores(
            self,
            documents: List[Dict],
            weights: Optional[Dict[str, float]] = None,
            normalize: bool = True
    ) -> List[Dict]:
        """
        融合多个检索分数

        参数：
            documents: 包含多个分数的文档列表
                [
                    {
                        'text': '...',
                        'bm25_score': 0.8,
                        'vector_score': 0.9,
                        'rerank_score': 0.95
                    },
                    ...
                ]
            weights: 各分数的权重
                {'bm25_score': 0.3, 'vector_score': 0.3, 'rerank_score': 0.4}
            normalize: 是否归一化分数

        返回：
            融合后的文档列表（按融合分数排序）
        """
        if not documents:
            return []

        # 默认权重
        if weights is None:
            weights = {
                'bm25_score': 0.3,
                'vector_score': 0.3,
                'rerank_score': 0.4
            }

        logger.debug(f"融合分数 | 权重: {weights}")

        # 归一化函数
        def normalize_scores(scores: List[float]) -> List[float]:
            if not scores or max(scores) == min(scores):
                return [1.0] * len(scores)
            min_score = min(scores)
            max_score = max(scores)
            return [(s - min_score) / (max_score - min_score) for s in scores]

        # 提取各类分数
        score_types = list(weights.keys())
        score_matrix = {k: [] for k in score_types}

        for doc in documents:
            for score_type in score_types:
                score = doc.get(score_type, 0)
                score_matrix[score_type].append(score)

        # 归一化
        if normalize:
            for score_type in score_types:
                score_matrix[score_type] = normalize_scores(
                    score_matrix[score_type]
                )

        # 计算融合分数
        fused_docs = []
        for idx, doc in enumerate(documents):
            doc_copy = doc.copy()

            # 加权融合
            fused_score = 0.0
            for score_type, weight in weights.items():
                score = score_matrix[score_type][idx]
                fused_score += score * weight

            doc_copy['fused_score'] = fused_score
            fused_docs.append(doc_copy)

        # 排序
        fused_docs.sort(
            key=lambda x: x['fused_score'],
            reverse=True
        )

        # 更新排名
        for rank, doc in enumerate(fused_docs, 1):
            doc['fused_rank'] = rank

        logger.debug("分数融合完成")

        return fused_docs

    def reciprocal_rank_fusion(
            self,
            ranked_lists: List[List[Dict]],
            k: int = 60,
            doc_id_key: str = 'doc_id'
    ) -> List[Dict]:
        """
        倒数排名融合（RRF）

        算法：
        RRF(d) = Σ 1 / (k + rank_i(d))

        参数：
            ranked_lists: 多个排序列表
                [
                    [doc1, doc2, doc3],  # BM25结果
                    [doc2, doc1, doc4],  # Vector结果
                ]
            k: RRF参数（通常60）
            doc_id_key: 文档ID字段名

        返回：
            融合后的文档列表
        """
        logger.debug(f"RRF融合 | 列表数: {len(ranked_lists)} | k={k}")

        # 计算每个文档的RRF分数
        doc_scores = {}
        doc_data = {}

        for rank_list in ranked_lists:
            for rank, doc in enumerate(rank_list, 1):
                doc_id = doc.get(doc_id_key, id(doc))

                # RRF分数
                rrf_score = 1.0 / (k + rank)

                if doc_id in doc_scores:
                    doc_scores[doc_id] += rrf_score
                else:
                    doc_scores[doc_id] = rrf_score
                    doc_data[doc_id] = doc

        # 排序
        sorted_doc_ids = sorted(
            doc_scores.keys(),
            key=lambda x: doc_scores[x],
            reverse=True
        )

        # 构建结果
        fused_results = []
        for rank, doc_id in enumerate(sorted_doc_ids, 1):
            doc = doc_data[doc_id].copy()
            doc['rrf_score'] = doc_scores[doc_id]
            doc['rrf_rank'] = rank
            fused_results.append(doc)

        logger.debug(f"RRF融合完成 | 结果数: {len(fused_results)}")

        return fused_results


# =========================================
# 💡 使用示例
# =========================================
"""
from services.rerank.reranker import Reranker

# 1. 基础重排序
reranker = Reranker(model_name='BAAI/bge-reranker-large')

query = "建筑结构荷载如何计算？"
documents = [
    {'text': '建筑结构荷载规范 GB50009-2012', 'score': 0.8},
    {'text': '建筑抗震设计规范', 'score': 0.7},
    {'text': '混凝土结构设计规范', 'score': 0.6}
]

reranked = reranker.rerank(query, documents, top_k=3)

for doc in reranked:
    print(f"排名: {doc['rerank_rank']}")
    print(f"重排序分数: {doc['rerank_score']:.4f}")
    print(f"原始分数: {doc['score']:.4f}")
    print(f"文档: {doc['text']}")
    print("---")


# 2. 分数融合
documents_with_scores = [
    {
        'text': '文档1',
        'bm25_score': 0.8,
        'vector_score': 0.6,
        'rerank_score': 0.9
    },
    {
        'text': '文档2',
        'bm25_score': 0.6,
        'vector_score': 0.9,
        'rerank_score': 0.7
    }
]

weights = {
    'bm25_score': 0.3,
    'vector_score': 0.3,
    'rerank_score': 0.4
}

fused = reranker.fuse_scores(documents_with_scores, weights=weights)

for doc in fused:
    print(f"融合排名: {doc['fused_rank']}")
    print(f"融合分数: {doc['fused_score']:.4f}")


# 3. RRF融合（混合检索）
bm25_results = [doc1, doc2, doc3]
vector_results = [doc2, doc1, doc4]

rrf_results = reranker.reciprocal_rank_fusion(
    ranked_lists=[bm25_results, vector_results],
    k=60
)

for doc in rrf_results:
    print(f"RRF排名: {doc['rrf_rank']}")
    print(f"RRF分数: {doc['rrf_score']:.4f}")
"""