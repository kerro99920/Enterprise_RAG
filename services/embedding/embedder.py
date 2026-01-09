"""
========================================
向量化服务
========================================

📚 模块说明：
- 文档分块向量化
- 批量处理优化
- 向量缓存管理

🎯 核心功能：
1. 文档级向量化
2. 分块向量化
3. 增量向量化
4. 向量持久化

========================================
"""

import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path

import numpy as np
from loguru import logger

from services.embedding.embedding_model import EmbeddingModel
from services.document.splitter import Chunk


class Embedder:
    """
    向量化服务

    🔧 核心职责：
    - 将文档块转换为向量
    - 管理向量化流程
    - 优化批处理性能

    💡 特性：
    - 自动批处理
    - 向量缓存
    - 错误重试
    """

    def __init__(
            self,
            embedding_model: Optional[EmbeddingModel] = None,
            batch_size: int = 32,
            cache_dir: Optional[str] = None
    ):
        """
        初始化向量化服务

        参数：
            embedding_model: Embedding模型实例
            batch_size: 批处理大小
            cache_dir: 向量缓存目录
        """
        self.embedding_model = embedding_model or EmbeddingModel()
        self.batch_size = batch_size
        self.cache_dir = Path(cache_dir) if cache_dir else None

        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"初始化向量化服务 | "
            f"模型: {self.embedding_model.model_name} | "
            f"batch_size: {batch_size}"
        )

    def embed_chunks(
            self,
            chunks: List[Chunk],
            show_progress: bool = True
    ) -> List[Dict]:
        """
        向量化文档块列表

        参数：
            chunks: 文档块列表
            show_progress: 是否显示进度

        返回：
            包含向量的块数据列表
            [
                {
                    'text': str,
                    'embedding': np.ndarray,
                    'metadata': dict,
                    ...
                }
            ]
        """
        if not chunks:
            logger.warning("输入块列表为空")
            return []

        logger.info(f"开始向量化 | 块数: {len(chunks)}")

        # 提取文本
        texts = [chunk.text for chunk in chunks]

        # 批量编码
        try:
            embeddings = self.embedding_model.encode(
                texts,
                batch_size=self.batch_size,
                show_progress=show_progress
            )

            # 组合结果
            embedded_chunks = []
            for chunk, embedding in zip(chunks, embeddings):
                embedded_chunk = {
                    'text': chunk.text,
                    'embedding': embedding,
                    'start_idx': chunk.start_idx,
                    'end_idx': chunk.end_idx,
                    'metadata': chunk.metadata.copy(),
                    'embedding_dim': len(embedding)
                }
                embedded_chunks.append(embedded_chunk)

            logger.info(
                f"向量化完成 | "
                f"块数: {len(embedded_chunks)} | "
                f"向量维度: {len(embeddings[0])}"
            )

            return embedded_chunks

        except Exception as e:
            logger.error(f"向量化失败: {e}")
            raise

    def embed_documents(
            self,
            documents: List[Dict],
            text_key: str = 'text',
            metadata_key: str = 'metadata'
    ) -> List[Dict]:
        """
        向量化文档列表（整文档，非分块）

        参数：
            documents: 文档列表，每个文档是字典
            text_key: 文本字段的键名
            metadata_key: 元数据字段的键名

        返回：
            包含向量的文档列表
        """
        if not documents:
            return []

        logger.info(f"向量化文档 | 数量: {len(documents)}")

        # 提取文本
        texts = [doc.get(text_key, '') for doc in documents]

        # 过滤空文本
        valid_indices = [i for i, t in enumerate(texts) if t and t.strip()]
        valid_texts = [texts[i] for i in valid_indices]

        if not valid_texts:
            logger.warning("所有文档文本为空")
            return documents

        # 批量编码
        embeddings = self.embedding_model.encode(
            valid_texts,
            batch_size=self.batch_size,
            show_progress=True
        )

        # 添加向量到文档
        embedding_idx = 0
        for doc_idx, doc in enumerate(documents):
            if doc_idx in valid_indices:
                doc['embedding'] = embeddings[embedding_idx]
                doc['embedding_dim'] = len(embeddings[embedding_idx])
                embedding_idx += 1
            else:
                # 空文档，使用零向量
                doc['embedding'] = np.zeros(self.embedding_model.dimension)
                doc['embedding_dim'] = self.embedding_model.dimension

        logger.info(f"文档向量化完成 | 成功: {len(valid_indices)}/{len(documents)}")

        return documents

    def embed_query(self, query: str) -> np.ndarray:
        """
        向量化查询文本（单个）

        参数：
            query: 查询文本

        返回：
            查询向量
        """
        if not query or not query.strip():
            logger.warning("查询文本为空，返回零向量")
            return np.zeros(self.embedding_model.dimension)

        logger.debug(f"向量化查询: {query[:50]}...")

        return self.embedding_model.encode_queries(query)

    def embed_queries(self, queries: List[str]) -> np.ndarray:
        """
        批量向量化查询

        参数：
            queries: 查询列表

        返回：
            查询向量矩阵 shape=(n, dimension)
        """
        if not queries:
            return np.array([])

        logger.debug(f"批量向量化查询 | 数量: {len(queries)}")

        return self.embedding_model.encode_queries(
            queries,
            batch_size=self.batch_size
        )

    def save_embeddings(
            self,
            embedded_chunks: List[Dict],
            filename: str
    ) -> str:
        """
        保存向量到文件

        参数：
            embedded_chunks: 包含向量的块列表
            filename: 文件名

        返回：
            保存路径
        """
        if not self.cache_dir:
            raise ValueError("未设置cache_dir，无法保存向量")

        filepath = self.cache_dir / filename

        # 将numpy数组转为列表以便JSON序列化
        serializable_chunks = []
        for chunk in embedded_chunks:
            chunk_copy = chunk.copy()
            if isinstance(chunk_copy.get('embedding'), np.ndarray):
                chunk_copy['embedding'] = chunk_copy['embedding'].tolist()
            serializable_chunks.append(chunk_copy)

        # 保存为JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(serializable_chunks, f, ensure_ascii=False, indent=2)

        logger.info(f"向量已保存: {filepath}")

        return str(filepath)

    def load_embeddings(self, filename: str) -> List[Dict]:
        """
        从文件加载向量

        参数：
            filename: 文件名

        返回：
            包含向量的块列表
        """
        if not self.cache_dir:
            raise ValueError("未设置cache_dir，无法加载向量")

        filepath = self.cache_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(f"向量文件不存在: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            chunks = json.load(f)

        # 将列表转回numpy数组
        for chunk in chunks:
            if 'embedding' in chunk and isinstance(chunk['embedding'], list):
                chunk['embedding'] = np.array(chunk['embedding'])

        logger.info(f"向量已加载: {filepath} | 块数: {len(chunks)}")

        return chunks

    def get_embedding_stats(
            self,
            embedded_chunks: List[Dict]
    ) -> Dict:
        """
        获取向量统计信息

        参数：
            embedded_chunks: 包含向量的块列表

        返回：
            统计信息字典
        """
        if not embedded_chunks:
            return {}

        embeddings = np.array([c['embedding'] for c in embedded_chunks])

        stats = {
            'count': len(embedded_chunks),
            'dimension': embeddings.shape[1],
            'mean_norm': float(np.mean(np.linalg.norm(embeddings, axis=1))),
            'std_norm': float(np.std(np.linalg.norm(embeddings, axis=1))),
            'min_norm': float(np.min(np.linalg.norm(embeddings, axis=1))),
            'max_norm': float(np.max(np.linalg.norm(embeddings, axis=1)))
        }

        return stats


# =========================================
# 💡 使用示例
# =========================================
"""
from services.embedding.embedder import Embedder
from services.embedding.embedding_model import EmbeddingModel
from services.document.splitter import DocumentSplitter

# 1. 初始化
model = EmbeddingModel(model_name='BAAI/bge-large-zh-v1.5')
embedder = Embedder(
    embedding_model=model,
    batch_size=32,
    cache_dir='data/embeddings'
)

# 2. 向量化文档块
splitter = DocumentSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split(long_text, method='recursive')

embedded_chunks = embedder.embed_chunks(chunks, show_progress=True)

print(f"向量化完成: {len(embedded_chunks)}个块")
print(f"向量维度: {embedded_chunks[0]['embedding_dim']}")


# 3. 向量化查询
query = "建筑荷载如何计算？"
query_embedding = embedder.embed_query(query)
print(f"查询向量: {query_embedding.shape}")


# 4. 保存和加载向量
embedder.save_embeddings(embedded_chunks, 'doc_chunks.json')
loaded_chunks = embedder.load_embeddings('doc_chunks.json')


# 5. 获取统计信息
stats = embedder.get_embedding_stats(embedded_chunks)
print(f"向量统计: {stats}")


# 6. 批量向量化文档
documents = [
    {'text': '文档1内容', 'metadata': {'id': 1}},
    {'text': '文档2内容', 'metadata': {'id': 2}}
]

embedded_docs = embedder.embed_documents(documents)
for doc in embedded_docs:
    print(f"文档ID: {doc['metadata']['id']}, 向量维度: {doc['embedding_dim']}")
"""