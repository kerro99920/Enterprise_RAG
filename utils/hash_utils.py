"""
========================================
哈希工具函数
========================================

📚 模块说明：
- 文件和文本哈希计算
- 内容去重
- 指纹生成

🎯 核心功能：
1. MD5/SHA256 哈希
2. 文件指纹
3. 内容去重检测
4. 相似度计算

========================================
"""

import hashlib
import os
from pathlib import Path
from typing import Union, List, Optional
import json

from loguru import logger


def md5_hash(content: Union[str, bytes]) -> str:
    """
    计算 MD5 哈希值

    参数：
        content: 字符串或字节内容

    返回：
        str: 32位十六进制哈希值
    """
    if isinstance(content, str):
        content = content.encode('utf-8')

    return hashlib.md5(content).hexdigest()


def sha256_hash(content: Union[str, bytes]) -> str:
    """
    计算 SHA256 哈希值

    参数：
        content: 字符串或字节内容

    返回：
        str: 64位十六进制哈希值
    """
    if isinstance(content, str):
        content = content.encode('utf-8')

    return hashlib.sha256(content).hexdigest()


def file_md5(file_path: Union[str, Path], chunk_size: int = 8192) -> str:
    """
    计算文件的 MD5 哈希值

    参数：
        file_path: 文件路径
        chunk_size: 分块大小（用于大文件）

    返回：
        str: 32位十六进制哈希值
    """
    md5 = hashlib.md5()

    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            md5.update(chunk)

    return md5.hexdigest()


def file_sha256(file_path: Union[str, Path], chunk_size: int = 8192) -> str:
    """
    计算文件的 SHA256 哈希值

    参数：
        file_path: 文件路径
        chunk_size: 分块大小（用于大文件）

    返回：
        str: 64位十六进制哈希值
    """
    sha256 = hashlib.sha256()

    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            sha256.update(chunk)

    return sha256.hexdigest()


def content_fingerprint(
    text: str,
    length: int = 16,
    normalize: bool = True
) -> str:
    """
    生成文本内容指纹

    用于快速比较两段文本是否相同

    参数：
        text: 文本内容
        length: 指纹长度（截取哈希值的前N位）
        normalize: 是否标准化文本（去除空格、换行等）

    返回：
        str: 内容指纹
    """
    if normalize:
        # 标准化：去除空格、换行、转小写
        text = ''.join(text.split()).lower()

    full_hash = md5_hash(text)
    return full_hash[:length]


def document_fingerprint(
    text: str,
    sample_size: int = 1000
) -> str:
    """
    生成文档指纹

    只采样文档的开头部分，用于快速去重

    参数：
        text: 文档内容
        sample_size: 采样大小（字符数）

    返回：
        str: 文档指纹
    """
    sample = text[:sample_size]
    return content_fingerprint(sample)


def chunk_fingerprint(
    text: str,
    doc_id: str,
    chunk_index: int
) -> str:
    """
    生成文档块指纹

    结合文档ID、块索引和内容生成唯一指纹

    参数：
        text: 块内容
        doc_id: 文档ID
        chunk_index: 块索引

    返回：
        str: 块指纹
    """
    combined = f"{doc_id}:{chunk_index}:{text[:200]}"
    return md5_hash(combined)


def is_duplicate(
    fingerprint: str,
    existing_fingerprints: List[str]
) -> bool:
    """
    检查是否重复

    参数：
        fingerprint: 待检查的指纹
        existing_fingerprints: 已存在的指纹列表

    返回：
        bool: 是否重复
    """
    return fingerprint in existing_fingerprints


def compute_similarity_hash(
    text: str,
    n_features: int = 128
) -> List[int]:
    """
    计算 SimHash（相似哈希）

    用于检测近似重复的文本

    参数：
        text: 文本内容
        n_features: 特征数量

    返回：
        List[int]: SimHash 向量
    """
    import re

    # 分词
    words = re.findall(r'\w+', text.lower())

    # 初始化向量
    v = [0] * n_features

    for word in words:
        # 计算词的哈希
        word_hash = int(md5_hash(word), 16)

        for i in range(n_features):
            bitmask = 1 << i
            if word_hash & bitmask:
                v[i] += 1
            else:
                v[i] -= 1

    # 转换为二进制指纹
    fingerprint = [1 if x > 0 else 0 for x in v]

    return fingerprint


def hamming_distance(hash1: List[int], hash2: List[int]) -> int:
    """
    计算两个哈希的汉明距离

    参数：
        hash1: 第一个哈希
        hash2: 第二个哈希

    返回：
        int: 汉明距离（不同位的数量）
    """
    if len(hash1) != len(hash2):
        raise ValueError("哈希长度必须相同")

    return sum(b1 != b2 for b1, b2 in zip(hash1, hash2))


