"""
========================================
Utils 工具模块初始化
========================================

📚 模块说明：
- 导入所有工具函数
- 提供统一的导入接口

========================================
"""

# ===== 导入文件工具 =====
from utils.file_utils import (
    ensure_dir,
    get_file_size,
    format_file_size,
    get_file_extension,
    get_file_name,
    get_mime_type,
    is_file_type,
    list_files,
    copy_file,
    move_file,
    delete_file,
    read_text_file,
    write_text_file,
    read_binary_file,
    write_binary_file,
    get_file_info,
    safe_filename,
    generate_unique_filename,
)

# ===== 导入哈希工具 =====
from utils.hash_utils import (
    md5_hash,
    sha256_hash,
    file_md5,
    file_sha256,
    content_fingerprint,
    document_fingerprint,
    chunk_fingerprint,
    is_duplicate,
    compute_similarity_hash,
    hamming_distance,
    is_near_duplicate,
    generate_unique_id,
    hash_dict,
    DeduplicationManager,
)

# ===== 导入文本工具 =====
from utils.text_utils import TextProcessor

# ===== 导出列表 =====
__all__ = [
    # 文件工具
    "ensure_dir",
    "get_file_size",
    "format_file_size",
    "get_file_extension",
    "get_file_name",
    "get_mime_type",
    "is_file_type",
    "list_files",
    "copy_file",
    "move_file",
    "delete_file",
    "read_text_file",
    "write_text_file",
    "read_binary_file",
    "write_binary_file",
    "get_file_info",
    "safe_filename",
    "generate_unique_filename",

    # 哈希工具
    "md5_hash",
    "sha256_hash",
    "file_md5",
    "file_sha256",
    "content_fingerprint",
    "document_fingerprint",
    "chunk_fingerprint",
    "is_duplicate",
    "compute_similarity_hash",
    "hamming_distance",
    "is_near_duplicate",
    "generate_unique_id",
    "hash_dict",
    "DeduplicationManager",

    # 文本工具
    "TextProcessor",
]


# =========================================
# 💡 使用示例
# =========================================
"""
# 方式1：统一导入
from utils import ensure_dir, md5_hash, TextProcessor

# 方式2：从具体模块导入
from utils.file_utils import ensure_dir
from utils.hash_utils import md5_hash
from utils.text_utils import TextProcessor
"""
