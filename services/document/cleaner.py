"""
========================================
文档清洗器
========================================

📚 模块说明：
- 清洗文档中的噪声和无用信息
- 统一文本格式
- 提高检索和生成质量

🎯 核心功能：
1. 去除特殊字符和噪声
2. 修复常见格式问题
3. 标准化空白符
4. 去除重复内容

========================================
"""

import re
from typing import List, Dict, Optional
from loguru import logger


class DocumentCleaner:
    """
    文档清洗器

    🔧 清洗策略：
    - 去除无效字符
    - 修复换行问题
    - 统一空白符
    - 去除重复段落

    💡 设计原则：
    - 保留有意义的内容
    - 修复而非删除
    - 可配置清洗强度
    """

    def __init__(
            self,
            remove_urls: bool = True,
            remove_emails: bool = True,
            fix_encoding: bool = True,
            remove_duplicates: bool = True,
            min_line_length: int = 2
    ):
        """
        初始化文档清洗器

        参数：
            remove_urls: 是否删除URL
            remove_emails: 是否删除邮箱
            fix_encoding: 是否修复编码问题
            remove_duplicates: 是否去除重复段落
            min_line_length: 最小行长度（短于此长度的行会被删除）
        """
        self.remove_urls = remove_urls
        self.remove_emails = remove_emails
        self.fix_encoding = fix_encoding
        self.remove_duplicates = remove_duplicates
        self.min_line_length = min_line_length

        # 编译正则表达式（提高性能）
        self._compile_patterns()

    def _compile_patterns(self):
        """预编译常用正则表达式"""
        # URL匹配
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )

        # 邮箱匹配
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )

        # 多余空白符
        self.whitespace_pattern = re.compile(r'\s+')

        # 连续标点符号
        self.punct_pattern = re.compile(r'([。！？，、；：])\1+')

        # 页码模式
        self.page_number_pattern = re.compile(r'^\s*[-–—]\s*\d+\s*[-–—]\s*$')

        # 页眉页脚（常见模式）
        self.header_footer_pattern = re.compile(
            r'(第\s*\d+\s*页|Page\s+\d+|共\s*\d+\s*页|\d+\s*/\s*\d+)',
            re.IGNORECASE
        )

    def clean(self, text: str) -> str:
        """
        清洗文本（主入口）

        参数：
            text: 原始文本

        返回：
            清洗后的文本
        """
        if not text:
            return ""

        logger.debug(f"开始清洗文本 | 原始长度: {len(text)}")

        # 1. 修复编码问题
        if self.fix_encoding:
            text = self._fix_encoding_issues(text)

        # 2. 删除URL和邮箱
        if self.remove_urls:
            text = self.url_pattern.sub('', text)
        if self.remove_emails:
            text = self.email_pattern.sub('', text)

        # 3. 清理特殊字符
        text = self._clean_special_chars(text)

        # 4. 修复换行问题
        text = self._fix_line_breaks(text)

        # 5. 删除页眉页脚
        text = self._remove_headers_footers(text)

        # 6. 标准化空白符
        text = self._normalize_whitespace(text)

        # 7. 去除重复段落
        if self.remove_duplicates:
            text = self._remove_duplicate_paragraphs(text)

        # 8. 最终清理
        text = self._final_cleanup(text)

        logger.debug(f"文本清洗完成 | 清洗后长度: {len(text)}")

        return text.strip()

    def clean_batch(self, texts: List[str]) -> List[str]:
        """
        批量清洗文本

        参数：
            texts: 文本列表

        返回：
            清洗后的文本列表
        """
        return [self.clean(text) for text in texts]

    def _fix_encoding_issues(self, text: str) -> str:
        """
        修复常见的编码问题

        处理：
        - UTF-8编码错误
        - 全角/半角混用
        - 特殊字符替换
        """
        # 全角转半角（除了中文标点）
        replacements = {
            '　': ' ',  # 全角空格
            '（': '(',
            '）': ')',
            '【': '[',
            '】': ']',
            '《': '<',
            '》': '>',
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        # 移除零宽字符
        zero_width_chars = [
            '\u200b',  # 零宽空格
            '\u200c',  # 零宽非连接符
            '\u200d',  # 零宽连接符
            '\ufeff',  # 零宽非换行符
        ]
        for char in zero_width_chars:
            text = text.replace(char, '')

        return text

    def _clean_special_chars(self, text: str) -> str:
        """
        清理特殊字符

        保留：
        - 中英文字符
        - 数字
        - 常用标点符号
        - 换行符
        """
        # 删除控制字符（保留换行和制表符）
        text = ''.join(
            char for char in text
            if char == '\n' or char == '\t' or not (0 <= ord(char) < 32)
        )

        # 修复连续标点符号
        text = self.punct_pattern.sub(r'\1', text)

        return text

    def _fix_line_breaks(self, text: str) -> str:
        """
        修复换行问题

        处理：
        1. PDF中常见的单词断行
        2. 不必要的换行
        3. 中文断行
        """
        lines = text.split('\n')
        fixed_lines = []

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # 跳过空行
            if not line:
                fixed_lines.append('')
                i += 1
                continue

            # 跳过太短的行（可能是页码或噪声）
            if len(line) < self.min_line_length:
                i += 1
                continue

            # 检查是否需要与下一行合并
            if i < len(lines) - 1:
                next_line = lines[i + 1].strip()

                # 如果当前行以连字符结尾（英文单词断行）
                if line.endswith('-') and next_line and next_line[0].islower():
                    line = line[:-1] + next_line  # 合并并删除连字符
                    i += 2
                    fixed_lines.append(line)
                    continue

                # 如果当前行不是以句号结尾，且下一行不是标题
                # （中文文本常见的不必要换行）
                if (
                        line and
                        not line[-1] in '。！？.!?'
                        and next_line
                        and not self._is_heading(next_line)
                ):
                    # 判断是否应该合并
                    if self._should_merge_lines(line, next_line):
                        line = line + next_line
                        i += 2
                        fixed_lines.append(line)
                        continue

            fixed_lines.append(line)
            i += 1

        return '\n'.join(fixed_lines)

    def _should_merge_lines(self, line1: str, line2: str) -> bool:
        """
        判断两行是否应该合并

        逻辑：
        - 如果第一行很短（<50字符）且不是完整句子
        - 如果第二行以小写字母开头（英文）
        - 如果都是中文且没有明显的段落分隔符
        """
        # 英文：下一行以小写字母开头
        if line2 and line2[0].islower():
            return True

        # 中文：两行都较短且没有句号
        if (
                len(line1) < 50
                and len(line2) < 50
                and not line1.endswith(('。', '！', '？'))
        ):
            return True

        return False

    def _is_heading(self, line: str) -> bool:
        """
        判断是否为标题

        特征：
        - 以数字开头（1.、一、第一章等）
        - 全部大写（英文）
        - 较短（<30字符）
        """
        if not line:
            return False

        # 章节标题模式
        heading_patterns = [
            r'^第[一二三四五六七八九十百千\d]+[章节条]',
            r'^\d+[\.\s]',
            r'^[一二三四五六七八九十]+[\.\、]',
        ]

        for pattern in heading_patterns:
            if re.match(pattern, line):
                return True

        # 英文：全大写且较短
        if line.isupper() and len(line) < 30:
            return True

        return False

    def _remove_headers_footers(self, text: str) -> str:
        """
        删除页眉页脚

        常见模式：
        - 页码（第1页、Page 1）
        - 文档标题重复
        """
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()

            # 删除纯页码行
            if self.page_number_pattern.match(line):
                continue

            # 删除页眉页脚标记
            if self.header_footer_pattern.search(line) and len(line) < 50:
                continue

            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def _normalize_whitespace(self, text: str) -> str:
        """
        标准化空白符

        处理：
        1. 多个空格变为单个
        2. 多个换行变为双换行（段落分隔）
        3. 删除行首行尾空格
        """
        # 每行去除首尾空格
        lines = [line.strip() for line in text.split('\n')]

        # 合并连续空行（最多保留一个空行）
        cleaned_lines = []
        prev_empty = False

        for line in lines:
            if not line:
                if not prev_empty:
                    cleaned_lines.append('')
                prev_empty = True
            else:
                # 行内多个空格变为单个
                line = self.whitespace_pattern.sub(' ', line)
                cleaned_lines.append(line)
                prev_empty = False

        return '\n'.join(cleaned_lines)

    def _remove_duplicate_paragraphs(self, text: str) -> str:
        """
        去除重复段落

        注意：
        - 只删除完全相同的段落
        - 保留第一次出现
        """
        paragraphs = text.split('\n\n')
        seen = set()
        unique_paragraphs = []

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # 使用段落的前100个字符作为指纹（避免内存占用过大）
            fingerprint = para[:100]

            if fingerprint not in seen:
                seen.add(fingerprint)
                unique_paragraphs.append(para)

        return '\n\n'.join(unique_paragraphs)

    def _final_cleanup(self, text: str) -> str:
        """
        最终清理

        确保文本格式规范
        """
        # 删除开头和结尾的空白
        text = text.strip()

        # 确保段落之间有明确分隔
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text


# =========================================
# 💡 使用示例
# =========================================
"""
from services.document.cleaner import DocumentCleaner

# 1. 基础使用
cleaner = DocumentCleaner()

raw_text = '''
第 1 页

标    题
这是一段文本，包含了很多
不必要的换行。
这是URL: https://example.com
邮箱: test@example.com

第一章  概述
这是正文内容。。。多余的标点

第 2 页
'''

cleaned = cleaner.clean(raw_text)
print(cleaned)


# 2. 自定义配置
cleaner = DocumentCleaner(
    remove_urls=False,      # 保留URL
    remove_emails=False,    # 保留邮箱
    min_line_length=5       # 最小行长度为5
)

cleaned = cleaner.clean(raw_text)


# 3. 批量清洗
texts = [text1, text2, text3]
cleaned_texts = cleaner.clean_batch(texts)
"""