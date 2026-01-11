"""
========================================
问答API接口
========================================

📚 模块说明：
- RAG问答核心接口
- 支持单轮和多轮对话
- 流式和非流式输出

🎯 核心功能：
1. 单轮问答
2. 多轮对话
3. 流式输出
4. 答案评分

========================================
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime

from loguru import logger
from core.config import settings

# 这里需要导入你的服务组件
# from services.llm.generator import AnswerGenerator
# from services.llm.llm_client import LLMClient
# from services.retrieval.hybrid_retriever import HybridRetriever


router = APIRouter()


# =========================================
# 请求模型
# =========================================

class QuestionRequest(BaseModel):
    """单轮问答请求"""
    query: str = Field(..., description="用户问题", min_length=1, max_length=500)
    top_k: Optional[int] = Field(5, description="检索文档数量", ge=1, le=20)
    use_rerank: bool = Field(True, description="是否使用重排序")
    stream: bool = Field(False, description="是否流式输出")
    language: Optional[str] = Field("zh", description="回答语言")

    class Config:
        schema_extra = {
            "example": {
                "query": "建筑结构楼面活荷载如何取值？",
                "top_k": 5,
                "use_rerank": True,
                "stream": False,
                "language": "zh"
            }
        }


class Message(BaseModel):
    """对话消息"""
    role: str = Field(..., description="角色：user或assistant")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    """多轮对话请求"""
    query: str = Field(..., description="当前问题")
    history: Optional[List[Message]] = Field(default=[], description="对话历史")
    top_k: Optional[int] = Field(5, description="检索文档数量")
    use_rerank: bool = Field(True, description="是否使用重排序")

    class Config:
        schema_extra = {
            "example": {
                "query": "那活荷载呢？",
                "history": [
                    {"role": "user", "content": "什么是恒荷载？"},
                    {"role": "assistant", "content": "恒荷载是指在结构使用期间..."}
                ],
                "top_k": 5,
                "use_rerank": True
            }
        }


# =========================================
# 响应模型
# =========================================

class SourceDocument(BaseModel):
    """来源文档"""
    doc_id: str = Field(..., description="文档ID")
    text: str = Field(..., description="文档内容片段")
    score: float = Field(..., description="相关性分数")
    metadata: Optional[Dict] = Field(default={}, description="文档元数据")


class QuestionResponse(BaseModel):
    """问答响应"""
    success: bool = Field(True, description="是否成功")
    answer: str = Field(..., description="答案内容")
    query: str = Field(..., description="原始问题")
    sources: List[SourceDocument] = Field(default=[], description="来源文档")
    metadata: Dict = Field(default={}, description="元数据")
    timestamp: str = Field(..., description="响应时间戳")


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = Field(False, description="是否成功")
    message: str = Field(..., description="错误消息")
    error_code: Optional[str] = Field(None, description="错误码")


# =========================================
# 问答接口
# =========================================

@router.post(
    "/ask",
    response_model=QuestionResponse,
    summary="单轮问答",
    description="提交问题，获取基于知识库的答案"
)
async def ask_question(request: QuestionRequest):
    """
    单轮问答接口

    流程：
    1. 接收用户问题
    2. 检索相关文档
    3. 生成答案
    4. 返回结果
    """
    try:
        logger.info(f"收到问题: {request.query}")

        # 这里需要实例化你的生成器
        # generator = AnswerGenerator(llm_client, retriever)

        # 生成答案（示例）
        # result = generator.generate(
        #     query=request.query,
        #     top_k=request.top_k,
        #     use_rerank=request.use_rerank,
        #     stream=False
        # )

        # 临时示例响应（实际使用时删除）
        result = {
            "answer": f"这是对问题'{request.query}'的回答示例。\n\n根据检索到的相关文档，...",
            "query": request.query,
            "sources": [
                {
                    "doc_id": "doc_001",
                    "text": "相关文档内容片段...",
                    "score": 0.95,
                    "metadata": {"source": "GB50009-2012"}
                }
            ],
            "metadata": {
                "retrieved_docs": request.top_k,
                "response_time": 1.5,
                "model": "qwen-plus"
            }
        }

        # 构建响应
        response = QuestionResponse(
            success=True,
            answer=result["answer"],
            query=result["query"],
            sources=[
                SourceDocument(**src) for src in result.get("sources", [])
            ],
            metadata=result.get("metadata", {}),
            timestamp=datetime.now().isoformat()
        )

        logger.info(f"问答完成 | 答案长度: {len(result['answer'])}")

        return response

    except Exception as e:
        logger.error(f"问答失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"问答处理失败: {str(e)}"
        )


@router.post(
    "/ask/stream",
    summary="流式问答",
    description="流式返回答案，适合长文本生成"
)
async def ask_question_stream(request: QuestionRequest):
    """
    流式问答接口

    返回：
    Server-Sent Events (SSE) 流式响应
    """
    try:
        logger.info(f"收到流式问题: {request.query}")

        # 生成器函数
        async def generate():
            try:
                # 这里需要使用你的生成器
                # generator = AnswerGenerator(llm_client, retriever)
                # for chunk in generator.generate(
                #     query=request.query,
                #     stream=True
                # ):
                #     yield f"data: {chunk}\n\n"

                # 临时示例（实际使用时删除）
                example_text = f"这是对问题'{request.query}'的流式回答示例。"
                for char in example_text:
                    yield f"data: {char}\n\n"

                # 发送结束标记
                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error(f"流式生成失败: {e}")
                yield f"data: [ERROR] {str(e)}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )

    except Exception as e:
        logger.error(f"流式问答失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"流式问答失败: {str(e)}"
        )


@router.post(
    "/chat",
    response_model=QuestionResponse,
    summary="多轮对话",
    description="支持上下文的多轮对话问答"
)
async def chat(request: ChatRequest):
    """
    多轮对话接口

    支持：
    - 对话历史记忆
    - 上下文理解
    - 连续问答
    """
    try:
        logger.info(
            f"收到对话: {request.query} | "
            f"历史轮数: {len(request.history) // 2}"
        )

        # 转换历史格式
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.history
        ]

        # 生成答案（示例）
        # generator = AnswerGenerator(llm_client, retriever)
        # result = generator.chat(
        #     query=request.query,
        #     conversation_history=conversation_history,
        #     top_k=request.top_k
        # )

        # 临时示例响应
        result = {
            "answer": f"基于对话历史，对'{request.query}'的回答是...",
            "query": request.query,
            "sources": [],
            "metadata": {
                "history_turns": len(conversation_history) // 2
            }
        }

        response = QuestionResponse(
            success=True,
            answer=result["answer"],
            query=result["query"],
            sources=[],
            metadata=result.get("metadata", {}),
            timestamp=datetime.now().isoformat()
        )

        return response

    except Exception as e:
        logger.error(f"多轮对话失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"对话处理失败: {str(e)}"
        )


@router.get(
    "/feedback/{query_id}",
    summary="答案反馈",
    description="用户对答案进行评分反馈"
)
async def submit_feedback(
        query_id: str,
        rating: int = Field(..., description="评分 1-5", ge=1, le=5),
        comment: Optional[str] = Field(None, description="反馈评论")
):
    """
    答案反馈接口

    用于收集用户对答案的评价
    """
    try:
        logger.info(f"收到反馈 | query_id: {query_id} | rating: {rating}")

        # 这里应该保存反馈到数据库
        # await save_feedback(query_id, rating, comment)

        return {
            "success": True,
            "message": "感谢您的反馈",
            "query_id": query_id,
            "rating": rating
        }

    except Exception as e:
        logger.error(f"反馈提交失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="反馈提交失败"
        )


# =========================================
# 💡 使用示例
# =========================================
"""
# 1. 单轮问答
curl -X POST "http://localhost:8000/api/v1/qa/ask" \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "建筑结构楼面活荷载如何取值？",
    "top_k": 5,
    "use_rerank": true,
    "stream": false
  }'


# 2. 流式问答
curl -X POST "http://localhost:8000/api/v1/qa/ask/stream" \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "什么是楼面活荷载？",
    "stream": true
  }'


# 3. 多轮对话
curl -X POST "http://localhost:8000/api/v1/qa/chat" \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "那活荷载呢？",
    "history": [
      {"role": "user", "content": "什么是恒荷载？"},
      {"role": "assistant", "content": "恒荷载是..."}
    ]
  }'


# 4. Python客户端示例
import requests

# 单轮问答
response = requests.post(
    "http://localhost:8000/api/v1/qa/ask",
    json={
        "query": "建筑结构楼面活荷载如何取值？",
        "top_k": 5,
        "use_rerank": True
    }
)

result = response.json()
print(f"答案: {result['answer']}")
print(f"来源数: {len(result['sources'])}")


# 流式问答
import requests

response = requests.post(
    "http://localhost:8000/api/v1/qa/ask/stream",
    json={"query": "什么是建筑荷载？"},
    stream=True
)

for line in response.iter_lines():
    if line:
        text = line.decode('utf-8')
        if text.startswith('data: '):
            chunk = text[6:]  # 去掉 'data: ' 前缀
            if chunk != '[DONE]':
                print(chunk, end='', flush=True)
"""