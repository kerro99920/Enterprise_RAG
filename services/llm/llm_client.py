"""
========================================
LLM客户端
========================================

📚 模块说明：
- 统一的LLM API调用接口
- 支持多种LLM服务
- 错误重试和流式输出

🎯 支持的LLM：
1. OpenAI API兼容接口（GPT、Qwen、GLM等）
2. 本地模型（通过vLLM、Ollama等）
3. 自定义API

========================================
"""

import time
from typing import List, Dict, Optional, Generator, Union
import json

from openai import OpenAI
from loguru import logger


class LLMClient:
    """
    LLM客户端

    🔧 功能：
    - 统一API调用
    - 支持流式输出
    - 自动重试
    - 错误处理

    💡 兼容性：
    - OpenAI API
    - Azure OpenAI
    - 阿里云通义千问
    - 智谱GLM
    - 本地vLLM/Ollama
    """

    def __init__(
            self,
            api_base: str = "http://localhost:8000/v1",
            api_key: str = "EMPTY",
            model: str = "qwen-plus",
            temperature: float = 0.7,
            max_tokens: int = 2000,
            timeout: int = 60,
            max_retries: int = 3
    ):
        """
        初始化LLM客户端

        参数：
            api_base: API地址
            api_key: API密钥
            model: 模型名称
            temperature: 温度参数（0-2，越低越确定）
            max_tokens: 最大输出token数
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
        """
        self.api_base = api_base
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries

        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base,
            timeout=timeout
        )

        logger.info(
            f"LLM客户端初始化 | "
            f"模型: {model} | "
            f"API: {api_base}"
        )

    def chat(
            self,
            messages: List[Dict[str, str]],
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None,
            stream: bool = False,
            **kwargs
    ) -> Union[str, Generator[str, None, None]]:
        """
        对话补全

        参数：
            messages: 对话消息列表
                [
                    {"role": "system", "content": "系统提示"},
                    {"role": "user", "content": "用户消息"},
                    {"role": "assistant", "content": "助手回复"}
                ]
            temperature: 温度（覆盖默认值）
            max_tokens: 最大token（覆盖默认值）
            stream: 是否流式输出
            **kwargs: 其他API参数

        返回：
            - stream=False: 完整回复文本
            - stream=True: 文本生成器
        """
        # 使用默认值
        if temperature is None:
            temperature = self.temperature
        if max_tokens is None:
            max_tokens = self.max_tokens

        logger.debug(
            f"调用LLM | 模型: {self.model} | "
            f"消息数: {len(messages)} | "
            f"流式: {stream}"
        )

        # 带重试的API调用
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream,
                    **kwargs
                )

                if stream:
                    return self._stream_response(response)
                else:
                    content = response.choices[0].message.content
                    logger.debug(f"LLM响应长度: {len(content)}")
                    return content

            except Exception as e:
                logger.warning(
                    f"LLM调用失败 (尝试 {attempt + 1}/{self.max_retries}): {e}"
                )

                if attempt == self.max_retries - 1:
                    logger.error(f"LLM调用最终失败: {e}")
                    raise

                # 指数退避
                time.sleep(2 ** attempt)

    def _stream_response(
            self,
            response
    ) -> Generator[str, None, None]:
        """
        处理流式响应

        生成器，逐步yield文本片段
        """
        try:
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"流式响应处理失败: {e}")
            raise

    def generate(
            self,
            prompt: str,
            system_prompt: Optional[str] = None,
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None,
            stream: bool = False,
            **kwargs
    ) -> Union[str, Generator[str, None, None]]:
        """
        简化的生成接口

        参数：
            prompt: 用户提示
            system_prompt: 系统提示（可选）
            temperature: 温度
            max_tokens: 最大token
            stream: 是否流式
            **kwargs: 其他参数

        返回：
            生成的文本或文本生成器
        """
        # 构建消息
        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        messages.append({
            "role": "user",
            "content": prompt
        })

        return self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            **kwargs
        )

    def batch_generate(
            self,
            prompts: List[str],
            system_prompt: Optional[str] = None,
            **kwargs
    ) -> List[str]:
        """
        批量生成

        参数：
            prompts: 提示列表
            system_prompt: 系统提示
            **kwargs: 其他参数

        返回：
            生成结果列表
        """
        results = []

        logger.info(f"批量生成 | 数量: {len(prompts)}")

        for idx, prompt in enumerate(prompts, 1):
            logger.debug(f"生成 {idx}/{len(prompts)}")

            try:
                result = self.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    **kwargs
                )
                results.append(result)
            except Exception as e:
                logger.error(f"批量生成失败 ({idx}/{len(prompts)}): {e}")
                results.append("")  # 失败返回空字符串

        logger.info(f"批量生成完成 | 成功: {sum(1 for r in results if r)}/{len(prompts)}")

        return results

    def count_tokens(self, text: str) -> int:
        """
        估算token数量

        简单估算：中文1字≈1token，英文1词≈1.3token

        参数：
            text: 文本

        返回：
            估算的token数
        """
        import re

        # 统计中文字符
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))

        # 统计英文单词
        english_words = len(re.findall(r'[a-zA-Z]+', text))

        # 估算
        tokens = chinese_chars + int(english_words * 1.3)

        return tokens

    def get_model_info(self) -> Dict:
        """获取模型配置信息"""
        return {
            'model': self.model,
            'api_base': self.api_base,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'timeout': self.timeout
        }


# =========================================
# 💡 使用示例
# =========================================
"""
from services.llm.llm_client import LLMClient

# 1. 初始化客户端
client = LLMClient(
    api_base="http://localhost:8000/v1",
    api_key="your_api_key",
    model="qwen-plus",
    temperature=0.7,
    max_tokens=2000
)

# 2. 简单生成
response = client.generate(
    prompt="什么是建筑结构荷载？",
    system_prompt="你是一个专业的工程师。"
)
print(response)


# 3. 对话模式
messages = [
    {"role": "system", "content": "你是一个专业的建筑工程师。"},
    {"role": "user", "content": "什么是楼面荷载？"},
    {"role": "assistant", "content": "楼面荷载是指作用在楼板上的..."},
    {"role": "user", "content": "那活荷载呢？"}
]

response = client.chat(messages=messages)
print(response)


# 4. 流式输出
print("流式输出：", end="", flush=True)
for chunk in client.generate(
    prompt="请详细介绍建筑荷载规范",
    stream=True
):
    print(chunk, end="", flush=True)
print()


# 5. 批量生成
prompts = [
    "什么是恒荷载？",
    "什么是活荷载？",
    "什么是风荷载？"
]

results = client.batch_generate(
    prompts=prompts,
    system_prompt="你是工程师，简洁回答。"
)

for prompt, result in zip(prompts, results):
    print(f"Q: {prompt}")
    print(f"A: {result}\n")


# 6. Token计数
text = "建筑结构荷载规范GB50009-2012"
tokens = client.count_tokens(text)
print(f"Token数: {tokens}")


# 7. 查看配置
info = client.get_model_info()
print(f"模型配置: {info}")


# 8. 使用不同的LLM
# OpenAI GPT
openai_client = LLMClient(
    api_base="https://api.openai.com/v1",
    api_key="sk-xxx",
    model="gpt-4"
)

# 智谱GLM
glm_client = LLMClient(
    api_base="https://open.bigmodel.cn/api/paas/v4",
    api_key="your_glm_key",
    model="glm-4"
)

# 本地Ollama
ollama_client = LLMClient(
    api_base="http://localhost:11434/v1",
    api_key="ollama",
    model="qwen2:7b"
)
"""