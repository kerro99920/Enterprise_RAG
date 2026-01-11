"""
========================================
问答系统Prompt模板
========================================

📚 模块说明：
- RAG问答专用Prompt
- 优化的检索增强生成策略
- 支持多种问答场景

🎯 核心功能：
1. 标准RAG问答
2. 引用式回答
3. 对比分析
4. 规范解读

========================================
"""

from typing import List, Dict, Optional
from services.llm.prompt.base_prompt import BasePrompt, PromptBuilder


class RAGPrompt(BasePrompt):
    """
    RAG（检索增强生成）问答Prompt

    专为基于检索内容的问答设计
    """

    @property
    def template(self) -> str:
        if self.language == 'zh':
            return """你是一个专业的工程技术助手，请基于以下参考资料回答用户问题。

【参考资料】
${context}

【回答要求】
1. 必须基于上述参考资料回答，不要编造信息
2. 如果参考资料中没有相关信息，请明确说明
3. 引用具体内容时，请标注来源（如文档名、章节号）
4. 回答要准确、专业、易懂
5. 如有必要，可以适当补充相关背景知识

【用户问题】
${query}

【你的回答】"""
        else:  # en
            return """You are a professional engineering assistant. Please answer user questions based on the following reference materials.

【Reference Materials】
${context}

【Answer Requirements】
1. Must base answer on the above reference materials, do not fabricate
2. If no relevant information in references, clearly state so
3. When citing content, indicate source (document name, section number)
4. Answer should be accurate, professional, and understandable
5. Can supplement relevant background knowledge if necessary

【User Question】
${query}

【Your Answer】"""

    @property
    def required_variables(self) -> List[str]:
        return ['context', 'query']


class CitationPrompt(BasePrompt):
    """
    引用式回答Prompt

    要求模型在回答中明确标注引用来源
    """

    @property
    def template(self) -> str:
        if self.language == 'zh':
            return """请基于以下参考文档回答问题，并在引用时标注来源。

【参考文档】
${context}

【回答格式】
请使用以下格式标注引用：
- 直接引用：根据《文档名》第X章第Y节："原文内容"
- 间接引用：参考《文档名》相关内容，...

【用户问题】
${query}

【回答】
请逐点回答，并明确标注每个要点的出处："""
        else:
            return """Please answer based on the following reference documents and cite sources.

【Reference Documents】
${context}

【Answer Format】
Use the following format for citations:
- Direct quote: According to "Document Name" Chapter X Section Y: "original text"
- Indirect reference: Referring to "Document Name", ...

【User Question】
${query}

【Answer】
Please answer point by point and clearly cite sources for each point:"""

    @property
    def required_variables(self) -> List[str]:
        return ['context', 'query']


class ComparisonPrompt(BasePrompt):
    """
    对比分析Prompt

    用于对比不同规范、标准或方法
    """

    @property
    def template(self) -> str:
        if self.language == 'zh':
            return """请基于以下参考资料，对比分析${comparison_target}。

【参考资料】
${context}

【对比维度】
${comparison_aspects}

【用户问题】
${query}

【对比分析】
请从以上维度进行对比，并总结主要差异："""
        else:
            return """Please compare and analyze ${comparison_target} based on the following references.

【References】
${context}

【Comparison Aspects】
${comparison_aspects}

【User Question】
${query}

【Comparative Analysis】
Please compare from the above aspects and summarize key differences:"""

    @property
    def required_variables(self) -> List[str]:
        return ['context', 'query', 'comparison_target']

    @property
    def optional_variables(self) -> Dict:
        return {
            'comparison_aspects': '适用范围、技术指标、计算方法、注意事项'
        }


class ExplanationPrompt(BasePrompt):
    """
    规范解读Prompt

    用于详细解释规范条文
    """

    @property
    def template(self) -> str:
        if self.language == 'zh':
            return """请详细解读以下规范条文，帮助用户理解其含义和应用。

【规范条文】
${context}

【解读要求】
1. 条文背景：说明该条文的制定背景和目的
2. 关键术语：解释条文中的专业术语
3. 适用场景：说明该条文的适用范围
4. 计算方法：如涉及计算，给出公式和示例
5. 注意事项：提醒实际应用中的要点

【用户问题】
${query}

【详细解读】"""
        else:
            return """Please provide a detailed explanation of the following regulatory clause.

【Regulatory Clause】
${context}

【Explanation Requirements】
1. Background: Explain background and purpose
2. Key Terms: Define technical terminology
3. Applicable Scenarios: Describe scope of application
4. Calculation Methods: Provide formulas and examples if applicable
5. Important Notes: Highlight key points for practical application

【User Question】
${query}

【Detailed Explanation】"""

    @property
    def required_variables(self) -> List[str]:
        return ['context', 'query']


