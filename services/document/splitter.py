"""
========================================
文本分块器
========================================

📚 模块说明：
- 将长文档切分为适合检索的小块
- 保持语义完整性
- 支持多种分块策略

🎯 核心功能：
1. 智能语义分块
2. 固定长度分块
3. 递归分块
4. 滑动窗口

========================================
"""

import re
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass

import jieba
from loguru import logger


@dataclass
class Chunk:
    """
    文本块数据类

    属性：
        text: 块文本
        start_idx: 在原文中的起始位置
        end_idx: 在原文中的结束位置
        metadata: 块的元数据
    """
    text: str
    start_idx: int
    end_idx: int
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    @property
    def length(self) -> int:
        """块的长度（字符数）"""
        return len(self.text)

    @property
    def token_count(self) -> int:
        """块的token数（中文按字数，英文按单词数）"""
        # 简单估算：中文1字=1token，英文1词≈1.3token
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', self.text))
        english_words = len(re.findall(r'[a-zA-Z]+', self.text))
        return chinese_chars + int(english_words * 1.3)


class DocumentSplitter:
    """
    文档分块器

    🔧 分块策略：
    1. semantic_split: 语义分块（按段落、章节）
    2. fixed_split: 固定长度分块
    3. recursive_split: 递归分块（优先保持语义）
    4. sliding_window: 滑动窗口分块

    💡 设计原则：
    - 尽量保持语义完整
    - 避免截断句子
    - 支持块之间的重叠
    """

    # 默认分隔符优先级（从高到低）
    DEFAULT_SEPARATORS = [
        '\n\n\n',  # 大段落分隔
        '\n\n',  # 段落分隔
        '\n',  # 换行
        '。',  # 中文句号
        '！',  # 感叹号
        '？',  # 问号
        '；',  # 分号
        '，',  # 逗号
        ' ',  # 空格
        '',  # 字符级分割（最后手段）
    ]

    def __init__(
            self,
            chunk_size: int = 500,
            chunk_overlap: int = 50,
            separators: Optional[List[str]] = None
    ):
        """
        初始化文本分块器

        参数：
            chunk_size: 目标块大小（字符数）
            chunk_overlap: 块之间的重叠大小
            separators: 自定义分隔符列表
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or self.DEFAULT_SEPARATORS

        logger.info(
            f"初始化分块器 | chunk_size={chunk_size}, "
            f"overlap={chunk_overlap}"
        )

    def split(
            self,
            text: str,
            method: str = 'recursive',
            metadata: Optional[Dict] = None
    ) -> List[Chunk]:
        """
        分块主入口

        参数：
            text: 待分块的文本
            method: 分块方法 ('semantic', 'fixed', 'recursive', 'sliding')
            metadata: 文档元数据（会传递给每个块）

        返回：
            分块列表
        """
        if not text or not text.strip():
            return []

        logger.debug(f"开始分块 | 方法: {method} | 原始长度: {len(text)}")

        # 选择分块方法
        if method == 'semantic':
            chunks = self._semantic_split(text)
        elif method == 'fixed':
            chunks = self._fixed_split(text)
        elif method == 'recursive':
            chunks = self._recursive_split(text)
        elif method == 'sliding':
            chunks = self._sliding_window_split(text)
        else:
            raise ValueError(f"不支持的分块方法: {method}")

        # 添加元数据
        if metadata:
            for chunk in chunks:
                chunk.metadata.update(metadata)

        # 添加块序号
        for idx, chunk in enumerate(chunks):
            chunk.metadata['chunk_index'] = idx
            chunk.metadata['total_chunks'] = len(chunks)

        logger.info(
            f"分块完成 | 方法: {method} | "
            f"原始长度: {len(text)} | "
            f"块数: {len(chunks)} | "
            f"平均块大小: {sum(c.length for c in chunks) / len(chunks):.0f}"
        )

        return chunks

    def _semantic_split(self, text: str) -> List[Chunk]:
        """
        语义分块 - 按段落和章节分割

        特点：
        - 保持段落完整
        - 识别章节标题
        - 不严格限制块大小
        """
        chunks = []

        # 按双换行分段
        paragraphs = re.split(r'\n\n+', text)

        current_chunk = ""
        current_start = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # 如果是标题，且当前有内容，先保存当前块
            if self._is_heading(para) and current_chunk:
                chunk = Chunk(
                    text=current_chunk.strip(),
                    start_idx=current_start,
                    end_idx=current_start + len(current_chunk),
                    metadata={'type': 'paragraph'}
                )
                chunks.append(chunk)
                current_chunk = ""
                current_start = current_start + len(current_chunk)

            # 添加段落
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para

            # 如果块太大，分割
            if len(current_chunk) > self.chunk_size * 2:
                chunk = Chunk(
                    text=current_chunk.strip(),
                    start_idx=current_start,
                    end_idx=current_start + len(current_chunk),
                    metadata={'type': 'paragraph'}
                )
                chunks.append(chunk)
                current_chunk = ""
                current_start = current_start + len(current_chunk)

        # 最后一个块
        if current_chunk:
            chunk = Chunk(
                text=current_chunk.strip(),
                start_idx=current_start,
                end_idx=current_start + len(current_chunk),
                metadata={'type': 'paragraph'}
            )
            chunks.append(chunk)

        return chunks

    def _fixed_split(self, text: str) -> List[Chunk]:
        """
        固定长度分块 - 严格按字符数分割

        特点：
        - 块大小均匀
        - 可能截断句子
        - 支持重叠
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]

            chunk = Chunk(
                text=chunk_text,
                start_idx=start,
                end_idx=min(end, len(text)),
                metadata={'type': 'fixed'}
            )
            chunks.append(chunk)

            # 考虑重叠
            start += (self.chunk_size - self.chunk_overlap)

        return chunks

    def _recursive_split(self, text: str) -> List[Chunk]:
        """
        递归分块 - 优先使用高级分隔符，逐步降级

        特点：
        - 优先保持段落完整
        - 其次保持句子完整
        - 最后才字符级分割
        """
        return self._recursive_split_helper(text, self.separators)

    def _recursive_split_helper(
            self,
            text: str,
            separators: List[str],
            start_idx: int = 0
    ) -> List[Chunk]:
        """递归分块辅助函数"""
        chunks = []

        # 如果文本已经足够小，直接返回
        if len(text) <= self.chunk_size:
            return [Chunk(
                text=text,
                start_idx=start_idx,
                end_idx=start_idx + len(text),
                metadata={'type': 'recursive'}
            )]

        # 尝试使用当前分隔符
        if not separators:
            # 无分隔符可用，强制分割
            return self._force_split(text, start_idx)

        separator = separators[0]
        remaining_separators = separators[1:]

        # 分割文本
        if separator:
            splits = text.split(separator)
        else:
            # 字符级分割
            splits = list(text)

        # 合并小块
        current_chunk = ""
        current_start = start_idx

        for i, split in enumerate(splits):
            if not split:
                continue

            # 添加分隔符（除了最后一个）
            if separator and i < len(splits) - 1:
                split += separator

            # 判断是否需要新建块
            if len(current_chunk) + len(split) > self.chunk_size and current_chunk:
                # 当前块已满，保存
                chunks.append(Chunk(
                    text=current_chunk,
                    start_idx=current_start,
                    end_idx=current_start + len(current_chunk),
                    metadata={'type': 'recursive'}
                ))

                # 开始新块（考虑重叠）
                if self.chunk_overlap > 0:
                    overlap_text = current_chunk[-self.chunk_overlap:]
                    current_chunk = overlap_text + split
                    current_start = current_start + len(current_chunk) - self.chunk_overlap - len(split)
                else:
                    current_chunk = split
                    current_start = current_start + len(current_chunk)
            else:
                current_chunk += split

        # 最后一个块
        if current_chunk:
            # 如果块太大，使用下一级分隔符递归分割
            if len(current_chunk) > self.chunk_size:
                sub_chunks = self._recursive_split_helper(
                    current_chunk,
                    remaining_separators,
                    current_start
                )
                chunks.extend(sub_chunks)
            else:
                chunks.append(Chunk(
                    text=current_chunk,
                    start_idx=current_start,
                    end_idx=current_start + len(current_chunk),
                    metadata={'type': 'recursive'}
                ))

        return chunks

    def _sliding_window_split(self, text: str) -> List[Chunk]:
        """
        滑动窗口分块

        特点：
        - 高重叠率
        - 适合问答场景
        - 确保关键信息不丢失
        """
        chunks = []
        window_size = self.chunk_size
        step_size = self.chunk_size - self.chunk_overlap

        start = 0
        while start < len(text):
            end = min(start + window_size, len(text))
            chunk_text = text[start:end]

            chunk = Chunk(
                text=chunk_text,
                start_idx=start,
                end_idx=end,
                metadata={'type': 'sliding_window'}
            )
            chunks.append(chunk)

            start += step_size

            # 如果剩余文本很短，直接加入最后一个块
            if len(text) - start < step_size:
                break

        return chunks

    def _force_split(self, text: str, start_idx: int) -> List[Chunk]:
        """强制分割（字符级）"""
        chunks = []
        for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
            chunk_text = text[i:i + self.chunk_size]
            chunks.append(Chunk(
                text=chunk_text,
                start_idx=start_idx + i,
                end_idx=start_idx + i + len(chunk_text),
                metadata={'type': 'forced'}
            ))
        return chunks

    def _is_heading(self, text: str) -> bool:
        """判断是否为标题"""
        # 章节标题模式
        patterns = [
            r'^第[一二三四五六七八九十百千\d]+[章节条]',
            r'^\d+[\.\s]',
            r'^[一二三四五六七八九十]+[\.\、]',
        ]

        for pattern in patterns:
            if re.match(pattern, text.strip()):
                return True

        return False


# =========================================
# 💡 使用示例
# =========================================
"""
from services.document.splitter import DocumentSplitter

# 1. 递归分块（推荐）
splitter = DocumentSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split(long_text, method='recursive')

for chunk in chunks:
    print(f"块{chunk.metadata['chunk_index']}: {chunk.length}字符")
    print(chunk.text[:100])
    print("---")


# 2. 语义分块
splitter = DocumentSplitter(chunk_size=1000, chunk_overlap=100)
chunks = splitter.split(long_text, method='semantic')


# 3. 滑动窗口（高重叠）
splitter = DocumentSplitter(chunk_size=300, chunk_overlap=150)
chunks = splitter.split(long_text, method='sliding')


# 4. 带元数据
metadata = {
    'doc_id': 'GB50009-2012',
    'source': 'PDF',
    'page': 1
}
chunks = splitter.split(text, method='recursive', metadata=metadata)
"""