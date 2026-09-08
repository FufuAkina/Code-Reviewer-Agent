"""工具基类"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from .result import ToolResult

class BaseTool(ABC):
    """工具基类
    
    所有工具都必须继承这个类
    """
    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """功能描述"""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """参数定义(JSON Schema格式)"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """执行工具
        
        Args:
            **kwargs:动态参数
            
        Returns:
            ToolResult:  执行结果
        """
        pass
    
    def to_llm_format(self) -> Dict[str, Any]:
        """转换为 LLM Function Calling格式
        
        Returns:
            符合 OpenAI/DeepSeek 标准的工具定义
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }