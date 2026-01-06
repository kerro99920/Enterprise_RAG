# =========================================
# HTTP状态码
# =========================================
class HTTPStatus:
    """
    常用HTTP状态码

    📡 状态码含义：
    - 2xx：成功
    - 4xx：客户端错误
    - 5xx：服务器错误
    """
    # 成功响应
    OK = 200  # 请求成功
    CREATED = 201  # 资源创建成功
    NO_CONTENT = 204  # 成功但无返回内容

    # 客户端错误
    BAD_REQUEST = 400  # 请求参数错误
    UNAUTHORIZED = 401  # 未登录
    FORBIDDEN = 403  # 无权限
    NOT_FOUND = 404  # 资源不存在
    CONFLICT = 409  # 资源冲突

    # 服务器错误
    INTERNAL_ERROR = 500  # 服务器内部错误
    SERVICE_UNAVAILABLE = 503  # 服务不可用


# =========================================
# 错误消息
# =========================================
class ErrorMessage:
    """
    标准错误消息

    💡 好处：
    - 统一错误提示
    - 方便国际化
    - 避免硬编码
    """
    # 认证相关
    INVALID_CREDENTIALS = "用户名或密码错误"
    TOKEN_EXPIRED = "登录已过期，请重新登录"
    INSUFFICIENT_PERMISSIONS = "权限不足，无法访问该资源"

    # 文档相关
    DOCUMENT_NOT_FOUND = "文档不存在或已被删除"
    DOCUMENT_ALREADY_EXISTS = "文档已存在，请勿重复上传"
    UNSUPPORTED_FILE_TYPE = "不支持的文件类型"
    FILE_TOO_LARGE = "文件大小超出限制"
    DOCUMENT_PROCESSING_FAILED = "文档处理失败，请稍后重试"

    # 查询相关
    INVALID_QUERY = "查询参数无效"
    NO_RESULTS_FOUND = "未找到相关结果"
    RETRIEVAL_FAILED = "检索失败，请稍后重试"

    # 系统相关
    DATABASE_ERROR = "数据库错误"
    VECTOR_DB_ERROR = "向量库错误"
    CACHE_ERROR = "缓存服务错误"
    INTERNAL_SERVER_ERROR = "服务器内部错误，请联系管理员"


# =========================================
# 成功消息
# =========================================
class SuccessMessage:
    """
    标准成功消息
    """
    DOCUMENT_UPLOADED = "文档上传成功"
    DOCUMENT_DELETED = "文档删除成功"
    DOCUMENT_UPDATED = "文档更新成功"
    QUERY_SUCCESS = "查询成功"
    LOGIN_SUCCESS = "登录成功"
    LOGOUT_SUCCESS = "登出成功"


# =========================================
# Redis缓存键前缀
# =========================================
class CacheKey:
    """
    Redis缓存键命名规范

    🔑 命名规则：
    - 使用冒号分隔层级
    - 使用有意义的前缀
    - 便于批量删除和管理

    示例：
        query:result:hash_value
        user:history:user_123
    """
    QUERY_RESULT = "query:result:"  # 查询结果缓存
    USER_SEARCH_HISTORY = "user:history:"  # 用户搜索历史
    USER_PERMISSIONS = "user:permissions:"  # 用户权限缓存
    HOT_QUERIES = "hot:queries"  # 热门查询统计
    DOCUMENT_METADATA = "doc:metadata:"  # 文档元数据缓存
    EMBEDDING_CACHE = "embedding:"  # Embedding向量缓存


# =========================================
# 日志事件类型
# =========================================
class LogEvent:
    """
    日志事件类型标识

    📝 用途：
    - 方便日志过滤和分析
    - 监控特定类型的事件
    """
    QUERY_START = "query_start"  # 查询开始
    QUERY_END = "query_end"  # 查询结束
    DOCUMENT_UPLOAD = "document_upload"  # 文档上传
    DOCUMENT_PROCESS = "document_process"  # 文档处理
    RETRIEVAL = "retrieval"  # 文档检索
    RERANK = "rerank"  # 重排序
    LLM_GENERATE = "llm_generate"  # LLM生成答案
    ERROR = "error"  # 错误事件
    WARNING = "warning"  # 警告事件
    INFO = "info"  # 信息事件


# =========================================
# 文件大小限制
# =========================================
class FileSizeLimit:
    """
    文件上传大小限制（单位：字节）

    💾 为什么要限制文件大小？
    - 避免占用过多内存
    - 防止恶意上传
    - 保证处理效率
    """
    PDF_MAX_SIZE = 50 * 1024 * 1024  # 50MB
    DOCX_MAX_SIZE = 20 * 1024 * 1024  # 20MB
    TXT_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    IMAGE_MAX_SIZE = 5 * 1024 * 1024  # 5MB


