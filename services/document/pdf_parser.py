"""
========================================
PDF 文档解析器
========================================

📚 模块说明：
- 解析PDF文档，提取文本和结构信息
- 支持普通PDF和扫描PDF（OCR）
- 提取表格、图片等元素

🎯 核心功能：
1. 文本提取
2. 表格识别和提取
3. 页面信息提取
4. 元数据提取

========================================
"""
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import PyPDF2
import pdfplumber

from core.logger import logger, log_execution
from core.config import settings


class PDFParser:
    """
    PDF解析器

    🎯 职责：
    - 提取PDF文本内容
    - 识别和提取表格
    - 提取文档元数据
    - 判断是否需要OCR
    """

    def __init__(self):
        """初始化PDF解析器"""
        self.supported_extensions = ['.pdf']

    @log_execution("解析PDF文档")
    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        解析PDF文件

        参数：
            file_path: PDF文件路径

        返回：
            Dict: 解析结果
            {
                "text": str,              # 全文本
                "pages": List[Dict],      # 每页的内容
                "tables": List[Dict],     # 表格数据
                "metadata": Dict,         # 文档元数据
                "total_pages": int,       # 总页数
                "is_scanned": bool,       # 是否为扫描件
                "has_tables": bool,       # 是否包含表格
            }
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")

            logger.info(f"开始解析PDF: {file_path}")

            # 提取元数据
            metadata = self._extract_metadata(file_path)

            # 提取文本和页面信息
            pages_data, total_text = self._extract_text_and_pages(file_path)

            # 提取表格
            tables = self._extract_tables(file_path)

            # 判断是否为扫描件（文本很少或没有）
            is_scanned = self._is_scanned_pdf(total_text, len(pages_data))

            result = {
                "text": total_text,
                "pages": pages_data,
                "tables": tables,
                "metadata": metadata,
                "total_pages": len(pages_data),
                "is_scanned": is_scanned,
                "has_tables": len(tables) > 0,
                "file_path": file_path,
                "file_name": os.path.basename(file_path)
            }

            logger.info(
                f"PDF解析完成: {file_path} | "
                f"页数: {result['total_pages']} | "
                f"表格: {len(tables)} | "
                f"扫描件: {is_scanned}"
            )

            return result

        except Exception as e:
            logger.error(f"PDF解析失败: {file_path} | 错误: {str(e)}")
            raise

    def _extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        提取PDF元数据

        参数：
            file_path: PDF文件路径

        返回：
            Dict: 元数据信息
        """
        try:
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)

                # 获取PDF元数据
                info = pdf_reader.metadata

                metadata = {
                    "title": info.get('/Title', '') if info else '',
                    "author": info.get('/Author', '') if info else '',
                    "subject": info.get('/Subject', '') if info else '',
                    "creator": info.get('/Creator', '') if info else '',
                    "producer": info.get('/Producer', '') if info else '',
                    "creation_date": info.get('/CreationDate', '') if info else '',
                    "modification_date": info.get('/ModDate', '') if info else '',
                }

                # 清理元数据中的特殊字符
                for key, value in metadata.items():
                    if isinstance(value, str):
                        metadata[key] = value.strip()

                return metadata

        except Exception as e:
            logger.warning(f"提取PDF元数据失败: {str(e)}")
            return {}

    def _extract_text_and_pages(
            self,
            file_path: str
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        提取文本和页面信息

        参数：
            file_path: PDF文件路径

        返回：
            Tuple[List[Dict], str]: (页面数据列表, 全文本)
        """
        pages_data = []
        all_text = []

        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    # 提取页面文本
                    text = page.extract_text() or ""

                    # 页面尺寸
                    width = page.width
                    height = page.height

                    # 页面数据
                    page_data = {
                        "page_num": page_num,
                        "text": text,
                        "width": width,
                        "height": height,
                        "char_count": len(text)
                    }

                    pages_data.append(page_data)
                    all_text.append(text)

            # 合并全部文本
            total_text = "\n\n".join(all_text)

            return pages_data, total_text

        except Exception as e:
            logger.error(f"提取PDF文本失败: {str(e)}")
            raise

    def _extract_tables(self, file_path: str) -> List[Dict[str, Any]]:
        """
        提取PDF中的表格

        参数：
            file_path: PDF文件路径

        返回：
            List[Dict]: 表格数据列表

        💡 表格格式：
        {
            "page_num": int,      # 所在页码
            "table_index": int,   # 表格索引
            "rows": int,          # 行数
            "cols": int,          # 列数
            "data": List[List],   # 表格数据
            "text": str           # 表格转换为文本
        }
        """
        tables = []

        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    # 提取页面中的所有表格
                    page_tables = page.extract_tables()

                    if page_tables:
                        for table_index, table_data in enumerate(page_tables):
                            if table_data and len(table_data) > 0:
                                # 转换表格为文本
                                table_text = self._table_to_text(table_data)

                                table_info = {
                                    "page_num": page_num,
                                    "table_index": table_index,
                                    "rows": len(table_data),
                                    "cols": len(table_data[0]) if table_data else 0,
                                    "data": table_data,
                                    "text": table_text
                                }

                                tables.append(table_info)

            logger.info(f"提取到 {len(tables)} 个表格")
            return tables

        except Exception as e:
            logger.warning(f"提取PDF表格失败: {str(e)}")
            return []

    def _table_to_text(self, table_data: List[List[str]]) -> str:
        """
        将表格数据转换为文本格式

        参数：
            table_data: 表格数据（二维列表）

        返回：
            str: 格式化的表格文本

        示例：
            输入: [['姓名', '年龄'], ['张三', '25'], ['李四', '30']]
            输出:
            姓名 | 年龄
            张三 | 25
            李四 | 30
        """
        if not table_data:
            return ""

        try:
            lines = []
            for row in table_data:
                # 清理每个单元格的内容
                cleaned_row = [
                    str(cell).strip() if cell else ""
                    for cell in row
                ]
                # 用 | 分隔
                line = " | ".join(cleaned_row)
                lines.append(line)

            return "\n".join(lines)

        except Exception as e:
            logger.warning(f"表格转文本失败: {str(e)}")
            return ""

    def _is_scanned_pdf(self, text: str, page_count: int) -> bool:
        """
        判断PDF是否为扫描件

        参数：
            text: 提取的文本
            page_count: 页数

        返回：
            bool: True表示是扫描件，需要OCR

        💡 判断逻辑：
        - 如果平均每页字符数 < 100，可能是扫描件
        - 如果完全没有文本，肯定是扫描件
        """
        if not text or len(text.strip()) == 0:
            return True

        # 计算平均每页字符数
        avg_chars_per_page = len(text) / page_count if page_count > 0 else 0

        # 阈值：平均每页少于100个字符，认为是扫描件
        threshold = 100

        is_scanned = avg_chars_per_page < threshold

        if is_scanned:
            logger.info(
                f"检测到扫描PDF: 平均每页 {avg_chars_per_page:.0f} 字符 "
                f"(阈值: {threshold})"
            )

        return is_scanned

    def extract_page_range(
            self,
            file_path: str,
            start_page: int,
            end_page: int
    ) -> str:
        """
        提取指定页面范围的文本

        参数：
            file_path: PDF文件路径
            start_page: 起始页码（从1开始）
            end_page: 结束页码（包含）

        返回：
            str: 提取的文本
        """
        try:
            text_parts = []

            with pdfplumber.open(file_path) as pdf:
                # 确保页码在有效范围内
                start_idx = max(0, start_page - 1)
                end_idx = min(len(pdf.pages), end_page)

                for page_num in range(start_idx, end_idx):
                    page = pdf.pages[page_num]
                    text = page.extract_text() or ""
                    text_parts.append(text)

            return "\n\n".join(text_parts)

        except Exception as e:
            logger.error(f"提取页面范围失败: {str(e)}")
            raise

    def get_page_count(self, file_path: str) -> int:
        """
        获取PDF页数

        参数：
            file_path: PDF文件路径

        返回：
            int: 页数
        """
        try:
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                return len(pdf_reader.pages)
        except Exception as e:
            logger.error(f"获取PDF页数失败: {str(e)}")
            return 0


# =========================================
# 💡 使用示例
# =========================================
"""
# 1. 基础使用
from services.document.pdf_parser import PDFParser

parser = PDFParser()

# 解析PDF
result = parser.parse("data/raw_docs/GB50009-2012.pdf")

print(f"文档标题: {result['metadata']['title']}")
print(f"总页数: {result['total_pages']}")
print(f"表格数: {len(result['tables'])}")
print(f"是否扫描件: {result['is_scanned']}")

# 访问文本内容
full_text = result['text']
print(f"全文长度: {len(full_text)}")

# 访问每页内容
for page in result['pages']:
    print(f"第{page['page_num']}页: {page['char_count']}字符")

# 访问表格
for table in result['tables']:
    print(f"第{table['page_num']}页的表格:")
    print(table['text'])


# 2. 提取指定页面
text = parser.extract_page_range("document.pdf", start_page=1, end_page=5)
print(text)


# 3. 获取页数
page_count = parser.get_page_count("document.pdf")
print(f"总页数: {page_count}")
"""