"""
========================================
RAG答案生成器
========================================

📚 模块说明：
- 整合检索和生成的完整RAG流程
- 支持多种生成策略
- 提供丰富的答案元数据

🎯 核心功能：
1. 检索增强生成
2. 上下文管理
3. 答案评估
4. 流式输出

========================================
"""

from typing import List, Dict, Optional, Generator, Union
from datetime import datetime

from loguru import logger

from services.llm.llm_client import LLMClient
from services.llm.prompt.qa_prompt import QAPromptFactory
from services.retrieval.hybrid_retriever import HybridRetriever


class AnswerGenerator:
    """
    RAG答案生成器

    🔧 核心流程：
    1. 接收用户问题
    2. 检索相关文档
    3. 构建Prompt
    4. LLM生成答案
    5. 返回结果和元数据

    💡 特性：
    - 自动上下文管理
    - 多轮对话支持
    - 答案质量评估
    - 引用追踪
    """

    def __init__(
            self,
            llm_client: LLMClient,
            retriever: HybridRetriever,
            language: str = 'zh',
            default_top_k: int = 5,
            max_context_length: int = 3000
    ):
        """
        初始化答案生成器

        参数：
            llm_client: LLM客户端
            retriever: 混合检索器
            language: 语言
            default_top_k: 默认检索数量
            max_context_length: 最大上下文长度
        """
        self.llm_client = llm_client
        self.retriever = retriever
        self.language = language
        self.default_top_k = default_top_k
        self.max_context_length = max_context_length

        logger.info(
            f"答案生成器初始化 | "
            f"语言: {language} | "
            f"top_k: {default_top_k}"
        )

    def generate(
            self,
            query: str,
            top_k: Optional[int] = None,
            use_rerank: bool = True,
            stream: bool = False,
            prompt_type: str = 'rag',
            include_sources: bool = True,
            **retrieval_kwargs
    ) -> Union[Dict, Generator[str, None, None]]:
        """
        生成答案

        参数：
            query: 用户问题
            top_k: 检索数量
            use_rerank: 是否使用重排序
            stream: 是否流式输出
            prompt_type: Prompt类型 ('rag', 'citation', 'explanation')
            include_sources: 是否包含来源信息
            **retrieval_kwargs: 传递给检索器的其他参数

        返回：
            - stream=False: 完整答案字典
                {
                    'answer': str,           # 答案文本
                    'sources': List[Dict],   # 来源文档
                    'query': str,            # 原始问题
                    'metadata': Dict         # 元数据
                }
            - stream=True: 文本生成器
        """
        logger.info(f"生成答案 | 问题: {query[:50]}... | 流式: {stream}")

        start_time = datetime.now()

        # Step 1: 检索相关文档
        if top_k is None:
            top_k = self.default_top_k

        logger.debug(f"检索文档 | top_k: {top_k}")

        retrieved_docs = self.retriever.search(
            query=query,
            top_k=top_k,
            use_rerank=use_rerank,
            **retrieval_kwargs
        )

        if not retrieved_docs:
            logger.warning("未检索到相关文档")
            return self._generate_no_context_answer(query, stream)

        logger.info(f"检索完成 | 文档数: {len(retrieved_docs)}")

        # Step 2: 构建Prompt
        prompt = QAPromptFactory.build_rag_prompt(
            query=query,
            contexts=[
                {
                    'text': doc.get('text', ''),
                    'metadata': {
                        'source': doc.get('doc_id', 'Unknown'),
                        'score': doc.get('rerank_score', doc.get('score', 0))
                    }
                }
                for doc in retrieved_docs
            ],
            language=self.language,
            max_context_length=self.max_context_length,
            include_metadata=include_sources
        )

        logger.debug(f"Prompt长度: {len(prompt)}")

        # Step 3: LLM生成答案
        if stream:
            # 流式输出（只返回文本生成器）
            return self.llm_client.generate(
                prompt=prompt,
                stream=True
            )
        else:
            # 非流式输出（返回完整结果）
            answer = self.llm_client.generate(
                prompt=prompt,
                stream=False
            )

            # Step 4: 构建响应
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()

            result = {
                'answer': answer,
                'query': query,
                'sources': retrieved_docs if include_sources else [],
                'metadata': {
                    'retrieved_docs': len(retrieved_docs),
                    'response_time': response_time,
                    'timestamp': end_time.isoformat(),
                    'model': self.llm_client.model,
                    'language': self.language,
                    'prompt_type': prompt_type,
                    'used_rerank': use_rerank
                }
            }

            logger.info(
                f"答案生成完成 | "
                f"耗时: {response_time:.2f}s | "
                f"答案长度: {len(answer)}"
            )

            return result

    def _generate_no_context_answer(
            self,
            query: str,
            stream: bool
    ) -> Union[Dict, Generator[str, None, None]]:
        """
        无上下文时的答案生成

        告知用户未找到相关信息
        """
        if self.language == 'zh':
            fallback_message = (
                f"抱歉，我在现有的知识库中没有找到与'{query}'直接相关的信息。\n\n"
                "建议：\n"
                "1. 尝试用不同的方式表述问题\n"
                "2. 检查问题中的专业术语是否准确\n"
                "3. 如果是特定规范或标准，请确认其已被收录到知识库中"
            )
        else:
            fallback_message = (
                f"Sorry, I couldn't find relevant information for '{query}' in the knowledge base.\n\n"
                "Suggestions:\n"
                "1. Try rephrasing your question\n"
                "2. Check if technical terms are accurate\n"
                "3. Ensure the specific regulation or standard is included in the knowledge base"
            )

        if stream:
            def fallback_generator():
                yield fallback_message

            return fallback_generator()
        else:
            return {
                'answer': fallback_message,
                'query': query,
                'sources': [],
                'metadata': {
                    'retrieved_docs': 0,
                    'no_context': True,
                    'timestamp': datetime.now().isoformat()
                }
            }

    def chat(
            self,
            query: str,
            conversation_history: Optional[List[Dict]] = None,
            top_k: Optional[int] = None,
            **kwargs
    ) -> Dict:
        """
        多轮对话生成

        参数：
            query: 当前问题
            conversation_history: 对话历史
                [
                    {"role": "user", "content": "问题1"},
                    {"role": "assistant", "content": "答案1"},
                    ...
                ]
            top_k: 检索数量
            **kwargs: 其他参数

        返回：
            答案字典
        """
        logger.info(f"多轮对话 | 历史轮数: {len(conversation_history or []) // 2}")

        # 检索相关文档
        if top_k is None:
            top_k = self.default_top_k

        retrieved_docs = self.retriever.search(
            query=query,
            top_k=top_k,
            **kwargs
        )

        # 构建上下文
        context = '\n\n'.join([
            f"【文档{i + 1}】\n{doc.get('text', '')}"
            for i, doc in enumerate(retrieved_docs)
        ])

        # 构建消息列表
        messages = []

        # 系统Prompt
        if self.language == 'zh':
            system_content = f"""你是一个专业的工程技术助手。请基于以下参考资料回答问题：

【参考资料】
{context}

回答要求：
1. 基于参考资料准确回答
2. 如果资料不足，明确说明
3. 保持回答简洁专业"""
        else:
            system_content = f"""You are a professional engineering assistant. Answer based on:

【References】
{context}

Requirements:
1. Answer accurately based on references
2. Clearly state if information insufficient
3. Keep answers concise and professional"""

        messages.append({
            "role": "system",
            "content": system_content
        })

        # 添加对话历史
        if conversation_history:
            messages.extend(conversation_history)

        # 添加当前问题
        messages.append({
            "role": "user",
            "content": query
        })

        # LLM生成
        answer = self.llm_client.chat(messages=messages)

        return {
            'answer': answer,
            'query': query,
            'sources': retrieved_docs,
            'conversation_history': messages,
            'metadata': {
                'retrieved_docs': len(retrieved_docs),
                'history_turns': len(conversation_history or []) // 2,
                'timestamp': datetime.now().isoformat()
            }
        }

    def evaluate_answer(self, result: Dict) -> Dict:
        """
        评估答案质量

        参数：
            result: generate()返回的结果

        返回：
            评估指标字典
        """
        answer = result.get('answer', '')
        sources = result.get('sources', [])

        # 简单的质量指标
        metrics = {
            'answer_length': len(answer),
            'has_sources': len(sources) > 0,
            'num_sources': len(sources),
            'avg_source_score': (
                sum(s.get('score', 0) for s in sources) / len(sources)
                if sources else 0
            ),
            'is_fallback': result.get('metadata', {}).get('no_context', False)
        }

        # 质量评分（0-1）
        quality_score = 0.0
        if metrics['has_sources']:
            quality_score += 0.3
        if metrics['answer_length'] > 50:
            quality_score += 0.3
        if metrics['avg_source_score'] > 0.7:
            quality_score += 0.4

        metrics['quality_score'] = quality_score

        return metrics


