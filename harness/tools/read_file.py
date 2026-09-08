"""读取文件工具"""
from pathlib import Path
from .base import BaseTool
from .result import ToolResult


class ReadFileTool(BaseTool):
    """读取文件内容"""
    
    @property
    def name(self) -> str:
        return "read_file"
    
    @property
    def description(self) -> str:
        return "读取文件内容"
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "文件路径"
                }
            },
            "required": ["file_path"]
        }
    
    def execute(self, file_path: str) -> ToolResult:
        """执行读取文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            ToolResult
        """
        try:
            path = Path(file_path)
            
            # 检查文件是否存在
            if not path.exists():
                return ToolResult.error(
                    error=f"文件不存在: {file_path}",
                    tool_name=self.name,
                    retryable=False
                )
            
            # 读取文件
            content = path.read_text(encoding="utf-8")
            
            return ToolResult.ok(
                data=content,
                tool_name=self.name,
                file_size=len(content)
            )
            
        except PermissionError:
            return ToolResult.error(
                error=f"没有权限读取文件: {file_path}",
                tool_name=self.name,
                retryable=False
            )
        except Exception as e:
            return ToolResult.error(
                error=f"读取失败: {str(e)}",
                tool_name=self.name,
                retryable=True  # 其他错误可能是临时的
            )
