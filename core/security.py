"""
========================================
安全工具模块
========================================

📚 模块说明：
- 加密解密工具
- 输入验证和清洗
- 安全令牌生成
- 文件安全检查

🎯 核心功能：
1. 密码加密和验证
2. 数据加密解密
3. 输入验证和过滤
4. XSS防护
5. SQL注入防护
6. 文件类型验证

========================================
"""

import re
import hashlib
import secrets
import string
from typing import Optional, List, Dict, Any
from pathlib import Path
import base64

from passlib.context import CryptContext
from loguru import logger

# =========================================
# 密码加密
# =========================================

# 密码加密上下文
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # 加密强度
)


def hash_password(password: str) -> str:
    """
    密码哈希

    使用bcrypt算法进行加密

    参数：
        password: 明文密码

    返回：
        哈希后的密码
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码

    参数：
        plain_password: 明文密码
        hashed_password: 哈希密码

    返回：
        是否匹配
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"密码验证失败: {e}")
        return False


def generate_password(
        length: int = 12,
        use_special_chars: bool = True
) -> str:
    """
    生成随机密码

    参数：
        length: 密码长度
        use_special_chars: 是否包含特殊字符

    返回：
        随机密码
    """
    chars = string.ascii_letters + string.digits
    if use_special_chars:
        chars += "!@#$%^&*"

    password = ''.join(secrets.choice(chars) for _ in range(length))
    return password


# =========================================
# 数据加密
# =========================================

def generate_secret_key(length: int = 32) -> str:
    """
    生成密钥

    用于JWT、加密等场景

    参数：
        length: 密钥长度（字节）

    返回：
        十六进制密钥字符串
    """
    return secrets.token_hex(length)


def generate_token(length: int = 32) -> str:
    """
    生成安全令牌

    用于API密钥、会话令牌等

    参数：
        length: 令牌长度

    返回：
        URL安全的令牌
    """
    return secrets.token_urlsafe(length)


def hash_data(data: str, algorithm: str = "sha256") -> str:
    """
    数据哈希

    参数：
        data: 待哈希的数据
        algorithm: 哈希算法 (md5, sha1, sha256, sha512)

    返回：
        哈希值（十六进制）
    """
    hash_func = getattr(hashlib, algorithm)
    return hash_func(data.encode()).hexdigest()


def encode_base64(data: str) -> str:
    """Base64编码"""
    return base64.b64encode(data.encode()).decode()


def decode_base64(encoded: str) -> str:
    """Base64解码"""
    try:
        return base64.b64decode(encoded.encode()).decode()
    except Exception as e:
        logger.error(f"Base64解码失败: {e}")
        return ""


# =========================================
# 输入验证
# =========================================

class InputValidator:
    """
    输入验证器

    防止注入攻击和恶意输入
    """

    # 危险字符模式
    SQL_INJECTION_PATTERN = re.compile(
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)|"
        r"(--|;|\/\*|\*\/|xp_|sp_)",
        re.IGNORECASE
    )

    XSS_PATTERN = re.compile(
        r"(<script|<iframe|<object|<embed|javascript:|onerror=|onload=)",
        re.IGNORECASE
    )

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """
        验证邮箱格式

        参数：
            email: 邮箱地址

        返回：
            是否有效
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def is_valid_username(username: str) -> bool:
        """
        验证用户名格式

        规则：
        - 3-20个字符
        - 只能包含字母、数字、下划线
        - 必须以字母开头

        参数：
            username: 用户名

        返回：
            是否有效
        """
        if not username or len(username) < 3 or len(username) > 20:
            return False

        pattern = r'^[a-zA-Z][a-zA-Z0-9_]{2,19}$'
        return bool(re.match(pattern, username))

    @staticmethod
    def is_valid_password(password: str) -> tuple[bool, str]:
        """
        验证密码强度

        规则：
        - 至少8个字符
        - 包含大写字母
        - 包含小写字母
        - 包含数字
        - 可选：包含特殊字符

        参数：
            password: 密码

        返回：
            (是否有效, 错误消息)
        """
        if len(password) < 8:
            return False, "密码至少8个字符"

        if not re.search(r'[A-Z]', password):
            return False, "密码必须包含大写字母"

        if not re.search(r'[a-z]', password):
            return False, "密码必须包含小写字母"

        if not re.search(r'\d', password):
            return False, "密码必须包含数字"

        return True, ""

    @staticmethod
    def check_sql_injection(text: str) -> bool:
        """
        检查SQL注入风险

        参数：
            text: 待检查的文本

        返回：
            True: 存在风险
            False: 安全
        """
        if not text:
            return False

        return bool(InputValidator.SQL_INJECTION_PATTERN.search(text))

    @staticmethod
    def check_xss(text: str) -> bool:
        """
        检查XSS攻击风险

        参数：
            text: 待检查的文本

        返回：
            True: 存在风险
            False: 安全
        """
        if not text:
            return False

        return bool(InputValidator.XSS_PATTERN.search(text))

    @staticmethod
    def sanitize_input(text: str) -> str:
        """
        清洗用户输入

        移除潜在危险字符

        参数：
            text: 原始输入

        返回：
            清洗后的文本
        """
        if not text:
            return ""

        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)

        # 移除特殊字符
        text = re.sub(r'[<>\'\"&]', '', text)

        # 移除多余空白
        text = ' '.join(text.split())

        return text.strip()


# =========================================
# 文件安全
# =========================================

