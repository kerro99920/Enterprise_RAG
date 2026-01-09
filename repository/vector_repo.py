"""
========================================
Milvus向量数据库访问层 (Repository)
========================================

📚 模块说明：
- 封装Milvus向量数据库的所有操作
- 实现分层向量库管理
- 提供向量检索接口

🎯 核心功能：
1. 向量库的创建和管理
2. 向量的插入、删除、搜索
3. 分层检索策略

========================================
"""
from typing import List, Dict, Any, Optional, Tuple
from pymilvus import (
    connections, Collection, FieldSchema,
    CollectionSchema, DataType, utility
)
import numpy as np

from core.config import settings
from core.constants import MilvusCollection, MilvusIndexParams, SearchParams
from core.logger import logger, log_execution


class VectorRepository:
    """
    Milvus向量数据库访问类

    🎯 职责：
    - 管理三层向量库（规范库、项目库、合同库）
    - 向量的增删改查
    - 语义相似度搜索
    """

    def __init__(self):
        """
        初始化Milvus连接
        """
        self._connect_milvus()
        self.collections = {}  # 缓存Collection对象

    # =========================================
    # 连接管理
    # =========================================

    def _connect_milvus(self):
        """
        连接到Milvus服务器

        📌 连接信息从配置文件读取
        """
        try:
            # 检查是否已连接
            if connections.has_connection("default"):
                logger.info("Milvus已连接")
                return

            # 建立连接
            connections.connect(
                alias="default",
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT,
                user=settings.MILVUS_USER if settings.MILVUS_USER else None,
                password=settings.MILVUS_PASSWORD if settings.MILVUS_PASSWORD else None
            )

            logger.info(f"成功连接到Milvus: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")

        except Exception as e:
            logger.error(f"连接Milvus失败: {str(e)}")
            raise

    def disconnect(self):
        """断开Milvus连接"""
        try:
            connections.disconnect("default")
            logger.info("断开Milvus连接")
        except Exception as e:
            logger.error(f"断开Milvus连接失败: {str(e)}")

    # =========================================
    # 集合（Collection）管理
    # =========================================

    @log_execution("创建Milvus集合")
    def create_collection(
            self,
            collection_name: str,
            description: str = ""
    ) -> Collection:
        """
        创建向量集合

        参数：
            collection_name: 集合名称
            description: 集合描述

        返回：
            Collection: 创建的集合对象

        🏗️ 集合结构：
        - id: 主键（自增）
        - vector_id: 向量ID（对应PostgreSQL中的chunk_id）
        - embedding: 向量（768维）
        - doc_id: 文档ID
        - doc_type: 文档类型
        - permission_level: 权限级别
        - metadata: 元数据（JSON）
        """
        try:
            # 检查集合是否已存在
            if utility.has_collection(collection_name):
                logger.warning(f"集合已存在: {collection_name}")
                return Collection(collection_name)

            # 定义字段
            fields = [
                # 主键字段（自增ID）
                FieldSchema(
                    name="id",
                    dtype=DataType.INT64,
                    is_primary=True,
                    auto_id=True,
                    description="主键ID"
                ),

                # 向量ID（关联PostgreSQL）
                FieldSchema(
                    name="vector_id",
                    dtype=DataType.VARCHAR,
                    max_length=100,
                    description="向量ID（对应chunk_id）"
                ),

                # 向量字段
                FieldSchema(
                    name="embedding",
                    dtype=DataType.FLOAT_VECTOR,
                    dim=settings.VECTOR_DIM,
                    description="文本向量"
                ),

                # 文档ID
                FieldSchema(
                    name="doc_id",
                    dtype=DataType.VARCHAR,
                    max_length=36,
                    description="文档ID"
                ),

                # 文档类型
                FieldSchema(
                    name="doc_type",
                    dtype=DataType.VARCHAR,
                    max_length=50,
                    description="文档类型"
                ),

                # 权限级别
                FieldSchema(
                    name="permission_level",
                    dtype=DataType.VARCHAR,
                    max_length=50,
                    description="权限级别"
                ),

                # 页码
                FieldSchema(
                    name="page_num",
                    dtype=DataType.INT32,
                    description="页码"
                ),
            ]

            # 创建集合Schema
            schema = CollectionSchema(
                fields=fields,
                description=description
            )

            # 创建集合
            collection = Collection(
                name=collection_name,
                schema=schema
            )

            logger.info(f"创建集合成功: {collection_name}")
            return collection

        except Exception as e:
            logger.error(f"创建集合失败: {str(e)}")
            raise

    def get_collection(self, collection_name: str) -> Optional[Collection]:
        """
        获取集合对象

        参数：
            collection_name: 集合名称

        返回：
            Collection: 集合对象，不存在则返回None
        """
        try:
            # 从缓存获取
            if collection_name in self.collections:
                return self.collections[collection_name]

            # 检查集合是否存在
            if not utility.has_collection(collection_name):
                logger.warning(f"集合不存在: {collection_name}")
                return None

            # 加载集合
            collection = Collection(collection_name)
            self.collections[collection_name] = collection

            return collection

        except Exception as e:
            logger.error(f"获取集合失败: {str(e)}")
            raise

    @log_execution("创建索引")
    def create_index(
            self,
            collection_name: str,
            index_params: Optional[Dict] = None
    ):
        """
        为集合创建索引

        参数：
            collection_name: 集合名称
            index_params: 索引参数（默认使用IVF_FLAT）

        💡 索引作用：
        - 加速向量搜索
        - 提高查询效率
        """
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                raise ValueError(f"集合不存在: {collection_name}")

            # 使用默认索引参数
            if index_params is None:
                index_params = MilvusIndexParams.IVF_FLAT

            # 创建索引
            collection.create_index(
                field_name="embedding",
                index_params=index_params
            )

            logger.info(f"创建索引成功: {collection_name}")

        except Exception as e:
            logger.error(f"创建索引失败: {str(e)}")
            raise

    def drop_collection(self, collection_name: str):
        """
        删除集合

        参数：
            collection_name: 集合名称
        """
        try:
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)

                # 从缓存中移除
                if collection_name in self.collections:
                    del self.collections[collection_name]

                logger.info(f"删除集合成功: {collection_name}")
            else:
                logger.warning(f"集合不存在: {collection_name}")

        except Exception as e:
            logger.error(f"删除集合失败: {str(e)}")
            raise

    # =========================================
    # 向量操作
    # =========================================

    @log_execution("插入向量")
    def insert_vectors(
            self,
            collection_name: str,
            vectors: List[np.ndarray],
            vector_ids: List[str],
            doc_ids: List[str],
            doc_types: List[str],
            permission_levels: List[str],
            page_nums: List[int]
    ) -> List[int]:
        """
        批量插入向量

        参数：
            collection_name: 集合名称
            vectors: 向量列表
            vector_ids: 向量ID列表（对应chunk_id）
            doc_ids: 文档ID列表
            doc_types: 文档类型列表
            permission_levels: 权限级别列表
            page_nums: 页码列表

        返回：
            List[int]: 插入的向量主键ID列表

        示例：
            ids = repo.insert_vectors(
                collection_name="rag_standards",
                vectors=[vec1, vec2, vec3],
                vector_ids=["chunk_1", "chunk_2", "chunk_3"],
                doc_ids=["doc_1", "doc_1", "doc_1"],
                doc_types=["standard", "standard", "standard"],
                permission_levels=["public", "public", "public"],
                page_nums=[1, 1, 2]
            )
        """
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                raise ValueError(f"集合不存在: {collection_name}")

            # 准备数据
            entities = [
                vector_ids,
                vectors,
                doc_ids,
                doc_types,
                permission_levels,
                page_nums
            ]

            # 插入数据
            insert_result = collection.insert(entities)

            # 刷新以确保数据持久化
            collection.flush()

            logger.info(f"插入向量成功: {collection_name}, 数量: {len(vectors)}")
            return insert_result.primary_keys

        except Exception as e:
            logger.error(f"插入向量失败: {str(e)}")
            raise

    @log_execution("搜索向量")
    def search_vectors(
            self,
            collection_name: str,
            query_vectors: List[np.ndarray],
            top_k: int = 10,
            search_params: Optional[Dict] = None,
            expr: Optional[str] = None
    ) -> List[List[Dict[str, Any]]]:
        """
        向量相似度搜索

        参数：
            collection_name: 集合名称
            query_vectors: 查询向量列表
            top_k: 返回最相似的k个结果
            search_params: 搜索参数
            expr: 过滤表达式（如：'doc_type == "standard"'）

        返回：
            List[List[Dict]]: 搜索结果
            - 外层List：对应每个查询向量
            - 内层List：每个向量的Top-K结果
            - Dict：单个结果，包含id、distance、entity等

        示例：
            # 搜索规范库
            results = repo.search_vectors(
                collection_name="rag_standards",
                query_vectors=[query_vec],
                top_k=5,
                expr='permission_level == "public"'
            )
        """
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                raise ValueError(f"集合不存在: {collection_name}")

            # 加载集合到内存
            collection.load()

            # 使用默认搜索参数
            if search_params is None:
                search_params = SearchParams.IVF_PARAMS

            # 执行搜索
            results = collection.search(
                data=query_vectors,
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=["vector_id", "doc_id", "doc_type", "permission_level", "page_num"]
            )

            # 格式化结果
            formatted_results = []
            for hits in results:
                hit_list = []
                for hit in hits:
                    hit_list.append({
                        "id": hit.id,
                        "distance": hit.distance,  # 相似度分数
                        "vector_id": hit.entity.get("vector_id"),
                        "doc_id": hit.entity.get("doc_id"),
                        "doc_type": hit.entity.get("doc_type"),
                        "permission_level": hit.entity.get("permission_level"),
                        "page_num": hit.entity.get("page_num")
                    })
                formatted_results.append(hit_list)

            logger.info(f"搜索向量成功: {collection_name}, 查询数: {len(query_vectors)}, Top-K: {top_k}")
            return formatted_results

        except Exception as e:
            logger.error(f"搜索向量失败: {str(e)}")
            raise

    def delete_vectors(
            self,
            collection_name: str,
            expr: str
    ) -> int:
        """
        删除向量

        参数：
            collection_name: 集合名称
            expr: 删除条件表达式

        返回：
            int: 删除的向量数量

        示例：
            # 删除指定文档的所有向量
            count = repo.delete_vectors(
                collection_name="rag_standards",
                expr='doc_id == "doc_123"'
            )
        """
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                raise ValueError(f"集合不存在: {collection_name}")

            # 执行删除
            collection.delete(expr)
            collection.flush()

            logger.info(f"删除向量成功: {collection_name}, 条件: {expr}")
            # 注意：Milvus不直接返回删除数量，这里返回0作为占位
            return 0

        except Exception as e:
            logger.error(f"删除向量失败: {str(e)}")
            raise

    # =========================================
    # 分层检索策略
    # =========================================

    def hierarchical_search(
            self,
            query_vector: np.ndarray,
            top_k: int = 5,
            permission_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        分层检索策略

        🏗️ 检索流程：
        1. 优先搜索权威规范库（STANDARDS）
        2. 如果结果不足，搜索项目资料库（PROJECTS）
        3. 最后搜索合同库（CONTRACTS）

        参数：
            query_vector: 查询向量
            top_k: 返回的最大结果数
            permission_filter: 权限过滤表达式

        返回：
            List[Dict]: 检索结果（已去重和排序）
        """
        try:
            all_results = []

            # 定义搜索顺序（按优先级）
            collections_order = [
                MilvusCollection.STANDARDS,
                MilvusCollection.PROJECTS,
                MilvusCollection.CONTRACTS
            ]

            for collection_name in collections_order:
                # 检查集合是否存在
                if not utility.has_collection(collection_name.value):
                    logger.warning(f"集合不存在，跳过: {collection_name.value}")
                    continue

                # 搜索当前层级
                results = self.search_vectors(
                    collection_name=collection_name.value,
                    query_vectors=[query_vector],
                    top_k=top_k,
                    expr=permission_filter
                )

                # 添加到总结果
                if results and results[0]:
                    for hit in results[0]:
                        hit["collection"] = collection_name.value
                        all_results.append(hit)

                # 如果已经找到足够的结果，提前结束
                if len(all_results) >= top_k:
                    break

            # 按相似度排序并返回Top-K
            all_results.sort(key=lambda x: x["distance"], reverse=True)
            return all_results[:top_k]

        except Exception as e:
            logger.error(f"分层检索失败: {str(e)}")
            raise

    # =========================================
    # 统计信息
    # =========================================

    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """
        获取集合统计信息

        参数：
            collection_name: 集合名称

        返回：
            Dict: 统计信息
        """
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                return {"error": "集合不存在"}

            stats = {
                "name": collection_name,
                "num_entities": collection.num_entities,
                "description": collection.description,
            }

            return stats

        except Exception as e:
            logger.error(f"获取集合统计失败: {str(e)}")
            raise


# =========================================
# 💡 使用示例
# =========================================
"""
# 1. 创建Repository实例
from repository.vector_repo import VectorRepository

repo = VectorRepository()


# 2. 创建三层向量库
repo.create_collection(
    collection_name="rag_standards",
    description="权威规范库"
)

repo.create_collection(
    collection_name="rag_projects",
    description="项目资料库"
)

repo.create_collection(
    collection_name="rag_contracts",
    description="合同库"
)


# 3. 创建索引
repo.create_index("rag_standards")
repo.create_index("rag_projects")
repo.create_index("rag_contracts")


# 4. 插入向量
import numpy as np

vectors = [np.random.rand(768) for _ in range(10)]
vector_ids = [f"chunk_{i}" for i in range(10)]
doc_ids = ["doc_001"] * 10
doc_types = ["standard"] * 10
permission_levels = ["public"] * 10
page_nums = [1, 1, 1, 2, 2, 2, 3, 3, 3, 4]

ids = repo.insert_vectors(
    collection_name="rag_standards",
    vectors=vectors,
    vector_ids=vector_ids,
    doc_ids=doc_ids,
    doc_types=doc_types,
    permission_levels=permission_levels,
    page_nums=page_nums
)


# 5. 向量搜索
query_vec = np.random.rand(768)

results = repo.search_vectors(
    collection_name="rag_standards",
    query_vectors=[query_vec],
    top_k=5
)


# 6. 分层检索
results = repo.hierarchical_search(
    query_vector=query_vec,
    top_k=5,
    permission_filter='permission_level == "public"'
)


# 7. 获取统计信息
stats = repo.get_collection_stats("rag_standards")
print(f"集合: {stats['name']}")
print(f"向量数量: {stats['num_entities']}")


# 8. 关闭连接
repo.disconnect()
"""