"""
========================================
文件工具函数
========================================

📚 模块说明：
- 文件操作辅助函数
- 路径处理
- 文件类型检测

🎯 核心功能：
1. 文件读写
2. 路径处理
3. 类型检测
4. 大小计算

========================================
"""

import os
import shutil
import mimetypes
from pathlib import Path
from typing import List, Optional, Union, BinaryIO
from datetime import datetime

from loguru import logger


def ensure_dir(path: Union[str, Path]) -> Path:
    """
    确保目录存在，不存在则创建

    参数：
        path: 目录路径

    返回：
        Path: 目录路径对象
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_size(file_path: Union[str, Path]) -> int:
    """
    获取文件大小（字节）

    参数：
        file_path: 文件路径

    返回：
        int: 文件大小（字节）
    """
    return os.path.getsize(file_path)


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小为可读字符串

    参数：
        size_bytes: 字节数

    返回：
        str: 格式化后的大小（如 "1.5 MB"）
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"


def get_file_extension(file_path: Union[str, Path]) -> str:
    """
    获取文件扩展名（小写）

    参数：
        file_path: 文件路径

    返回：
        str: 扩展名（如 ".pdf"）
    """
    return Path(file_path).suffix.lower()


def get_file_name(file_path: Union[str, Path], with_extension: bool = True) -> str:
    """
    获取文件名

    参数：
        file_path: 文件路径
        with_extension: 是否包含扩展名

    返回：
        str: 文件名
    """
    path = Path(file_path)
    if with_extension:
        return path.name
    return path.stem


def get_mime_type(file_path: Union[str, Path]) -> str:
    """
    获取文件 MIME 类型

    参数：
        file_path: 文件路径

    返回：
        str: MIME 类型（如 "application/pdf"）
    """
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type or "application/octet-stream"


def is_file_type(file_path: Union[str, Path], extensions: List[str]) -> bool:
    """
    检查文件是否为指定类型

    参数：
        file_path: 文件路径
        extensions: 扩展名列表（如 ['.pdf', '.docx']）

    返回：
        bool: 是否匹配
    """
    ext = get_file_extension(file_path)
    return ext in [e.lower() for e in extensions]


def list_files(
    directory: Union[str, Path],
    extensions: Optional[List[str]] = None,
    recursive: bool = False
) -> List[Path]:
    """
    列出目录中的文件

    参数：
        directory: 目录路径
        extensions: 限定扩展名（如 ['.pdf', '.docx']）
        recursive: 是否递归子目录

    返回：
        List[Path]: 文件路径列表
    """
    directory = Path(directory)
    files = []

    if recursive:
        pattern = "**/*"
    else:
        pattern = "*"

    for path in directory.glob(pattern):
        if path.is_file():
            if extensions is None or get_file_extension(path) in extensions:
                files.append(path)

    return sorted(files)


def copy_file(
    src: Union[str, Path],
    dst: Union[str, Path],
    overwrite: bool = False
) -> Path:
    """
    复制文件

    参数：
        src: 源文件路径
        dst: 目标路径
        overwrite: 是否覆盖已存在的文件

    返回：
        Path: 目标文件路径
    """
    src = Path(src)
    dst = Path(dst)

    if dst.is_dir():
        dst = dst / src.name

    if dst.exists() and not overwrite:
        raise FileExistsError(f"文件已存在: {dst}")

    ensure_dir(dst.parent)
    shutil.copy2(src, dst)

    logger.debug(f"文件已复制: {src} -> {dst}")
    return dst


def move_file(
    src: Union[str, Path],
    dst: Union[str, Path],
    overwrite: bool = False
) -> Path:
    """
    移动文件

    参数：
        src: 源文件路径
        dst: 目标路径
        overwrite: 是否覆盖已存在的文件

    返回：
        Path: 目标文件路径
    """
    src = Path(src)
    dst = Path(dst)

    if dst.is_dir():
        dst = dst / src.name

    if dst.exists() and not overwrite:
        raise FileExistsError(f"文件已存在: {dst}")

    ensure_dir(dst.parent)
    shutil.move(str(src), str(dst))

    logger.debug(f"文件已移动: {src} -> {dst}")
    return dst


def delete_file(file_path: Union[str, Path]) -> bool:
    """
    删除文件

    参数：
        file_path: 文件路径

    返回：
        bool: 是否成功删除
    """
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            logger.debug(f"文件已删除: {file_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"删除文件失败: {file_path} | {e}")
        return False


def read_text_file(
    file_path: Union[str, Path],
    encoding: str = 'utf-8'
) -> str:
    """
    读取文本文件

    参数：
        file_path: 文件路径
        encoding: 编码

    返回：
        str: 文件内容
    """
    with open(file_path, 'r', encoding=encoding) as f:
        return f.read()


def write_text_file(
    file_path: Union[str, Path],
    content: str,
    encoding: str = 'utf-8'
) -> Path:
    """
    写入文本文件

    参数：
        file_path: 文件路径
        content: 文件内容
        encoding: 编码

    返回：
        Path: 文件路径
    """
    path = Path(file_path)
    ensure_dir(path.parent)

    with open(path, 'w', encoding=encoding) as f:
        f.write(content)

    return path


def read_binary_file(file_path: Union[str, Path]) -> bytes:
    """
    读取二进制文件

    参数：
        file_path: 文件路径

    返回：
        bytes: 文件内容
    """
    with open(file_path, 'rb') as f:
        return f.read()


def write_binary_file(
    file_path: Union[str, Path],
    content: bytes
) -> Path:
    """
    写入二进制文件

    参数：
        file_path: 文件路径
        content: 文件内容

    返回：
        Path: 文件路径
    """
    path = Path(file_path)
    ensure_dir(path.parent)

    with open(path, 'wb') as f:
        f.write(content)

    return path


def get_file_info(file_path: Union[str, Path]) -> dict:
    """
    获取文件详细信息

    参数：
        file_path: 文件路径

    返回：
        dict: 文件信息
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    stat = path.stat()

    return {
        'name': path.name,
        'stem': path.stem,
        'extension': path.suffix,
        'path': str(path.absolute()),
        'parent': str(path.parent),
        'size': stat.st_size,
        'size_formatted': format_file_size(stat.st_size),
        'mime_type': get_mime_type(path),
        'created_time': datetime.fromtimestamp(stat.st_ctime).isoformat(),
        'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
        'is_file': path.is_file(),
        'is_dir': path.is_dir()
    }