class FileSecurityChecker:
    """
    文件安全检查器

    验证上传文件的安全性
    """

    # 允许的文件扩展名
    ALLOWED_EXTENSIONS = {
        'document': {'.pdf', '.docx', '.doc', '.txt', '.md'},
        'image': {'.jpg', '.jpeg', '.png', '.gif', '.bmp'},
        'archive': {'.zip', '.tar', '.gz', '.rar'}
    }

    # 危险文件扩展名
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.sh', '.ps1',
        '.dll', '.so', '.dylib',
        '.js', '.jar', '.apk'
    }

    # 最大文件大小（字节）
    MAX_FILE_SIZE = {
        'document': 50 * 1024 * 1024,  # 50MB
        'image': 10 * 1024 * 1024,  # 10MB
        'archive': 100 * 1024 * 1024  # 100MB
    }

    @staticmethod
    def is_allowed_extension(
            filename: str,
            category: str = 'document'
    ) -> bool:
        """
        检查文件扩展名是否允许

        参数：
            filename: 文件名
            category: 文件类别

        返回：
            是否允许
        """
        ext = Path(filename).suffix.lower()

        # 检查是否在危险列表
        if ext in FileSecurityChecker.DANGEROUS_EXTENSIONS:
            logger.warning(f"检测到危险文件类型: {ext}")
            return False

        # 检查是否在允许列表
        allowed = FileSecurityChecker.ALLOWED_EXTENSIONS.get(category, set())
        return ext in allowed

    @staticmethod
    def check_file_size(
            file_size: int,
            category: str = 'document'
    ) -> bool:
        """
        检查文件大小是否超限

        参数：
            file_size: 文件大小（字节）
            category: 文件类别

        返回：
            是否在限制内
        """
        max_size = FileSecurityChecker.MAX_FILE_SIZE.get(
            category,
            50 * 1024 * 1024
        )

        if file_size > max_size:
            logger.warning(
                f"文件过大: {file_size / 1024 / 1024:.2f}MB "
                f"(限制: {max_size / 1024 / 1024:.2f}MB)"
            )
            return False

        return True

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        清洗文件名

        移除危险字符，防止路径遍历

        参数：
            filename: 原始文件名

        返回：
            安全的文件名
        """
        # 只保留文件名部分（防止路径遍历）
        filename = Path(filename).name

        # 移除危险字符
        filename = re.sub(r'[^\w\s.-]', '', filename)

        # 移除开头的点（隐藏文件）
        filename = filename.lstrip('.')

        # 限制长度
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1)
            filename = name[:250] + '.' + ext

        return filename


# =========================================
# API安全
# =========================================

class RateLimiter:
    """
    简单的速率限制器

    防止API滥用
    """

    def __init__(self):
        self._requests = {}  # {identifier: [timestamp, ...]}

    def check_rate_limit(
            self,
            identifier: str,
            limit: int = 100,
            window: int = 3600
    ) -> tuple[bool, int]:
        """
        检查速率限制

        参数：
            identifier: 标识符（IP、用户ID等）
            limit: 时间窗口内的最大请求数
            window: 时间窗口（秒）

        返回：
            (是否允许, 剩余请求数)
        """
        import time

        now = time.time()

        # 清理过期记录
        if identifier in self._requests:
            self._requests[identifier] = [
                ts for ts in self._requests[identifier]
                if now - ts < window
            ]
        else:
            self._requests[identifier] = []

        # 检查是否超限
        current_count = len(self._requests[identifier])

        if current_count >= limit:
            return False, 0

        # 记录本次请求
        self._requests[identifier].append(now)

        remaining = limit - current_count - 1
        return True, remaining


# =========================================
# 💡 使用示例
# =========================================
"""
from core.security import (
    hash_password,
    verify_password,
    generate_token,
    InputValidator,
    FileSecurityChecker
)

# 1. 密码加密
password = "MyPassword123"
hashed = hash_password(password)
print(f"哈希密码: {hashed}")

# 验证密码
is_valid = verify_password(password, hashed)
print(f"密码正确: {is_valid}")


# 2. 生成令牌
api_key = generate_token(32)
print(f"API密钥: {api_key}")


# 3. 输入验证
validator = InputValidator()

# 验证邮箱
email = "user@example.com"
is_valid = validator.is_valid_email(email)
print(f"邮箱有效: {is_valid}")

# 验证密码强度
password = "Weak123"
is_valid, msg = validator.is_valid_password(password)
if not is_valid:
    print(f"密码不符合要求: {msg}")

# 检查SQL注入
user_input = "SELECT * FROM users; DROP TABLE users;"
if validator.check_sql_injection(user_input):
    print("检测到SQL注入风险！")

# 清洗输入
unsafe_input = "<script>alert('XSS')</script>Hello"
safe_input = validator.sanitize_input(unsafe_input)
print(f"清洗后: {safe_input}")


# 4. 文件安全检查
checker = FileSecurityChecker()

# 检查文件扩展名
filename = "document.pdf"
if checker.is_allowed_extension(filename, 'document'):
    print("文件类型允许")

# 检查文件大小
file_size = 5 * 1024 * 1024  # 5MB
if checker.check_file_size(file_size, 'document'):
    print("文件大小合格")

# 清洗文件名
unsafe_name = "../../../etc/passwd"
safe_name = checker.sanitize_filename(unsafe_name)
print(f"安全文件名: {safe_name}")


# 5. 速率限制
limiter = RateLimiter()

user_id = "user_123"
allowed, remaining = limiter.check_rate_limit(user_id, limit=10, window=60)

if allowed:
    print(f"请求通过，剩余 {remaining} 次")
else:
    print("请求过于频繁，请稍后再试")
"""