# =========================================
# 正则表达式模式
# =========================================
class RegexPattern:
    """
    常用正则表达式

    🔍 用途：
    - 验证输入格式
    - 提取特定信息
    """
    # 通用格式
    EMAIL = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    PHONE = r"^1[3-9]\d{9}$"  # 中国手机号
    URL = r"https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)"

    # 工程专业格式
    # 示例：GB 50009-2012、GB50009-2012
    STANDARD_CODE = r"[A-Z]{2,4}[\s\-]?\d{4,6}[\-\s]?\d{4}"

    # 项目编号示例：GC202401
    PROJECT_CODE = r"[A-Z]{2}\d{6}"


# =========================================
# Prompt模板类型
# =========================================
class PromptType(str, Enum):
    """
    Prompt模板类型

    🤖 不同类型的问题使用不同的Prompt模板：
    - QA_STANDARD：规范问答，要求严谨
    - QA_CONTRACT：合同问答，注意条款
    - QA_CASE：案例问答，提供参考
    """
    QA_BASIC = "qa_basic"  # 基础问答
    QA_WITH_CONTEXT = "qa_with_context"  # 带上下文问答
    QA_STANDARD = "qa_standard"  # 规范查询
    QA_CONTRACT = "qa_contract"  # 合同查询
    QA_CASE = "qa_case"  # 案例查询
    SUMMARY = "summary"  # 文档摘要
    COMPARISON = "comparison"  # 对比分析


# =========================================
# 系统配置常量
# =========================================
class SystemConfig:
    """
    系统级配置常量

    ⚙️ 这些是系统的硬编码限制，不建议修改
    """
    # 分页配置
    DEFAULT_PAGE_SIZE = 20  # 默认每页20条
    MAX_PAGE_SIZE = 100  # 最多每页100条

    # 查询限制
    MAX_QUERY_LENGTH = 500  # 查询最长500字符
    MIN_QUERY_LENGTH = 2  # 查询至少2字符

    # 重试配置
    MAX_RETRIES = 3  # 失败后最多重试3次
    RETRY_DELAY = 1  # 重试间隔1秒

    # 超时配置
    EMBEDDING_TIMEOUT = 30  # Embedding超时30秒
    LLM_TIMEOUT = 60  # LLM生成超时60秒
    RETRIEVAL_TIMEOUT = 10  # 检索超时10秒


# =========================================
# Milvus索引参数
# =========================================
class MilvusIndexParams:
    """
    Milvus向量索引参数配置

    🏗️ 索引类型选择指南：

    IVF_FLAT：
    - 适合：中等规模（百万级）
    - 优点：准确率高，内存占用适中
    - 缺点：速度中等

    IVF_SQ8：
    - 适合：大规模数据（千万级）
    - 优点：省内存（原来的1/4）
    - 缺点：略微降低精度

    HNSW：
    - 适合：对速度要求高的场景
    - 优点：速度快，精度高
    - 缺点：内存占用大
    """
    IVF_FLAT = {
        "index_type": "IVF_FLAT",
        "metric_type": "IP",  # 内积相似度
        "params": {"nlist": 1024}  # 聚类中心数量
    }

    IVF_SQ8 = {
        "index_type": "IVF_SQ8",
        "metric_type": "IP",
        "params": {"nlist": 1024}
    }

    HNSW = {
        "index_type": "HNSW",
        "metric_type": "IP",
        "params": {
            "M": 16,  # 连接数
            "efConstruction": 200  # 构建时的搜索深度
        }
    }


# =========================================
# 搜索参数
# =========================================
class SearchParams:
    """
    向量搜索参数

    📊 参数说明：
    - nprobe：搜索多少个聚类中心（越大越准确，越慢）
    - ef：HNSW搜索深度（越大越准确，越慢）
    """
    IVF_PARAMS = {"nprobe": 10}
    HNSW_PARAMS = {"ef": 64}


# =========================================
# 💡 使用示例
# =========================================
"""
# 1. 使用枚举
from core.constants import DocumentType, PermissionLevel

doc_type = DocumentType.STANDARD
if doc_type == DocumentType.STANDARD:
    print("这是规范文档")

# 2. 使用错误消息
from core.constants import ErrorMessage

raise ValueError(ErrorMessage.DOCUMENT_NOT_FOUND)

# 3. 使用缓存键
from core.constants import CacheKey

cache_key = f"{CacheKey.QUERY_RESULT}{query_hash}"
"""