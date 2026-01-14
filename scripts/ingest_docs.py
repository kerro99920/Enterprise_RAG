"""
========================================
文档入库脚本
========================================

📚 模块说明：
- 批量处理文档并入库
- 支持增量更新
- 完整的处理流程

🚀 使用方式：
    python scripts/ingest_docs.py

========================================
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import argparse
import json

# 添加项目根目录到 Python 路径
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from loguru import logger

# 导入核心模块
from core.config import settings
from core.constants import DocumentType, DocumentStatus, MilvusCollection

# 导入服务模块
from services.document.loader import DocumentLoader
from services.document.cleaner import DocumentCleaner
from services.document.splitter import DocumentSplitter
from services.document.metadata import MetadataExtractor
from services.embedding.embedding_model import EmbeddingModel
from services.embedding.embedder import Embedder
from repository.vector_repo import VectorRepository
from repository.document_repo import DocumentRepository

# 数据库
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class DocumentIngester:
    """
    文档入库器

    🔧 处理流程：
    1. 加载文档（PDF/Word/图片）
    2. 文本清洗
    3. 文档分块
    4. 元数据提取
    5. 向量化
    6. 存入向量库
    7. 存入关系数据库
    """

    def __init__(
        self,
        enable_ocr: bool = True,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        batch_size: int = 32
    ):
        """
        初始化文档入库器

        参数：
            enable_ocr: 是否启用 OCR
            chunk_size: 分块大小
            chunk_overlap: 分块重叠大小
            batch_size: 向量化批大小
        """
        logger.info("初始化文档入库器...")

        # 初始化组件
        self.loader = DocumentLoader(enable_ocr=enable_ocr)
        self.cleaner = DocumentCleaner()
        self.splitter = DocumentSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        self.metadata_extractor = MetadataExtractor()

        # 初始化 Embedding
        self.embedding_model = EmbeddingModel(
            model_name=settings.EMBEDDING_MODEL_NAME
        )
        self.embedder = Embedder(
            embedding_model=self.embedding_model,
            batch_size=batch_size
        )

        # 初始化 Repository
        self.vector_repo = VectorRepository()

        # 初始化数据库
        self.engine = create_engine(settings.postgres_url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.doc_repo = DocumentRepository(self.session)

        # 统计信息
        self.stats = {
            'total_files': 0,
            'processed': 0,
            'failed': 0,
            'total_chunks': 0,
            'total_time': 0
        }

        logger.info("文档入库器初始化完成")

    def ingest_file(
        self,
        file_path: str,
        collection_name: str = None,
        doc_type: DocumentType = None
    ) -> Dict:
        """
        处理单个文件

        参数：
            file_path: 文件路径
            collection_name: 向量库集合名称
            doc_type: 文档类型

        返回：
            处理结果
        """
        start_time = datetime.now()
        file_name = os.path.basename(file_path)

        logger.info(f"开始处理: {file_name}")

        try:
            # 1. 加载文档
            logger.debug(f"  [1/6] 加载文档...")
            doc_data = self.loader.load(file_path)

            # 2. 清洗文本
            logger.debug(f"  [2/6] 清洗文本...")
            cleaned_text = self.cleaner.clean(doc_data['text'])

            # 3. 提取元数据
            logger.debug(f"  [3/6] 提取元数据...")
            metadata = self.metadata_extractor.extract(
                cleaned_text,
                file_path=file_path,
                doc_metadata=doc_data.get('metadata', {})
            )

            # 4. 文档分块
            logger.debug(f"  [4/6] 文档分块...")
            chunks = self.splitter.split(
                cleaned_text,
                method='recursive',
                metadata=metadata
            )

            if not chunks:
                raise ValueError("文档分块失败，未生成任何块")

            logger.debug(f"    生成 {len(chunks)} 个块")

            # 5. 向量化
            logger.debug(f"  [5/6] 向量化...")
            embedded_chunks = self.embedder.embed_chunks(chunks)

            # 6. 存入向量库
            logger.debug(f"  [6/6] 存入向量库...")

            # 确定集合名称
            if collection_name is None:
                collection_name = self._determine_collection(doc_type, metadata)

            # 准备向量数据
            vectors_data = []
            for i, chunk in enumerate(embedded_chunks):
                vectors_data.append({
                    'doc_id': f"{file_name}_{i}",
                    'text': chunk['text'],
                    'embedding': chunk['embedding'],
                    'metadata': {
                        'file_name': file_name,
                        'file_path': file_path,
                        'chunk_index': i,
                        'total_chunks': len(embedded_chunks),
                        **chunk.get('metadata', {})
                    }
                })

            # 插入向量库
            self.vector_repo.insert_vectors(
                collection_name=collection_name,
                vectors=vectors_data
            )

            # 7. 存入关系数据库
            doc_record = self.doc_repo.create_document(
                name=file_name,
                doc_type=doc_type or DocumentType.OTHER,
                source_path=file_path,
                status=DocumentStatus.COMPLETED,
                total_chunks=len(chunks),
                vector_collection=collection_name,
                embedding_model=settings.EMBEDDING_MODEL_NAME,
                **{k: v for k, v in metadata.items() if k in ['title', 'author', 'version']}
            )

            # 计算耗时
            process_time = (datetime.now() - start_time).total_seconds()

            # 更新统计
            self.stats['processed'] += 1
            self.stats['total_chunks'] += len(chunks)
            self.stats['total_time'] += process_time

            result = {
                'success': True,
                'file_name': file_name,
                'doc_id': doc_record.id,
                'chunks': len(chunks),
                'collection': collection_name,
                'process_time': process_time
            }

            logger.info(
                f"✓ 处理完成: {file_name} | "
                f"块数: {len(chunks)} | "
                f"耗时: {process_time:.2f}s"
            )

            return result

        except Exception as e:
            self.stats['failed'] += 1

            logger.error(f"✗ 处理失败: {file_name} | 错误: {str(e)}")

            return {
                'success': False,
                'file_name': file_name,
                'error': str(e)
            }

    def ingest_directory(
        self,
        directory: str,
        collection_name: str = None,
        recursive: bool = True,
        file_types: List[str] = None
    ) -> List[Dict]:
        """
        批量处理目录中的文档

        参数：
            directory: 目录路径
            collection_name: 向量库集合名称
            recursive: 是否递归子目录
            file_types: 限定文件类型（如 ['.pdf', '.docx']）

        返回：
            处理结果列表
        """
        if not os.path.isdir(directory):
            raise ValueError(f"目录不存在: {directory}")

        # 收集文件
        files = []
        supported_types = file_types or self.loader.get_supported_formats()

        if recursive:
            for root, dirs, filenames in os.walk(directory):
                for filename in filenames:
                    if any(filename.lower().endswith(ext) for ext in supported_types):
                        files.append(os.path.join(root, filename))
        else:
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path):
                    if any(filename.lower().endswith(ext) for ext in supported_types):
                        files.append(file_path)

        self.stats['total_files'] = len(files)

        logger.info(f"找到 {len(files)} 个待处理文件")

        # 批量处理
        results = []
        for i, file_path in enumerate(files, 1):
            logger.info(f"[{i}/{len(files)}] 处理中...")
            result = self.ingest_file(file_path, collection_name)
            results.append(result)

        return results

    def _determine_collection(
        self,
        doc_type: Optional[DocumentType],
        metadata: Dict
    ) -> str:
        """
        根据文档类型确定向量库集合

        规则：
        - 标准/规范类 -> rag_standards
        - 项目资料类 -> rag_projects
        - 合同类 -> rag_contracts
        - 其他 -> rag_projects（默认）
        """
        if doc_type == DocumentType.STANDARD:
            return MilvusCollection.STANDARDS.value
        elif doc_type == DocumentType.CONTRACT:
            return MilvusCollection.CONTRACTS.value
        elif doc_type == DocumentType.PROJECT:
            return MilvusCollection.PROJECTS.value

        # 根据元数据判断
        title = metadata.get('title', '').lower()
        doc_number = metadata.get('document_number', '')

        # 检查是否是标准/规范
        if doc_number and any(prefix in doc_number.upper() for prefix in ['GB', 'JGJ', 'CJJ']):
            return MilvusCollection.STANDARDS.value

        if any(keyword in title for keyword in ['规范', '标准', '规程', 'standard']):
            return MilvusCollection.STANDARDS.value

        # 检查是否是合同
        if any(keyword in title for keyword in ['合同', '协议', 'contract']):
            return MilvusCollection.CONTRACTS.value

        # 默认项目资料库
        return MilvusCollection.PROJECTS.value

    def print_stats(self):
        """打印统计信息"""
        print("\n" + "=" * 60)
        print("📊 入库统计")
        print("=" * 60)
        print(f"  总文件数: {self.stats['total_files']}")
        print(f"  成功处理: {self.stats['processed']}")
        print(f"  处理失败: {self.stats['failed']}")
        print(f"  总块数: {self.stats['total_chunks']}")
        print(f"  总耗时: {self.stats['total_time']:.2f}s")

        if self.stats['processed'] > 0:
            avg_time = self.stats['total_time'] / self.stats['processed']
            avg_chunks = self.stats['total_chunks'] / self.stats['processed']
            print(f"  平均耗时: {avg_time:.2f}s/文件")
            print(f"  平均块数: {avg_chunks:.1f}块/文件")

        print("=" * 60)

    def close(self):
        """关闭连接"""
        try:
            self.session.close()
            self.vector_repo.disconnect()
            logger.info("连接已关闭")
        except Exception as e:
            logger.error(f"关闭连接失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="企业级 RAG 系统 - 文档入库工具"
    )

    parser.add_argument(
        'path',
        nargs='?',
        default=str(settings.RAW_DOCS_DIR),
        help='文件或目录路径（默认: data/raw_docs）'
    )

    parser.add_argument(
        '-c', '--collection',
        default=None,
        help='向量库集合名称'
    )

    parser.add_argument(
        '-t', '--type',
        choices=['standard', 'project', 'contract', 'other'],
        default=None,
        help='文档类型'
    )

    parser.add_argument(
        '--no-recursive',
        action='store_true',
        help='不递归处理子目录'
    )

    parser.add_argument(
        '--no-ocr',
        action='store_true',
        help='禁用 OCR'
    )

    parser.add_argument(
        '--chunk-size',
        type=int,
        default=500,
        help='分块大小（默认: 500）'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='向量化批大小（默认: 32）'
    )

    args = parser.parse_args()

    # 打印配置
    print("\n" + "=" * 60)
    print("🚀 企业级 RAG 系统 - 文档入库工具")
    print("=" * 60)
    print(f"  路径: {args.path}")
    print(f"  集合: {args.collection or '自动判断'}")
    print(f"  类型: {args.type or '自动判断'}")
    print(f"  OCR: {'禁用' if args.no_ocr else '启用'}")
    print(f"  递归: {'否' if args.no_recursive else '是'}")
    print(f"  分块大小: {args.chunk_size}")
    print("=" * 60)

    # 确认
    confirm = input("\n确认开始处理？(y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消")
        return

    # 初始化入库器
    ingester = DocumentIngester(
        enable_ocr=not args.no_ocr,
        chunk_size=args.chunk_size,
        batch_size=args.batch_size
    )

    try:
        # 处理文档类型
        doc_type = None
        if args.type:
            type_map = {
                'standard': DocumentType.STANDARD,
                'project': DocumentType.PROJECT,
                'contract': DocumentType.CONTRACT,
                'other': DocumentType.OTHER
            }
            doc_type = type_map.get(args.type)

        # 判断是文件还是目录
        if os.path.isfile(args.path):
            # 单个文件
            result = ingester.ingest_file(
                args.path,
                collection_name=args.collection,
                doc_type=doc_type
            )
            if result['success']:
                print(f"\n✓ 文件处理成功: {result['file_name']}")
            else:
                print(f"\n✗ 文件处理失败: {result['error']}")

        elif os.path.isdir(args.path):
            # 目录
            results = ingester.ingest_directory(
                args.path,
                collection_name=args.collection,
                recursive=not args.no_recursive
            )

            # 打印结果摘要
            success_count = sum(1 for r in results if r['success'])
            fail_count = sum(1 for r in results if not r['success'])

            print(f"\n处理完成: 成功 {success_count}, 失败 {fail_count}")

            # 打印失败文件
            if fail_count > 0:
                print("\n失败文件:")
                for r in results:
                    if not r['success']:
                        print(f"  - {r['file_name']}: {r['error']}")

        else:
            print(f"路径不存在: {args.path}")
            return

        # 打印统计
        ingester.print_stats()

    finally:
        ingester.close()


if __name__ == "__main__":
    main()


# =========================================
# 💡 使用示例
# =========================================
"""
# 1. 处理默认目录（data/raw_docs）
python scripts/ingest_docs.py

# 2. 处理指定目录
python scripts/ingest_docs.py /path/to/docs

# 3. 处理单个文件
python scripts/ingest_docs.py /path/to/doc.pdf

# 4. 指定文档类型
python scripts/ingest_docs.py -t standard /path/to/standards

# 5. 指定向量库集合
python scripts/ingest_docs.py -c rag_standards /path/to/standards

# 6. 禁用 OCR（加快处理速度）
python scripts/ingest_docs.py --no-ocr /path/to/docs

# 7. 不递归子目录
python scripts/ingest_docs.py --no-recursive /path/to/docs

# 8. 自定义分块大小
python scripts/ingest_docs.py --chunk-size 300 /path/to/docs

# 9. 在代码中使用
from scripts.ingest_docs import DocumentIngester

ingester = DocumentIngester()
result = ingester.ingest_file("document.pdf")
print(result)
"""