def safe_filename(filename: str, replacement: str = '_') -> str:
    """
    将文件名转换为安全的文件名

    参数：
        filename: 原始文件名
        replacement: 替换字符

    返回：
        str: 安全的文件名
    """
    # 不安全的字符
    unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\0']

    for char in unsafe_chars:
        filename = filename.replace(char, replacement)

    # 去除首尾空格和点
    filename = filename.strip(' .')

    # 限制长度
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext

    return filename


def generate_unique_filename(
    directory: Union[str, Path],
    filename: str
) -> str:
    """
    生成唯一的文件名

    如果文件已存在，添加数字后缀

    参数：
        directory: 目录路径
        filename: 原始文件名

    返回：
        str: 唯一的文件名
    """
    directory = Path(directory)
    path = directory / filename

    if not path.exists():
        return filename

    name, ext = os.path.splitext(filename)
    counter = 1

    while True:
        new_filename = f"{name}_{counter}{ext}"
        if not (directory / new_filename).exists():
            return new_filename
        counter += 1


# =========================================
# 💡 使用示例
# =========================================
"""
from utils.file_utils import *

# 1. 确保目录存在
ensure_dir("data/processed")

# 2. 获取文件信息
info = get_file_info("document.pdf")
print(f"文件大小: {info['size_formatted']}")
print(f"MIME类型: {info['mime_type']}")

# 3. 列出目录中的 PDF 文件
pdf_files = list_files("data/raw_docs", extensions=['.pdf'], recursive=True)
for f in pdf_files:
    print(f)

# 4. 复制文件
copy_file("source.pdf", "backup/source.pdf")

# 5. 安全文件名
safe_name = safe_filename("test/file:name.pdf")
print(safe_name)  # test_file_name.pdf

# 6. 生成唯一文件名
unique_name = generate_unique_filename("data/", "document.pdf")
print(unique_name)  # document.pdf 或 document_1.pdf
"""