def is_near_duplicate(
    text1: str,
    text2: str,
    threshold: float = 0.9
) -> bool:
    """
    检测两段文本是否近似重复

    参数：
        text1: 第一段文本
        text2: 第二段文本
        threshold: 相似度阈值（0-1）

    返回：
        bool: 是否近似重复
    """
    hash1 = compute_similarity_hash(text1)
    hash2 = compute_similarity_hash(text2)

    distance = hamming_distance(hash1, hash2)
    similarity = 1 - (distance / len(hash1))

    return similarity >= threshold


def generate_unique_id(
    prefix: str = "",
    length: int = 8
) -> str:
    """
    生成唯一ID

    参数：
        prefix: ID前缀
        length: ID长度（不含前缀）

    返回：
        str: 唯一ID
    """
    import uuid
    import time

    # 结合时间戳和UUID
    unique_str = f"{time.time()}{uuid.uuid4()}"
    hash_value = md5_hash(unique_str)[:length]

    if prefix:
        return f"{prefix}_{hash_value}"
    return hash_value


def hash_dict(data: dict) -> str:
    """
    计算字典的哈希值

    参数：
        data: 字典数据

    返回：
        str: 哈希值
    """
    # 转换为排序后的 JSON 字符串
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return md5_hash(json_str)


class DeduplicationManager:
    """
    去重管理器

    用于管理已处理文档的指纹，避免重复处理
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化去重管理器

        参数：
            storage_path: 指纹存储文件路径
        """
        self.fingerprints = set()
        self.storage_path = storage_path

        if storage_path and os.path.exists(storage_path):
            self.load()

    def add(self, fingerprint: str) -> bool:
        """
        添加指纹

        参数：
            fingerprint: 指纹

        返回：
            bool: 是否为新指纹（True=新，False=重复）
        """
        if fingerprint in self.fingerprints:
            return False

        self.fingerprints.add(fingerprint)
        return True

    def check(self, fingerprint: str) -> bool:
        """
        检查指纹是否存在

        参数：
            fingerprint: 指纹

        返回：
            bool: 是否存在
        """
        return fingerprint in self.fingerprints

    def remove(self, fingerprint: str):
        """移除指纹"""
        self.fingerprints.discard(fingerprint)

    def clear(self):
        """清空所有指纹"""
        self.fingerprints.clear()

    def save(self):
        """保存指纹到文件"""
        if self.storage_path:
            with open(self.storage_path, 'w') as f:
                json.dump(list(self.fingerprints), f)
            logger.debug(f"指纹已保存: {len(self.fingerprints)} 个")

    def load(self):
        """从文件加载指纹"""
        if self.storage_path and os.path.exists(self.storage_path):
            with open(self.storage_path, 'r') as f:
                self.fingerprints = set(json.load(f))
            logger.debug(f"指纹已加载: {len(self.fingerprints)} 个")

    def __len__(self):
        return len(self.fingerprints)

    def __contains__(self, fingerprint: str):
        return fingerprint in self.fingerprints


# =========================================
# 💡 使用示例
# =========================================
"""
from utils.hash_utils import *

# 1. 计算文本哈希
text = "这是一段测试文本"
print(f"MD5: {md5_hash(text)}")
print(f"SHA256: {sha256_hash(text)}")

# 2. 计算文件哈希
print(f"文件MD5: {file_md5('document.pdf')}")
print(f"文件SHA256: {file_sha256('document.pdf')}")

# 3. 生成内容指纹
fingerprint = content_fingerprint(text)
print(f"内容指纹: {fingerprint}")

# 4. 文档指纹
doc_fp = document_fingerprint(long_text)
print(f"文档指纹: {doc_fp}")

# 5. 检测近似重复
text1 = "这是第一段文本内容"
text2 = "这是第一段文本内容。"  # 只多了一个句号
is_dup = is_near_duplicate(text1, text2, threshold=0.8)
print(f"是否近似重复: {is_dup}")

# 6. 生成唯一ID
unique_id = generate_unique_id(prefix="doc", length=8)
print(f"唯一ID: {unique_id}")  # 如: doc_a1b2c3d4

# 7. 使用去重管理器
dedup = DeduplicationManager(storage_path="data/fingerprints.json")

# 添加指纹
is_new = dedup.add(fingerprint)
if is_new:
    print("新文档，开始处理")
else:
    print("重复文档，跳过")

# 检查指纹
if fingerprint in dedup:
    print("已存在")

# 保存
dedup.save()
"""
