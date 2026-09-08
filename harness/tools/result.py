"""工具执行结果"""
from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class ToolResult:
    """工具执行结果
    
    作用: 统一工具返回格式, 并支持错误处理和重试
    """
    success: bool                # 是否成功
    data: any                    # 工具返回的数据
    error: Optional[str] = None  # 错误信息
    tool_name: str = ""          # 工具名称(方便日志)
    retryable: bool  = False     # 是否可以重试
    metadata: dict = None        # 元数据(执行时间、重试次数等)
    
    def __post_init__(self):
        """初始化后处理"""
        if self.metadata is None:
            self.metadata = {}
            
    @classmethod
    def ok(cls, data: Any, tool_name: str = "", **metadata) -> "ToolResult":
        """创建成功结果
        
        Args:
            data: 返回数据
            tool_name: 工具名称
            **metadata: 元数据
            
        Return:
            ToolResult: 成功结果
        """
        return cls(
            success=True,
            data=data,
            tool_name=tool_name,
            metadata=metadata
        )
        
    @classmethod
    def error(
        cls,
        error: str,
        tool_name: str = "",
        retryable: bool = False,
        **metadata
    ) -> "ToolResult":
        """创建错误结果
        
        Args:
            error:错误信息
            tool_name: 工具名称
            retryable: 是否可重试
            **metadata: 元数据
            
        Returns:
            ToolResult: 错误结果
        """
        return cls(
            success=False,
            data=None,
            error=error,
            tool_name=tool_name,
            retryable=retryable,
            metadata=metadata
        )
    
    # 添加一个专门处理超时错误的方法
    @classmethod
    def timeout(cls, tool_name: str, timeout_seconds: int = 30) -> "ToolResult":
        """创建超时错误"""
        return cls(
            success=False,
            data=None,
            error=f"执行超时（{timeout_seconds}秒）",
            tool_name=tool_name,
            retryable=True,  # 超时可重试
            metadata={"timeout": timeout_seconds}
        )

        
    def to_observation(self) -> str:
        """转换为观察结果（优化版）"""
        if self.success:
            if isinstance(self.data, str):
                return self.data
            elif isinstance(self.data, dict):
                # 格式化字典（更易读）
                import json
                return json.dumps(self.data, indent=2, ensure_ascii=False)
            elif isinstance(self.data, list):
                # 格式化列表
                return "\n".join(str(item) for item in self.data)
            else:
                return str(self.data)
        else:
            return f"❌ 错误: {self.error}"

     
    