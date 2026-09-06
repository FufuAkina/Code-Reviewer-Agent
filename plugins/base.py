"""插件基类"""
from abc import ABC, abstractmethod
from typing import Dict, Any

class ToolPlugin(ABC):
    """工具插件基类
    
    所有插件都必须继承这个类，并实现:
    - name: 工具名称
    - description: 功能描述
    - parameters: 参数定义
    - execute: 执行逻辑
    """
    
    @property
    @abstractmethod
    def description(self) -> str:
        """功能描述"""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """参数定义
        
        格式:
        {
            "param_name":{
                "type": "string",
                "description": "参数说明"
            }
        }
        """
        pass
    
    @property
    @abstractmethod
    def required(self) -> list:
        """必要参数列表"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> str:
        """执行工具逻辑
        
        Args:
            **kwargs: 动态参数
            
        Returns:
            执行结果(字符串)
        """
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为Agent需要的工具格式"""
        return {
            "function": self.execute,
            "description": self.description,
            "parameters": self.parameters,
            "required": self.required
        }