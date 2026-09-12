"""DeepSeek 模型适配器"""
import aiohttp
from typing import List, Dict

from .base import (
    ModelResponse, 
    ModelAdapter,
    APIError,
    AuthenticationError,
    RateLimiterError,
    ServerError
)

class DeepSeekAdapter(ModelAdapter):
    """DeepSeek API 适配器"""
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 2048
    ) -> ModelResponse:
        """调用DeepSeek API
        
        Args:
            messages: 对话历史
            temperature: 温度参数
            max_tokens: 最大token数
        
        Return:
            ModelResponse: 统一响应格式
            
        Raises:
            AuthenticationError: API Key无效
            RateLimitError: 请求过于频繁(可重试)
            ServerError: 服务器错误(可重试)
            APIError: 其他API错误
        """
        url = f"{self.base_url}/v1/chat/completions"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={
                    "Authorization":f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    
                    if resp.status == 401:
                        raise AuthenticationError(f"API Key 无效: {error_text}")
                    elif resp.status == 429:
                        raise RateLimiterError(f"请求过于频繁: {error_text}")
                    elif resp.status >= 500:
                        raise ServerError(f"服务器错误 {resp.status}: {error_text}")
                    else:
                        raise APIError(f"API 错误 {resp.status}: {error_text}")
                
                data = await resp.json()

                # 转换为统一格式
                return self._parse_response(data)

    def _parse_response(self, data: dict) -> ModelResponse:
        """解析 DeepSeek 返回的 JSON

        Args:
            data: API原始返回

        Returns:
            ModelResponse: 统一格式

        Raise:
            APIError: 返回格式不正确
        """
        # 验证必需字段
        if "choices" not in data or not data["choices"]:
            raise APIError(f"API 返回格式错误, 缺少 choices: {data}")

        if "usage" not in data:
            raise APIError(f"API 返回格式错误, 缺少 usage: {data}")

        choice = data["choices"][0]
        usage = data["usage"]

        # 验证嵌套字段
        if "message" not in choice or "content" not in choice["message"]:
            raise APIError(f"API 返回格式错误: message结构不正确: {choice}")

        return ModelResponse(
            content = choice["message"]["content"],
            finish_reason=choice.get("finish_reason", "unknown"),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            model=data.get("model", self.model),
            raw_response=data
        )