"""
========================================
文档元数据提取器
========================================

📚 模块说明：
- 从文档中提取结构化元数据
- 自动识别文档属性
- 增强检索和过滤能力

🎯 核心功能：
1. 提取文档标题、作者等基础信息
2. 识别文档类型和领域
3. 提取关键词和摘要
4. 生成文档指纹

========================================
"""

import re
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

import jieba
import jieba.analyse
from loguru import logger


class MetadataExtractor:
    """
    元数据提取器

    🔧 提取内容：
    - 基础信息（标题、作者、日期）
    - 文档分类（类型、领域）
    - 关键词和标签
    - 统计信息（字数、段落数）

    💡 应用场景：
    - 文档管理
    - 权限控制
    - 智能检索
    - 数据分析
    """

    # 文档类型识别关键词
    DOC_TYPE_KEYWORDS = {
        'regulation': ['规范', '标准', 'GB', 'JGJ', '国标', '行标'],
        'contract': ['合同', '协议', '甲方', '乙方', '签订'],
        'report': ['报告', '总结', '分析', '调研', '汇报'],
        'manual': ['手册', '指南', '说明书', '操作', '使用'],
        'proposal': ['方案', '计划', '提案', '建议'],
        'notice': ['通知', '公告', '公示', '声明']
    }

    # 领域识别关键词
    DOMAIN_KEYWORDS = {
        'construction': ['建筑', '施工', '工程', '结构', '建造'],
        'legal': ['法律', '法规', '条例', '法条', '司法'],
        'finance': ['财务', '会计', '税务', '审计', '金融'],
        'technology': ['技术', '科技', '研发', '算法', '系统'],
        'management': ['管理', '运营', '组织', '行政', '人力']
    }

    def __init__(self):
        """初始化元数据提取器"""
        # 初始化jieba分词（用于关键词提取）
        jieba.setLogLevel(jieba.logging.INFO)

    def extract(
            self,
            text: str,
            file_path: Optional[str] = None,
            doc_metadata: Optional[Dict] = None
    ) -> Dict:
        """
        提取元数据（主入口）

        参数：
            text: 文档文本
            file_path: 文件路径（可选）
            doc_metadata: 已有的文档元数据（可选）

        返回：
            完整的元数据字典
        """
        logger.debug("开始提取元数据")

        metadata = {}

        # 1. 基础信息
        metadata.update(self._extract_basic_info(text, file_path))

        # 2. 文档分类
        metadata.update(self._extract_classification(text))

        # 3. 关键词提取
        metadata.update(self._extract_keywords(text))

        # 4. 统计信息
        metadata.update(self._extract_statistics(text))

        # 5. 文档指纹
        metadata['doc_fingerprint'] = self._generate_fingerprint(text)

        # 6. 合并已有元数据
        if doc_metadata:
            metadata.update(doc_metadata)

        # 7. 添加提取时间
        metadata['metadata_extracted_at'] = datetime.now().isoformat()

        logger.debug(f"元数据提取完成 | 关键词数: {len(metadata.get('keywords', []))}")

        return metadata

    def _extract_basic_info(
            self,
            text: str,
            file_path: Optional[str]
    ) -> Dict:
        """
        提取基础信息

        提取内容：
        - 标题（从文件名或文档首行）
        - 文件信息
        - 日期
        """
        info = {}

        # 1. 标题
        title = self._extract_title(text, file_path)
        if title:
            info['title'] = title

        # 2. 文件信息
        if file_path:
            path = Path(file_path)
            info['filename'] = path.name
            info['file_extension'] = path.suffix
            info['file_stem'] = path.stem

        # 3. 日期提取
        dates = self._extract_dates(text)
        if dates:
            info['extracted_dates'] = dates
            info['latest_date'] = max(dates)

        # 4. 编号提取（如文件编号、合同编号）
        doc_number = self._extract_document_number(text)
        if doc_number:
            info['document_number'] = doc_number

        return info

    def _extract_title(
            self,
            text: str,
            file_path: Optional[str]
    ) -> Optional[str]:
        """
        提取文档标题

        优先级：
        1. 文档第一行（如果是标题格式）
        2. 文件名
        """
        # 尝试从文本第一行提取
        lines = text.split('\n')
        for line in lines[:5]:  # 只看前5行
            line = line.strip()
            if not line:
                continue

            # 如果是短行且不包含过多标点，可能是标题
            if 5 < len(line) < 100 and line.count('。') < 2:
                return line

        # 从文件名提取
        if file_path:
            return Path(file_path).stem

        return None

    def _extract_classification(self, text: str) -> Dict:
        """
        提取文档分类信息

        返回：
            {
                'doc_type': str,      # 文档类型
                'domain': str,        # 所属领域
                'confidence': float   # 分类置信度
            }
        """
        classification = {}

        # 文档类型识别
        doc_type, type_confidence = self._classify_by_keywords(
            text,
            self.DOC_TYPE_KEYWORDS
        )
        if doc_type:
            classification['doc_type'] = doc_type
            classification['type_confidence'] = type_confidence

        # 领域识别
        domain, domain_confidence = self._classify_by_keywords(
            text,
            self.DOMAIN_KEYWORDS
        )
        if domain:
            classification['domain'] = domain
            classification['domain_confidence'] = domain_confidence

        return classification

    def _classify_by_keywords(
            self,
            text: str,
            keyword_dict: Dict[str, List[str]]
    ) -> Tuple[Optional[str], float]:
        """
        基于关键词的分类

        返回：
            (分类标签, 置信度)
        """
        # 统计每个类别的关键词出现次数
        scores = {}

        for category, keywords in keyword_dict.items():
            count = 0
            for keyword in keywords:
                count += text.count(keyword)
            scores[category] = count

        # 找出得分最高的类别
        if not scores or max(scores.values()) == 0:
            return None, 0.0

        best_category = max(scores, key=scores.get)
        total_count = sum(scores.values())
        confidence = scores[best_category] / total_count if total_count > 0 else 0

        return best_category, confidence

    def _extract_keywords(
            self,
            text: str,
            top_k: int = 10
    ) -> Dict:
        """
        提取关键词

        参数：
            text: 文本
            top_k: 提取前k个关键词

        返回：
            {
                'keywords': List[str],           # 关键词列表
                'keyword_weights': Dict[str, float]  # 关键词权重
            }
        """
        # 使用jieba的TF-IDF提取关键词
        try:
            keywords_with_weights = jieba.analyse.extract_tags(
                text,
                topK=top_k,
                withWeight=True
            )

            keywords = [kw for kw, weight in keywords_with_weights]
            keyword_weights = {kw: weight for kw, weight in keywords_with_weights}

            return {
                'keywords': keywords,
                'keyword_weights': keyword_weights
            }
        except Exception as e:
            logger.warning(f"关键词提取失败: {e}")
            return {
                'keywords': [],
                'keyword_weights': {}
            }

    def _extract_statistics(self, text: str) -> Dict:
        """
        提取统计信息

        返回：
            {
                'char_count': int,        # 字符数
                'word_count': int,        # 词数
                'line_count': int,        # 行数
                'paragraph_count': int,   # 段落数
                'avg_line_length': float, # 平均行长
                'language': str           # 主要语言
            }
        """
        stats = {}

        # 字符数
        stats['char_count'] = len(text)

        # 行数和段落数
        lines = [line for line in text.split('\n') if line.strip()]
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        stats['line_count'] = len(lines)
        stats['paragraph_count'] = len(paragraphs)

        # 平均行长
        if lines:
            stats['avg_line_length'] = sum(len(line) for line in lines) / len(lines)
        else:
            stats['avg_line_length'] = 0

        # 词数（中文按字，英文按单词）
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
        stats['word_count'] = chinese_chars + english_words

        # 语言检测
        if chinese_chars > english_words * 5:
            stats['language'] = 'chinese'
        elif english_words > chinese_chars:
            stats['language'] = 'english'
        else:
            stats['language'] = 'mixed'

        return stats

    def _extract_dates(self, text: str) -> List[str]:
        """
        提取文档中的日期

        支持格式：
        - 2024年1月1日
        - 2024-01-01
        - 2024/01/01
        """
        date_patterns = [
            r'\d{4}年\d{1,2}月\d{1,2}日',
            r'\d{4}-\d{1,2}-\d{1,2}',
            r'\d{4}/\d{1,2}/\d{1,2}',
        ]

        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            dates.extend(matches)

        # 去重并排序
        dates = sorted(set(dates))

        return dates

    def _extract_document_number(self, text: str) -> Optional[str]:
        """
        提取文档编号

        常见格式：
        - GB50009-2012
        - JGJ 123-2020
        - [2024]001号
        """
        patterns = [
            r'GB\s*\d+[-–]\d{4}',
            r'JGJ\s*\d+[-–]\d{4}',
            r'\[\d{4}\]\d+号',
            r'No\.\s*\d+',
        ]

        for pattern in patterns:
            match = re.search(pattern, text[:1000])  # 只在开头搜索
            if match:
                return match.group(0)

        return None

    def _generate_fingerprint(self, text: str) -> str:
        """
        生成文档指纹（用于去重和比对）

        使用MD5哈希前1000个字符
        """
        sample = text[:1000].encode('utf-8')
        return hashlib.md5(sample).hexdigest()


# =========================================
# 💡 使用示例
# =========================================
"""
from services.document.metadata import MetadataExtractor

# 1. 基础使用
extractor = MetadataExtractor()

text = '''
建筑结构荷载规范 GB50009-2012

第一章 总则

1.0.1 为了在建筑结构设计中合理确定荷载...
'''

metadata = extractor.extract(text, file_path="GB50009-2012.pdf")

print(f"标题: {metadata.get('title')}")
print(f"文档类型: {metadata.get('doc_type')}")
print(f"领域: {metadata.get('domain')}")
print(f"关键词: {metadata.get('keywords')}")
print(f"字符数: {metadata.get('char_count')}")


# 2. 带已有元数据
existing_metadata = {
    'author': '中华人民共和国住房和城乡建设部',
    'publish_date': '2012-05-01'
}

metadata = extractor.extract(
    text,
    file_path="GB50009-2012.pdf",
    doc_metadata=existing_metadata
)
"""