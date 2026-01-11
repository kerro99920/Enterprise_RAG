"""
========================================
基础Prompt模板系统
========================================

📚 模块说明：
- 提供Prompt模板基类
- 支持变量替换
- 统一Prompt管理

🎯 核心功能：
1. 模板定义和渲染
2. 变量验证
3. 多语言支持
4. Few-shot示例管理

========================================
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from string import Template
from loguru import logger


class BasePrompt(ABC):
    """
    Prompt模板基类

    🔧 设计原则：
    - 模板与逻辑分离
    - 支持变量替换
    - 可扩展和复用

    💡 使用方式：
    1. 继承此类
    2. 定义template属性
    3. 实现format()方法
    """

    def __init__(self, language: str = 'zh'):
        """
        初始化Prompt模板

        参数：
            language: 语言 ('zh', 'en')
        """
        self.language = language

    @property
    @abstractmethod
    def template(self) -> str:
        """
        Prompt模板字符串

        使用${variable}占位符
        """
        pass

    @property
    def required_variables(self) -> List[str]:
        """必需的变量列表"""
        return []

    @property
    def optional_variables(self) -> Dict[str, Any]:
        """可选变量及其默认值"""
        return {}

    def format(self, **kwargs) -> str:
        """
        格式化Prompt

        参数：
            **kwargs: 模板变量

        返回：
            格式化后的Prompt
        """
        # 验证必需变量
        missing = [v for v in self.required_variables if v not in kwargs]
        if missing:
            raise ValueError(f"缺少必需变量: {missing}")

        # 合并可选变量
        variables = self.optional_variables.copy()
        variables.update(kwargs)

        # 渲染模板
        try:
            prompt = Template(self.template).safe_substitute(variables)
            return prompt.strip()
        except Exception as e:
            logger.error(f"Prompt格式化失败: {e}")
            raise

    def __call__(self, **kwargs) -> str:
        """使Prompt对象可调用"""
        return self.format(**kwargs)


class SystemPrompt(BasePrompt):
    """
    系统Prompt模板

    用于定义AI助手的角色和行为准则
    """

    @property
    def template(self) -> str:
        if self.language == 'zh':
            return """你是一个专业的工程技术助手，专门帮助用户理解和应用工程规范、标准和技术文档。

你的职责：
1. 基于提供的参考资料准确回答问题
2. 引用具体的规范条文和数据
3. 给出清晰、专业的解释
4. 如果信息不足，诚实说明

回答要求：
- 准确性：严格基于参考资料，不编造信息
- 专业性：使用规范的工程术语
- 完整性：提供必要的背景和细节
- 可读性：条理清晰，易于理解

${additional_instructions}"""
        else:  # en
            return """You are a professional engineering assistant specializing in helping users understand and apply engineering standards, regulations, and technical documents.

Your responsibilities:
1. Answer questions accurately based on provided reference materials
2. Cite specific regulatory clauses and data
3. Provide clear, professional explanations
4. Honestly acknowledge when information is insufficient

Answer requirements:
- Accuracy: Strictly based on reference materials, no fabrication
- Professionalism: Use proper engineering terminology
- Completeness: Provide necessary background and details
- Readability: Clear structure, easy to understand

${additional_instructions}"""

    @property
    def optional_variables(self) -> Dict[str, Any]:
        return {
            'additional_instructions': ''
        }


class FewShotPrompt(BasePrompt):
    """
    Few-shot Prompt模板

    包含示例的Prompt，用于引导模型输出
    """

    def __init__(
            self,
            examples: List[Dict[str, str]],
            language: str = 'zh'
    ):
        """
        初始化Few-shot Prompt

        参数：
            examples: 示例列表
                [
                    {'input': '问题1', 'output': '答案1'},
                    {'input': '问题2', 'output': '答案2'}
                ]
            language: 语言
        """
        super().__init__(language)
        self.examples = examples

    @property
    def template(self) -> str:
        if self.language == 'zh':
            return """以下是一些示例：

${examples}

现在请回答：
${query}"""
        else:
            return """Here are some examples:

${examples}

Now please answer:
${query}"""

    @property
    def required_variables(self) -> List[str]:
        return ['query']

    def format(self, **kwargs) -> str:
        # 格式化示例
        if self.language == 'zh':
            examples_text = '\n\n'.join([
                f"问题：{ex['input']}\n答案：{ex['output']}"
                for ex in self.examples
            ])
        else:
            examples_text = '\n\n'.join([
                f"Question: {ex['input']}\nAnswer: {ex['output']}"
                for ex in self.examples
            ])

        kwargs['examples'] = examples_text
        return super().format(**kwargs)


class ChainOfThoughtPrompt(BasePrompt):
    """
    思维链（CoT）Prompt模板

    引导模型进行逐步推理
    """

    @property
    def template(self) -> str:
        if self.language == 'zh':
            return """请一步步分析并回答以下问题：

