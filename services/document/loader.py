"""
========================================
统一文档加载器
========================================

📚 模块说明：
- 根据文件类型自动选择合适的解析器
- 统一的文档加载接口
- 支持批量处理

🎯 核心功能：
1. 自动识别文件类型
2. 调用对应的解析器
3. 处理OCR扫描件
4. 批量加载文档

========================================
"""
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from enum import Enum

from services.document.pdf_parser import PDFParser
from services.document.word_parser import WordParser
from services.document.ocr_parser import OCRParser
from loguru import logger


class DocumentType(str, Enum):
    """文档类型枚举"""
    PDF = "pdf"
    WORD = "word"
    IMAGE = "image"
    TEXT = "text"
    UNKNOWN = "unknown"


class DocumentLoader:
    """
    统一文档加载器

    🎯 职责：
    - 识别文件类型
    - 自动选择解析器
    - 处理OCR需求
    - 提供统一接口

    💡 支持的格式：
    - PDF (.pdf)
    - Word (.docx, .doc)
    - 图片 (.jpg, .jpeg, .png, .bmp, .tiff)
    - 文本 (.txt, .md)
    """

    def __init__(self, enable_ocr: bool = True):
        """
        初始化文档加载器

        参数：
            enable_ocr: 是否启用OCR功能
        """
        self.enable_ocr = enable_ocr

        # 初始化各个解析器
        self.pdf_parser = PDFParser()
        self.word_parser = WordParser()

        if enable_ocr:
            self.ocr_parser = OCRParser()
        else:
            self.ocr_parser = None

        # 文件扩展名映射
        self.extension_map = {
            '.pdf': DocumentType.PDF,
            '.docx': DocumentType.WORD,
            '.doc': DocumentType.WORD,
            '.jpg': DocumentType.IMAGE,
            '.jpeg': DocumentType.IMAGE,
            '.png': DocumentType.IMAGE,
            '.bmp': DocumentType.IMAGE,
            '.tiff': DocumentType.IMAGE,
            '.txt': DocumentType.TEXT,
            '.md': DocumentType.TEXT,
        }

        logger.info(f"文档加载器初始化完成 | OCR: {enable_ocr}")

    def load(self, file_path: str, use_ocr: bool = True) -> Dict[str, Any]:
        """
        加载文档（自动识别类型）

        参数：
            file_path: 文件路径
            use_ocr: 是否对扫描PDF使用OCR

        返回：
            Dict: 统一格式的文档数据
            {
                "text": str,              # 文本内容
                "metadata": Dict,         # 元数据
                "doc_type": str,          # 文档类型
                "file_path": str,         # 文件路径
                "file_name": str,         # 文件名
                "file_size": int,         # 文件大小（字节）
                "pages": List[Dict],      # 页面数据（如果有）
                "tables": List[Dict],     # 表格数据（如果有）
                "is_scanned": bool,       # 是否为扫描件
                "ocr_confidence": float,  # OCR置信度（如果使用了OCR）
            }

        示例：
            loader = DocumentLoader()
            result = loader.load("data/raw_docs/GB50009-2012.pdf")
            print(result['text'])
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")

            # 获取文件信息
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            file_ext = Path(file_path).suffix.lower()

            # 识别文档类型
            doc_type = self.extension_map.get(file_ext, DocumentType.UNKNOWN)

            if doc_type == DocumentType.UNKNOWN:
                raise ValueError(f"不支持的文件类型: {file_ext}")

            logger.info(f"加载文档: {file_name} | 类型: {doc_type.value}")

            # 根据类型调用对应的解析器
            if doc_type == DocumentType.PDF:
                result = self._load_pdf(file_path, use_ocr)
            elif doc_type == DocumentType.WORD:
                result = self._load_word(file_path)
            elif doc_type == DocumentType.IMAGE:
                result = self._load_image(file_path)
            elif doc_type == DocumentType.TEXT:
                result = self._load_text(file_path)
            else:
                raise ValueError(f"未实现的文档类型: {doc_type}")

            # 添加通用信息
            result.update({
                "doc_type": doc_type.value,
                "file_path": file_path,
                "file_name": file_name,
                "file_size": file_size,
            })

            logger.info(
                f"文档加载完成: {file_name} | "
                f"字符数: {len(result.get('text', ''))} | "
                f"OCR: {result.get('is_scanned', False)}"
            )

            return result

        except Exception as e:
            logger.error(f"加载文档失败: {file_path} | 错误: {str(e)}")
            raise

    def _load_pdf(self, file_path: str, use_ocr: bool) -> Dict[str, Any]:
        """
        加载PDF文档

        🔄 处理流程：
        1. 使用PDF解析器提取文本
        2. 判断是否为扫描件
        3. 如果是扫描件且启用OCR，使用OCR识别
        4. 返回统一格式的结果
        """
        # 先用PDF解析器尝试提取文本
        pdf_result = self.pdf_parser.parse(file_path)

        # 检查是否为扫描件
        is_scanned = pdf_result.get('is_scanned', False)

        # 如果是扫描件且启用OCR
        if is_scanned and use_ocr and self.enable_ocr and self.ocr_parser:
            logger.info(f"检测到扫描PDF，使用OCR识别: {file_path}")

            try:
                # 使用OCR识别
                ocr_result = self.ocr_parser.parse_pdf(file_path)

                # 合并结果（优先使用OCR的文本）
                return {
                    "text": ocr_result['text'],
                    "metadata": pdf_result.get('metadata', {}),
                    "pages": ocr_result['pages'],
                    "tables": pdf_result.get('tables', []),  # 表格仍使用PDF解析的结果
                    "is_scanned": True,
                    "ocr_confidence": ocr_result['avg_confidence'],
                    "total_pages": ocr_result['total_pages']
                }

            except Exception as e:
                logger.warning(f"OCR识别失败，使用原始PDF解析结果: {str(e)}")
                # OCR失败，返回PDF解析结果
                return {
                    "text": pdf_result.get('text', ''),
                    "metadata": pdf_result.get('metadata', {}),
                    "pages": pdf_result.get('pages', []),
                    "tables": pdf_result.get('tables', []),
                    "is_scanned": True,
                    "ocr_confidence": 0.0,
                    "total_pages": pdf_result.get('total_pages', 0)
                }
        else:
            # 非扫描件或不使用OCR
            return {
                "text": pdf_result.get('text', ''),
                "metadata": pdf_result.get('metadata', {}),
                "pages": pdf_result.get('pages', []),
                "tables": pdf_result.get('tables', []),
                "is_scanned": is_scanned,
                "ocr_confidence": None,
                "total_pages": pdf_result.get('total_pages', 0)
            }

    def _load_word(self, file_path: str) -> Dict[str, Any]:
        """加载Word文档"""
        word_result = self.word_parser.parse(file_path)

        return {
            "text": word_result.get('text', ''),
            "metadata": word_result.get('metadata', {}),
            "pages": word_result.get('paragraphs', []),  # Word用段落代替页面
            "tables": word_result.get('tables', []),
            "is_scanned": False,
            "ocr_confidence": None,
            "total_pages": word_result.get('paragraph_count', 0)
        }

    def _load_image(self, file_path: str) -> Dict[str, Any]:
        """加载图片（使用OCR）"""
        if not self.enable_ocr or not self.ocr_parser:
            raise RuntimeError("OCR功能未启用，无法识别图片")

        ocr_result = self.ocr_parser.parse_image(file_path)

        return {
            "text": ocr_result.get('text', ''),
            "metadata": {},
            "pages": [{"page_num": 1, "text": ocr_result.get('text', '')}],
            "tables": [],
            "is_scanned": True,
            "ocr_confidence": ocr_result.get('confidence', 0.0),
            "total_pages": 1
        }

    def _load_text(self, file_path: str) -> Dict[str, Any]:
        """加载纯文本文件"""
        try:
            # 尝试UTF-8编码
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except UnicodeDecodeError:
            # 尝试GBK编码
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    text = f.read()
            except UnicodeDecodeError:
                # 尝试其他编码
                with open(file_path, 'r', encoding='latin-1') as f:
                    text = f.read()

        return {
            "text": text,
            "metadata": {},
            "pages": [{"page_num": 1, "text": text}],
            "tables": [],
            "is_scanned": False,
            "ocr_confidence": None,
            "total_pages": 1
        }

    def batch_load(
            self,
            file_paths: List[str],
            use_ocr: bool = True
    ) -> List[Dict[str, Any]]:
        """
        批量加载文档

        参数：
            file_paths: 文件路径列表
            use_ocr: 是否使用OCR

        返回：
            List[Dict]: 文档数据列表

        💡 错误处理：
        - 单个文件失败不影响其他文件
        - 失败的文件会记录错误日志
        """
        results = []

        logger.info(f"开始批量加载 | 文件数: {len(file_paths)}")

        for idx, file_path in enumerate(file_paths, 1):
            try:
                logger.info(f"[{idx}/{len(file_paths)}] 加载: {file_path}")
                result = self.load(file_path, use_ocr=use_ocr)
                results.append(result)
            except Exception as e:
                logger.error(f"批量加载失败: {file_path} | 错误: {str(e)}")
                # 继续处理下一个文件
                continue

        logger.info(
            f"批量加载完成: 成功 {len(results)}/{len(file_paths)} 个文件"
        )

        return results

    def load_directory(
            self,
            directory: str,
            recursive: bool = False,
            use_ocr: bool = True
    ) -> List[Dict[str, Any]]:
        """
        加载目录中的所有文档

        参数：
            directory: 目录路径
            recursive: 是否递归子目录
            use_ocr: 是否使用OCR

        返回：
            List[Dict]: 文档数据列表
        """
        try:
            # 收集所有支持的文件
            file_paths = []

            if recursive:
                # 递归遍历
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if self._is_supported_file(file_path):
                            file_paths.append(file_path)
            else:
                # 只遍历当前目录
                for file in os.listdir(directory):
                    file_path = os.path.join(directory, file)
                    if os.path.isfile(file_path) and self._is_supported_file(file_path):
                        file_paths.append(file_path)

            logger.info(f"找到 {len(file_paths)} 个支持的文件")

            # 批量加载
            return self.batch_load(file_paths, use_ocr=use_ocr)

        except Exception as e:
            logger.error(f"加载目录失败: {directory} | 错误: {str(e)}")
            raise

    def _is_supported_file(self, file_path: str) -> bool:
        """检查文件是否支持"""
        file_ext = Path(file_path).suffix.lower()
        return file_ext in self.extension_map

    def get_supported_formats(self) -> List[str]:
        """获取支持的文件格式列表"""
        return list(self.extension_map.keys())


# =========================================
# 💡 使用示例
# =========================================
"""
# 1. 加载单个文档
from services.document.loader import DocumentLoader

loader = DocumentLoader()

# 加载PDF
result = loader.load("data/raw_docs/GB50009-2012.pdf")
print(f"文档类型: {result['doc_type']}")
print(f"总页数: {result['total_pages']}")
print(f"是否扫描件: {result['is_scanned']}")
print(f"文本预览: {result['text'][:200]}")

# 加载Word
result = loader.load("data/raw_docs/项目总结.docx")
print(result['text'])

# 加载图片
result = loader.load("scan.jpg")
print(f"OCR置信度: {result['ocr_confidence']:.2%}")


# 2. 批量加载
files = [
    "doc1.pdf",
    "doc2.docx",
    "doc3.pdf"
]

results = loader.batch_load(files)
for result in results:
    print(f"{result['file_name']}: {len(result['text'])} 字符")


# 3. 加载整个目录
results = loader.load_directory("data/raw_docs", recursive=True)
print(f"加载了 {len(results)} 个文档")


# 4. 查看支持的格式
formats = loader.get_supported_formats()
print(f"支持的格式: {formats}")


# 5. 禁用OCR
loader_no_ocr = DocumentLoader(enable_ocr=False)
result = loader_no_ocr.load("document.pdf", use_ocr=False)
"""