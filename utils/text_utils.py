"""
========================================
文本处理工具
========================================

📚 模块说明：
- 文本预处理工具
- 分词和标准化
- 支持中英文混合

🎯 核心功能：
1. 中英文分词
2. 停用词过滤
3. 文本标准化
4. 关键词提取

========================================
"""

import re
from typing import List, Set, Optional

import jieba
import jieba.analyse
from loguru import logger


class TextProcessor:
    """
    文本处理器

    🔧 功能：
    - 中文分词（jieba）
    - 英文分词
    - 停用词过滤
    - 文本标准化

    💡 应用场景：
    - BM25检索预处理
    - 关键词提取
    - 文本清洗
    """

    # 默认中文停用词
    DEFAULT_STOPWORDS = {
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人',
        '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去',
        '你', '会', '着', '没有', '看', '好', '自己', '这', '能', '那',
        '来', '但', '与', '对', '于', '由', '从', '以', '向', '用',
        '比', '或', '被', '因', '所', '而', '及', '等', '为', '之'
    }

    def __init__(
            self,
            use_stopwords: bool = True,
            custom_stopwords: Optional[Set[str]] = None,
            enable_jieba_userdict: bool = False,
            userdict_path: Optional[str] = None
    ):
        """
        初始化文本处理器

        参数：
            use_stopwords: 是否使用停用词过滤
            custom_stopwords: 自定义停用词集合
            enable_jieba_userdict: 是否启用jieba自定义词典
            userdict_path: 自定义词典路径
        """
        self.use_stopwords = use_stopwords

        # 停用词集合
        self.stopwords = self.DEFAULT_STOPWORDS.copy()
        if custom_stopwords:
            self.stopwords.update(custom_stopwords)

        # 设置jieba日志级别
        jieba.setLogLevel(jieba.logging.INFO)

        # 加载自定义词典
        if enable_jieba_userdict and userdict_path:
            try:
                jieba.load_userdict(userdict_path)
                logger.info(f"加载jieba自定义词典: {userdict_path}")
            except Exception as e:
                logger.warning(f"加载自定义词典失败: {e}")

        logger.info("文本处理器初始化完成")

    def tokenize(
            self,
            text: str,
            mode: str = 'search'
    ) -> List[str]:
        """
        文本分词

        参数：
            text: 输入文本
            mode: 分词模式
                - 'default': 精确模式
                - 'search': 搜索引擎模式（推荐）
                - 'all': 全模式

        返回：
            词列表
        """
        if not text or not text.strip():
            return []

        # 预处理
        text = self._preprocess(text)

        # 分词
        if mode == 'search':
            tokens = jieba.cut_for_search(text)
        elif mode == 'all':
            tokens = jieba.cut(text, cut_all=True)
        else:  # default
            tokens = jieba.cut(text, cut_all=False)

        tokens = list(tokens)

        # 过滤
        tokens = self._filter_tokens(tokens)

        return tokens

    def tokenize_batch(
            self,
            texts: List[str],
            mode: str = 'search'
    ) -> List[List[str]]:
        """批量分词"""
        return [self.tokenize(text, mode) for text in texts]

    def extract_keywords(
            self,
            text: str,
            top_k: int = 10,
            method: str = 'tfidf'
    ) -> List[str]:
        """
        提取关键词

        参数：
            text: 输入文本
            top_k: 提取数量
            method: 提取方法
                - 'tfidf': TF-IDF
                - 'textrank': TextRank

        返回：
            关键词列表
        """
        if not text or not text.strip():
            return []

        try:
            if method == 'tfidf':
                keywords = jieba.analyse.extract_tags(
                    text,
                    topK=top_k,
                    withWeight=False
                )
            elif method == 'textrank':
                keywords = jieba.analyse.textrank(
                    text,
                    topK=top_k,
                    withWeight=False
                )
            else:
                raise ValueError(f"不支持的关键词提取方法: {method}")

            return list(keywords)

        except Exception as e:
            logger.error(f"关键词提取失败: {e}")
            return []

    def _preprocess(self, text: str) -> str:
        """
        文本预处理

        处理：
        1. 转小写
        2. 去除多余空白
        3. 保留中英文、数字、常用标点
        """
        # 转小写（保留中文）
        text = text.lower()

        # 去除URL
        text = re.sub(r'http[s]?://\S+', '', text)

        # 去除邮箱
        text = re.sub(r'\S+@\S+', '', text)

        # 去除特殊字符（保留中英文、数字、空格、常用标点）
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s.,!?;:，。！？；：]', ' ', text)

        # 统一空白符
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def _filter_tokens(self, tokens: List[str]) -> List[str]:
        """
        过滤词元

        过滤规则：
        1. 停用词
        2. 单字符（除了有意义的字）
        3. 纯数字
        4. 纯空白
        """
        filtered = []

        for token in tokens:
            token = token.strip()

            # 跳过空白
            if not token:
                continue

            # 跳过停用词
            if self.use_stopwords and token in self.stopwords:
                continue

            # 跳过单字符（除了有意义的中文字）
            if len(token) == 1 and not self._is_meaningful_char(token):
                continue

            # 跳过纯标点
            if re.match(r'^[.,!?;:，。！？；：]+$', token):
                continue

            filtered.append(token)

        return filtered

    def _is_meaningful_char(self, char: str) -> bool:
        """判断单字符是否有意义（主要针对中文）"""
        # 中文字符一般都有意义
        if '\u4e00' <= char <= '\u9fa5':
            return True

        # 英文字母（A-Z, a-z）
        if char.isalpha():
            return True

        return False

    def add_stopwords(self, words: List[str]):
        """添加停用词"""
        self.stopwords.update(words)
        logger.info(f"添加 {len(words)} 个停用词")

    def remove_stopwords(self, words: List[str]):
        """移除停用词"""
        for word in words:
            self.stopwords.discard(word)
        logger.info(f"移除 {len(words)} 个停用词")

    def get_stopwords(self) -> Set[str]:
        """获取当前停用词集合"""
        return self.stopwords.copy()


# =========================================
# 💡 使用示例
# =========================================
"""
from services.retrieval.text_utils import TextProcessor

# 1. 基础分词
processor = TextProcessor()

text = "建筑结构荷载规范GB50009-2012是工程设计的重要标准"
tokens = processor.tokenize(text)
print(f"分词结果: {tokens}")
# 输出: ['建筑', '结构', '荷载', '规范', 'gb50009', '2012', '工程', '设计', '重要', '标准']


# 2. 批量分词
texts = ["文本1", "文本2", "文本3"]
tokens_list = processor.tokenize_batch(texts)


# 3. 关键词提取
text = '''
建筑结构荷载规范是建筑工程设计中的基础性标准，
主要规定了各类荷载的取值方法和组合原则。
'''

keywords_tfidf = processor.extract_keywords(text, top_k=5, method='tfidf')
keywords_textrank = processor.extract_keywords(text, top_k=5, method='textrank')

print(f"TF-IDF关键词: {keywords_tfidf}")
print(f"TextRank关键词: {keywords_textrank}")


# 4. 自定义停用词
custom_stopwords = {'建筑', '工程'}
processor = TextProcessor(custom_stopwords=custom_stopwords)

# 或动态添加
processor.add_stopwords(['设计', '标准'])


# 5. 不使用停用词
processor = TextProcessor(use_stopwords=False)
tokens = processor.tokenize(text)
"""