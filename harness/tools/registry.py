"""工具注册表"""
from typing import Dict, List, Optional
from .base import BaseTool

class ToolRegistry:
    """工具注册表
    
    作用：
        1.注册工具
        2.获取工具
        3.生成工具列表(给LLM)
    """
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        
    def register(self, tool: BaseTool):
        """注册工具
        
        Args:
            tool: 工具实例
        """
        if tool.name in self._tools:
            raise ValueError(f"工具 '{tool.name}' 已存在")
        
        self._tools[tool.name] = tool
        
    def get(self, name: str) -> Optional[BaseTool]:
        """获取工具
        
        Args: 
            name: 工具名称
            
        Returns:
            工具实例，不存在时返回None
        """
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """列出所有工具名称"""
        return list(self._tools.keys())
    
    def to_llm_format(self) -> List[Dict]:
        """转换为LLM Function Calling 格式
        
        Returns:
            工具列表
        """
        return [tool.to_llm_format() for tool in self._tools.values()]
    
    def execute(self, name: str, **kwargs):
        """执行工具
        
        Args:
            name:工具名称
            **kwargs: 工具参数
            
        Returns:
            ToolResult
        """
        tool = self.get(name)
        if not tool:
            from .result import ToolResult
            return  ToolResult.error(
                error=f"工具 '{name}' 不存在， 可用工具: {self.list_tools()}",
                tool_name=name,
                retryable=False
            )
            
        try:
            return tool.execute(**kwargs)
        except Exception as e:
            from .result import ToolResult
            return ToolResult.error(
                error=f"执行失败: {str(e)}",
                tool_name=name,
                retryable=False
            )