问题：${query}

请按以下步骤思考：
1. 理解问题的核心要点
2. 分析相关的背景知识
3. 逐步推导结论
4. 给出最终答案

${additional_guidance}"""
        else:
            return """Please analyze and answer the following question step by step:

Question: ${query}

Please think through these steps:
1. Understand the core points of the question
2. Analyze relevant background knowledge
3. Derive conclusions step by step
4. Provide the final answer

${additional_guidance}"""

    @property
    def required_variables(self) -> List[str]:
        return ['query']

    @property
    def optional_variables(self) -> Dict[str, Any]:
        return {
            'additional_guidance': ''
        }


class PromptBuilder:
    """
    Prompt构建器

    用于组合多个Prompt组件
    """

    def __init__(self, language: str = 'zh'):
        """
        初始化构建器

        参数：
            language: 语言
        """
        self.language = language
        self.components = []

    def add_system_prompt(
            self,
            additional_instructions: str = ''
    ) -> 'PromptBuilder':
        """添加系统Prompt"""
        system = SystemPrompt(self.language)
        self.components.append(
            system.format(additional_instructions=additional_instructions)
        )
        return self

    def add_context(
            self,
            context: str,
            context_label: str = '参考资料'
    ) -> 'PromptBuilder':
        """添加上下文"""
        if self.language == 'zh':
            self.components.append(f"{context_label}：\n{context}")
        else:
            self.components.append(f"Reference:\n{context}")
        return self

    def add_examples(
            self,
            examples: List[Dict[str, str]]
    ) -> 'PromptBuilder':
        """添加示例"""
        if self.language == 'zh':
            examples_text = '\n\n'.join([
                f"示例 {i + 1}：\n问题：{ex['input']}\n答案：{ex['output']}"
                for i, ex in enumerate(examples)
            ])
        else:
            examples_text = '\n\n'.join([
                f"Example {i + 1}:\nQuestion: {ex['input']}\nAnswer: {ex['output']}"
                for i, ex in enumerate(examples)
            ])

        self.components.append(examples_text)
        return self

    def add_query(
            self,
            query: str,
            query_label: str = '问题'
    ) -> 'PromptBuilder':
        """添加查询"""
        if self.language == 'zh':
            self.components.append(f"{query_label}：\n{query}")
        else:
            self.components.append(f"Question:\n{query}")
        return self

    def add_instructions(
            self,
            instructions: str
    ) -> 'PromptBuilder':
        """添加额外指令"""
        self.components.append(instructions)
        return self

    def build(self, separator: str = '\n\n') -> str:
        """
        构建最终Prompt

        参数：
            separator: 组件之间的分隔符

        返回：
            完整的Prompt
        """
        return separator.join(self.components)

    def clear(self) -> 'PromptBuilder':
        """清空组件"""
        self.components = []
        return self


# =========================================
# 💡 使用示例
# =========================================
"""
from services.llm.prompt.base_prompt import (
    SystemPrompt,
    FewShotPrompt,
    ChainOfThoughtPrompt,
    PromptBuilder
)

# 1. 使用系统Prompt
system = SystemPrompt(language='zh')
prompt = system.format(
    additional_instructions='特别注意引用规范条文编号。'
)
print(prompt)


# 2. 使用Few-shot Prompt
examples = [
    {
        'input': '混凝土强度等级是什么意思？',
        'output': '混凝土强度等级是指混凝土的抗压强度标准值，用fcu,k表示...'
    }
]

few_shot = FewShotPrompt(examples, language='zh')
prompt = few_shot.format(query='什么是钢筋保护层？')
print(prompt)


# 3. 使用思维链Prompt
cot = ChainOfThoughtPrompt(language='zh')
prompt = cot.format(
    query='如何计算梁的配筋？',
    additional_guidance='参考《混凝土结构设计规范》'
)
print(prompt)


# 4. 使用PromptBuilder组合
builder = PromptBuilder(language='zh')

prompt = (builder
    .add_system_prompt('你是建筑工程专家。')
    .add_context('GB50009-2012 建筑结构荷载规范...')
    .add_query('楼面活荷载如何取值？')
    .add_instructions('请引用具体条文编号。')
    .build()
)

print(prompt)


# 5. 自定义Prompt类
class CustomPrompt(BasePrompt):
    @property
    def template(self) -> str:
        return "自定义模板：${var1} ${var2}"

    @property
    def required_variables(self) -> List[str]:
        return ['var1', 'var2']

custom = CustomPrompt()
prompt = custom.format(var1='值1', var2='值2')
"""