"""
========================================
Embedding模型管理器
========================================

📚 模块说明：
- 加载和管理向量化模型
- 支持多种Embedding模型
- 统一的向量化接口

🎯 核心功能：
1. 模型加载和缓存
2. 批量向量化
3. 相似度计算
4. 模型切换

========================================
"""

import os
from typing import List, Union, Optional, Dict
from pathlib import Path

import torch
import numpy as np
from sentence_transformers import SentenceTransformer
from loguru import logger


class EmbeddingModel:
    """
    Embedding模型管理器

    🔧 支持的模型：
    - BAAI/bge-large-zh-v1.5 (推荐中文)
    - BAAI/bge-base-zh-v1.5
    - shibing624/text2vec-base-chinese
    - 其他SentenceTransformer兼容模型

    💡 特性：
    - 自动设备选择（GPU/CPU）
    - 批量处理优化
    - 模型缓存
    """

    # 推荐模型配置
    RECOMMENDED_MODELS = {
        'bge-large-zh': {
            'model_name': 'BAAI/bge-large-zh-v1.5',
            'dimension': 1024,
            'max_length': 512,
            'description': 'BGE大模型，中文最佳性能'
        },
        'bge-base-zh': {
            'model_name': 'BAAI/bge-base-zh-v1.5',
            'dimension': 768,
            'max_length': 512,
            'description': 'BGE基础模型，速度快'
        },
        'text2vec': {
            'model_name': 'shibing624/text2vec-base-chinese',
            'dimension': 768,
            'max_length': 256,
            'description': 'Text2Vec，轻量级'
        }
    }

    def __init__(
            self,
            model_name: str = 'BAAI/bge-large-zh-v1.5',
            device: Optional[str] = None,
            cache_dir: Optional[str] = None,
            normalize_embeddings: bool = True
    ):
        """
        初始化Embedding模型

        参数：
            model_name: 模型名称或路径
            device: 设备 ('cuda', 'cpu', 'mps' 或 None自动选择)
            cache_dir: 模型缓存目录
            normalize_embeddings: 是否归一化向量（推荐True）
        """
        self.model_name = model_name
        self.normalize_embeddings = normalize_embeddings

        # 自动选择设备
        if device is None:
            if torch.cuda.is_available():
                device = 'cuda'
            elif torch.backends.mps.is_available():
                device = 'mps'
            else:
                device = 'cpu'

        self.device = device
        self.cache_dir = cache_dir or os.path.join(
            Path.home(),
            '.cache',
            'huggingface',
            'hub'
        )

        logger.info(
            f"初始化Embedding模型 | "
            f"模型: {model_name} | "
            f"设备: {device} | "
            f"归一化: {normalize_embeddings}"
        )

        # 加载模型
        self.model = self._load_model()
        self.dimension = self.model.get_sentence_embedding_dimension()

        logger.info(f"模型加载完成 | 向量维度: {self.dimension}")

    def _load_model(self) -> SentenceTransformer:
        """加载SentenceTransformer模型"""
        try:
            model = SentenceTransformer(
                self.model_name,
                device=self.device,
                cache_folder=self.cache_dir
            )

            # 设置为评估模式
            model.eval()

            return model

        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise

    def encode(
            self,
            texts: Union[str, List[str]],
            batch_size: int = 32,
            show_progress: bool = False,
            convert_to_numpy: bool = True
    ) -> Union[np.ndarray, torch.Tensor]:
        """
        将文本编码为向量

        参数：
            texts: 单个文本或文本列表
            batch_size: 批处理大小
            show_progress: 是否显示进度条
            convert_to_numpy: 是否转为numpy数组

        返回：
            向量数组 shape=(n, dimension)
        """
        # 统一处理为列表
        if isinstance(texts, str):
            texts = [texts]
            single_text = True
        else:
            single_text = False

        # 过滤空文本
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            logger.warning("输入包含空文本，返回零向量")
            return np.zeros((len(texts), self.dimension))

        logger.debug(f"编码文本 | 数量: {len(valid_texts)} | batch_size: {batch_size}")

        try:
            # 使用模型编码
            embeddings = self.model.encode(
                valid_texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=convert_to_numpy,
                normalize_embeddings=self.normalize_embeddings
            )

            # 如果是单个文本，返回一维向量
            if single_text and convert_to_numpy:
                return embeddings[0]

            return embeddings

        except Exception as e:
            logger.error(f"文本编码失败: {e}")
            raise

    def encode_queries(
            self,
            queries: Union[str, List[str]],
            **kwargs
    ) -> Union[np.ndarray, torch.Tensor]:
        """
        编码查询文本（为查询优化）

        注意：某些模型对查询和文档使用不同的编码
        """
        # BGE模型需要添加查询指令
        if 'bge' in self.model_name.lower():
            if isinstance(queries, str):
                queries = f"为这个句子生成表示以用于检索相关文章：{queries}"
            else:
                queries = [
                    f"为这个句子生成表示以用于检索相关文章：{q}"
                    for q in queries
                ]

        return self.encode(queries, **kwargs)

    def similarity(
            self,
            embeddings1: np.ndarray,
            embeddings2: np.ndarray,
            metric: str = 'cosine'
    ) -> Union[float, np.ndarray]:
        """
        计算向量相似度

        参数：
            embeddings1: 向量1或向量矩阵1
            embeddings2: 向量2或向量矩阵2
            metric: 相似度度量 ('cosine', 'dot', 'euclidean')

        返回：
            相似度分数
        """
        if metric == 'cosine':
            # 余弦相似度
            if self.normalize_embeddings:
                # 如果已归一化，直接点积
                return np.dot(embeddings1, embeddings2.T)
            else:
                # 未归一化，计算余弦
                norm1 = np.linalg.norm(embeddings1, axis=-1, keepdims=True)
                norm2 = np.linalg.norm(embeddings2, axis=-1, keepdims=True)
                return np.dot(embeddings1, embeddings2.T) / (norm1 * norm2.T)

        elif metric == 'dot':
            # 点积
            return np.dot(embeddings1, embeddings2.T)

        elif metric == 'euclidean':
            # 欧氏距离（越小越相似）
            return -np.linalg.norm(
                embeddings1[:, None] - embeddings2,
                axis=-1
            )

        else:
            raise ValueError(f"不支持的相似度度量: {metric}")

    def get_model_info(self) -> Dict:
        """获取模型信息"""
        return {
            'model_name': self.model_name,
            'dimension': self.dimension,
            'device': self.device,
            'normalize_embeddings': self.normalize_embeddings,
            'max_seq_length': self.model.max_seq_length
        }

    @classmethod
    def list_recommended_models(cls) -> Dict:
        """列出推荐的模型配置"""
        return cls.RECOMMENDED_MODELS

    def __repr__(self) -> str:
        return (
            f"EmbeddingModel("
            f"model='{self.model_name}', "
            f"dim={self.dimension}, "
            f"device='{self.device}')"
        )