class QAPromptFactory:
    """
    问答Prompt工厂

    根据场景选择合适的Prompt模板
    """

    @staticmethod
    def create_prompt(
            prompt_type: str,
            language: str = 'zh'
    ) -> BasePrompt:
        """
        创建Prompt实例

        参数：
            prompt_type: Prompt类型
                - 'rag': 标准RAG问答
                - 'citation': 引用式回答
                - 'comparison': 对比分析
                - 'explanation': 规范解读
            language: 语言

        返回：
            Prompt实例
        """
        prompt_map = {
            'rag': RAGPrompt,
            'citation': CitationPrompt,
            'comparison': ComparisonPrompt,
            'explanation': ExplanationPrompt
        }

        if prompt_type not in prompt_map:
            raise ValueError(
                f"不支持的Prompt类型: {prompt_type}. "
                f"可选: {list(prompt_map.keys())}"
            )

        return prompt_map[prompt_type](language=language)

    @staticmethod
    def build_rag_prompt(
            query: str,
            contexts: List[Dict],
            language: str = 'zh',
            max_context_length: int = 3000,
            include_metadata: bool = True
    ) -> str:
        """
        构建RAG问答Prompt

        参数：
            query: 用户问题
            contexts: 检索到的上下文列表
                [
                    {
                        'text': '内容',
                        'metadata': {'source': '来源', 'score': 0.9}
                    },
                    ...
                ]
            language: 语言
            max_context_length: 上下文最大长度
            include_metadata: 是否包含元数据

        返回：
            完整的Prompt
        """
        # 格式化上下文
        context_parts = []
        current_length = 0

        for idx, ctx in enumerate(contexts, 1):
            text = ctx.get('text', '')
            metadata = ctx.get('metadata', {})

            # 检查长度
            if current_length + len(text) > max_context_length:
                break

            # 格式化单个上下文
            if language == 'zh':
                if include_metadata:
                    source = metadata.get('source', f'文档{idx}')
                    score = metadata.get('score', 0)
                    context_part = f"【来源{idx}：{source} | 相关度：{score:.2f}】\n{text}"
                else:
                    context_part = f"【片段{idx}】\n{text}"
            else:
                if include_metadata:
                    source = metadata.get('source', f'Document{idx}')
                    score = metadata.get('score', 0)
                    context_part = f"【Source{idx}: {source} | Relevance: {score:.2f}】\n{text}"
                else:
                    context_part = f"【Snippet{idx}】\n{text}"

            context_parts.append(context_part)
            current_length += len(text)

        # 组合上下文
        context = '\n\n'.join(context_parts)

        # 创建Prompt
        prompt = RAGPrompt(language=language)
        return prompt.format(context=context, query=query)


# =========================================
# 💡 使用示例
# =========================================
"""
from services.llm.prompt.qa_prompt import (
    RAGPrompt,
    CitationPrompt,
    QAPromptFactory
)

# 1. 使用RAG Prompt
rag_prompt = RAGPrompt(language='zh')

context = '''
GB50009-2012 建筑结构荷载规范
第4.1.1条：民用建筑楼面均布活荷载的标准值及其组合值、
频遇值和准永久值系数，应按表4.1.1采用。
'''

query = "办公室楼面活荷载标准值是多少？"

prompt = rag_prompt.format(context=context, query=query)
print(prompt)


# 2. 使用引用式Prompt
citation_prompt = CitationPrompt(language='zh')
prompt = citation_prompt.format(context=context, query=query)


# 3. 使用Prompt工厂
prompt = QAPromptFactory.create_prompt('rag', language='zh')


# 4. 构建完整的RAG Prompt（推荐）
contexts = [
    {
        'text': 'GB50009-2012规定，办公室楼面活荷载标准值为2.0kN/m²',
        'metadata': {
            'source': 'GB50009-2012',
            'score': 0.95,
            'doc_id': 'doc_001'
        }
    },
    {
        'text': '对于重要办公室，活荷载可适当提高',
        'metadata': {
            'source': 'GB50009-2012条文说明',
            'score': 0.82,
            'doc_id': 'doc_002'
        }
    }
]

query = "办公室楼面活荷载如何取值？"

final_prompt = QAPromptFactory.build_rag_prompt(
    query=query,
    contexts=contexts,
    language='zh',
    max_context_length=3000,
    include_metadata=True
)

print(final_prompt)


# 5. 对比分析Prompt
comparison = ComparisonPrompt(language='zh')
prompt = comparison.format(
    context='新旧规范内容...',
    query='GB50009-2012与GB50009-2001有何差异？',
    comparison_target='新旧荷载规范',
    comparison_aspects='荷载分类、取值方法、组合原则'
)
"""