# =========================================
# 💡 使用示例
# =========================================
"""
from services.llm.generator import AnswerGenerator
from services.llm.llm_client import LLMClient
from services.retrieval.hybrid_retriever import HybridRetriever

# 1. 初始化组件
llm_client = LLMClient(
    api_base="http://localhost:8000/v1",
    model="qwen-plus"
)

hybrid_retriever = HybridRetriever(
    bm25_retriever=bm25,
    vector_retriever=vector,
    reranker=reranker
)

generator = AnswerGenerator(
    llm_client=llm_client,
    retriever=hybrid_retriever,
    language='zh'
)

# 2. 生成答案
result = generator.generate(
    query="建筑结构荷载如何计算？",
    top_k=5,
    use_rerank=True
)

print(f"问题: {result['query']}")
print(f"答案: {result['answer']}")
print(f"来源数: {len(result['sources'])}")
print(f"耗时: {result['metadata']['response_time']:.2f}s")


# 3. 流式输出
print("流式答案: ", end="", flush=True)
for chunk in generator.generate(
    query="什么是楼面活荷载？",
    stream=True
):
    print(chunk, end="", flush=True)
print()


# 4. 多轮对话
conversation = []

# 第一轮
result1 = generator.chat(
    query="什么是恒荷载？",
    conversation_history=conversation
)

conversation.extend([
    {"role": "user", "content": "什么是恒荷载？"},
    {"role": "assistant", "content": result1['answer']}
])

# 第二轮
result2 = generator.chat(
    query="它和活荷载有什么区别？",
    conversation_history=conversation
)

print(f"答案: {result2['answer']}")


# 5. 评估答案质量
metrics = generator.evaluate_answer(result)
print(f"答案质量: {metrics}")


# 6. 带引用的生成
result = generator.generate(
    query="办公室楼面荷载标准值是多少？",
    prompt_type='citation',
    include_sources=True
)
"""