# =========================================
# 💡 使用示例
# =========================================
"""
from services.embedding.embedding_model import EmbeddingModel

# 1. 基础使用
model = EmbeddingModel(
    model_name='BAAI/bge-large-zh-v1.5',
    device='cuda'  # 或 'cpu'
)

# 编码单个文本
text = "建筑结构荷载规范"
embedding = model.encode(text)
print(f"向量维度: {embedding.shape}")  # (1024,)

# 编码多个文本
texts = ["文本1", "文本2", "文本3"]
embeddings = model.encode(texts, batch_size=32)
print(f"向量矩阵: {embeddings.shape}")  # (3, 1024)


# 2. 查询编码（为检索优化）
query = "什么是建筑荷载？"
query_embedding = model.encode_queries(query)


# 3. 相似度计算
text1 = "建筑结构设计"
text2 = "结构荷载计算"

emb1 = model.encode(text1)
emb2 = model.encode(text2)

similarity = model.similarity(emb1, emb2)
print(f"相似度: {similarity:.4f}")


# 4. 批量相似度
query_emb = model.encode("建筑")
doc_embs = model.encode(["建筑设计", "软件开发", "结构工程"])

similarities = model.similarity(query_emb, doc_embs)
print(f"相似度: {similarities}")


# 5. 查看模型信息
info = model.get_model_info()
print(f"模型信息: {info}")


# 6. 查看推荐模型
models = EmbeddingModel.list_recommended_models()
for key, config in models.items():
    print(f"{key}: {config['description']}")
"""