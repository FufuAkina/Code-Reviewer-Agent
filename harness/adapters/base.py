"""模型适配器基类"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict

@dataclass
class ModelResponse:
    """LLM 返回的统一响应格式
    
    作用: 屏蔽不同模型的返回格式差异
    """
    content: str            # LLM生成的内容
    finish_reason: str      # 结束原因: stop, length, tool_calls
    prompt_tokens: int      # 输入 token 数
    completion_tokens: int  # 输出 token 数
    model: str              # 使用的模型名称
    raw_response: Optional[dict] = None  # 原始响应(调试用)
    
    @property
    def total_tokens(self) -> int:
        """总 token 数"""
        return self.prompt_tokens + self.completion_tokens
    
class ModelAdapter(ABC):
    """模型适配器抽象基类
    
    所有LLM适配器都必须继承这个类，实现chat()方法
    """
    def __init__(self, api_key: str, base_url: str, model: str):
        """
        Args:
            api_key: API密钥
            base_url: API基础URL
            model: 模型名称
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 500
    ) -> ModelResponse:
        """调用LLM进行对话
        
        Args:
            messages: 对话历史 [{"role": "user", "content":"..."}]
            temperature: 温度参数
            max_tokens: 最大token数
            
        Return:
            ModelResponse: 统一响应格式
        """
        
# ==== 自定义异常 ====
class APIError(Exception):
    """API 调用基础错误"""
    pass

class AuthenticationError(APIError):
    """认证失败(401)"""
    pass

class RateLimiterError(APIError):
    """速率限制(429) - 可重试"""
    pass

class ServerError(APIError):
    """服务器错误(5xx) - 可重试"""
    pass