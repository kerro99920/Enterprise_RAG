"""
========================================
查询日志数据模型
========================================

📚 模块说明：
- 记录用户的查询历史
- 分析查询效果和用户行为
- 用于系统优化和改进

🎯 核心模型：
1. QueryLog - 查询日志主表
2. QueryFeedback - 查询反馈表

========================================
"""
from sqlalchemy import (
    Column, String, Integer, DateTime, Text,
    Float, JSON, ForeignKey, Boolean, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from core.constants import QueryType, AnswerQuality, RetrievalMode

# 使用与document.py相同的Base
from models.document import Base


# =========================================
# 1. 查询日志主表
# =========================================
class QueryLog(Base):
    """
    查询日志表

    📋 存储内容：
    - 用户的查询问题
    - 检索到的文档
    - 生成的答案
    - 性能指标（耗时、准确率等）

    💡 用途：
    - 分析用户搜索习惯
    - 评估系统性能
    - 发现热门查询
    - 改进检索策略
    """
    __tablename__ = "query_logs"

    # ===== 主键 =====
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="查询日志ID"
    )

    # ===== 用户信息 =====
    user_id = Column(
        String(36),
        nullable=True,
        index=True,
        comment="用户ID（如果用户已登录）"
    )

    session_id = Column(
        String(100),
        nullable=True,
        index=True,
        comment="会话ID（用于追踪同一次会话）"
    )

    # ===== 查询内容 =====
    query = Column(
        Text,
        nullable=False,
        comment="用户的查询问题"
    )

    query_type = Column(
        SQLEnum(QueryType),
        nullable=True,
        index=True,
        comment="查询类型：standard_query/contract_query/case_query等"
    )

    query_hash = Column(
        String(64),
        nullable=True,
        index=True,
        comment="查询内容的哈希值（用于查找相似查询）"
    )

    # ===== 检索配置 =====
    retrieval_mode = Column(
        SQLEnum(RetrievalMode),
        nullable=True,
        comment="检索模式：hybrid/vector_only/bm25_only"
    )

    collections_searched = Column(
        JSON,
        nullable=True,
        comment="搜索的向量库集合列表"
    )

    top_k = Column(
        Integer,
        nullable=True,
        comment="返回的Top-K文档数量"
    )

    # ===== 检索结果 =====
    retrieved_docs = Column(
        JSON,
        nullable=True,
        comment="检索到的文档列表（包含doc_id, score等）"
    )

    retrieved_count = Column(
        Integer,
        default=0,
        comment="检索到的文档数量"
    )

    # ===== 生成的答案 =====
    answer = Column(
        Text,
        nullable=True,
        comment="LLM生成的答案"
    )

    answer_sources = Column(
        JSON,
        nullable=True,
        comment="答案来源（引用的文档列表）"
    )

    # ===== 性能指标 =====
    retrieval_time = Column(
        Float,
        nullable=True,
        comment="检索耗时（秒）"
    )

    rerank_time = Column(
        Float,
        nullable=True,
        comment="重排序耗时（秒）"
    )

    generation_time = Column(
        Float,
        nullable=True,
        comment="答案生成耗时（秒）"
    )

    total_time = Column(
        Float,
        nullable=True,
        comment="总耗时（秒）"
    )

    # ===== 质量评估 =====
    answer_quality = Column(
        SQLEnum(AnswerQuality),
        nullable=True,
        comment="答案质量评分"
    )

    has_answer = Column(
        Boolean,
        default=True,
        comment="是否找到答案"
    )

    confidence_score = Column(
        Float,
        nullable=True,
        comment="置信度分数（0-1）"
    )

    # ===== 用户反馈 =====
    user_rating = Column(
        Integer,
        nullable=True,
        comment="用户评分（1-5星）"
    )

    is_helpful = Column(
        Boolean,
        nullable=True,
        comment="用户是否觉得有帮助"
    )

    # ===== 上下文信息 =====
    ip_address = Column(
        String(50),
        nullable=True,
        comment="用户IP地址"
    )

    user_agent = Column(
        String(500),
        nullable=True,
        comment="用户代理信息"
    )

    platform = Column(
        String(50),
        nullable=True,
        comment="访问平台（web/mobile/api）"
    )

    # ===== 错误信息 =====
    has_error = Column(
        Boolean,
        default=False,
        comment="是否发生错误"
    )

    error_message = Column(
        Text,
        nullable=True,
        comment="错误信息"
    )

    # ===== 额外数据 =====
    extra_data = Column(
        JSON,
        nullable=True,
        comment="额外的数据（JSON格式）"
    )

    # ===== 时间信息 =====
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
        comment="查询时间"
    )

    # ===== 关联关系 =====
    feedback = relationship(
        "QueryFeedback",
        back_populates="query_log",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<QueryLog(id={self.id}, query={self.query[:50]}...)>"

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "query": self.query,
            "query_type": self.query_type.value if self.query_type else None,
            "retrieval_mode": self.retrieval_mode.value if self.retrieval_mode else None,
            "retrieved_count": self.retrieved_count,
            "answer": self.answer,
            "retrieval_time": self.retrieval_time,
            "generation_time": self.generation_time,
            "total_time": self.total_time,
            "has_answer": self.has_answer,
            "confidence_score": self.confidence_score,
            "user_rating": self.user_rating,
            "is_helpful": self.is_helpful,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# =========================================
# 2. 查询反馈表
# =========================================
class QueryFeedback(Base):
    """
    查询反馈表

    📋 存储内容：
    - 用户对查询结果的反馈
    - 评分和评论
    - 改进建议

    💡 用途：
    - 收集用户反馈
    - 评估系统效果
    - 发现改进点
    """
    __tablename__ = "query_feedbacks"

    # ===== 主键 =====
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="反馈ID"
    )

    # ===== 外键：关联查询日志 =====
    query_log_id = Column(
        String(36),
        ForeignKey("query_logs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="查询日志ID"
    )

    # ===== 用户信息 =====
    user_id = Column(
        String(36),
        nullable=True,
        index=True,
        comment="用户ID"
    )

    # ===== 评分 =====
    rating = Column(
        Integer,
        nullable=False,
        comment="评分（1-5星）"
    )

    is_helpful = Column(
        Boolean,
        nullable=False,
        comment="是否有帮助"
    )

    is_accurate = Column(
        Boolean,
        nullable=True,
        comment="答案是否准确"
    )

    is_complete = Column(
        Boolean,
        nullable=True,
        comment="答案是否完整"
    )

    # ===== 反馈内容 =====
    comment = Column(
        Text,
        nullable=True,
        comment="用户评论"
    )

    suggestion = Column(
        Text,
        nullable=True,
        comment="改进建议"
    )

    # ===== 问题标记 =====
    has_hallucination = Column(
        Boolean,
        default=False,
        comment="是否存在幻觉（模型编造信息）"
    )

    is_irrelevant = Column(
        Boolean,
        default=False,
        comment="答案是否不相关"
    )

    is_incomplete = Column(
        Boolean,
        default=False,
        comment="答案是否不完整"
    )

    # ===== 标签 =====
    feedback_tags = Column(
        JSON,
        nullable=True,
        comment="反馈标签列表"
    )

    # ===== 时间信息 =====
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
        comment="反馈时间"
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="更新时间"
    )

    # ===== 关联关系 =====
    query_log = relationship("QueryLog", back_populates="feedback")

    def __repr__(self):
        return f"<QueryFeedback(id={self.id}, rating={self.rating}, helpful={self.is_helpful})>"

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "query_log_id": self.query_log_id,
            "rating": self.rating,
            "is_helpful": self.is_helpful,
            "is_accurate": self.is_accurate,
            "is_complete": self.is_complete,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# =========================================
# 💡 使用示例
# =========================================
"""
# 1. 记录查询日志
from models.query import QueryLog, QueryFeedback
from core.constants import QueryType, RetrievalMode

# 创建查询日志
query_log = QueryLog(
    user_id="user_123",
    query="防水规范的标准是什么？",
    query_type=QueryType.STANDARD_QUERY,
    retrieval_mode=RetrievalMode.HYBRID,
    collections_searched=["rag_standards"],
    retrieved_count=5,
    answer="根据GB 50009-2012规范...",
    retrieval_time=0.3,
    generation_time=1.2,
    total_time=1.5,
    has_answer=True
)

# 2. 添加用户反馈
feedback = QueryFeedback(
    query_log_id=query_log.id,
    user_id="user_123",
    rating=5,
    is_helpful=True,
    is_accurate=True,
    comment="答案非常准确，帮助很大！"
)

# 3. 保存到数据库
session.add(query_log)
session.add(feedback)
session.commit()


# 4. 查询统计
# 查询今天的查询数量
from sqlalchemy import func
today_count = session.query(func.count(QueryLog.id)).filter(
    func.date(QueryLog.created_at) == datetime.utcnow().date()
).scalar()

# 查询平均响应时间
avg_time = session.query(func.avg(QueryLog.total_time)).scalar()

# 查询用户满意度
satisfaction_rate = session.query(
    func.avg(QueryFeedback.rating)
).scalar()
"""