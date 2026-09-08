"""列出目录文件工具"""
from pathlib import Path
from typing import Dict, Any

from harness.tools.base import BaseTool
from harness.tools.result import ToolResult


class ListFilesTool(BaseTool):
    """列出目录中的文件"""

    @property
    def name(self) -> str:
        return "list_files"

    @property
    def description(self) -> str:
        return "列出指定目录中的所有文件和子目录"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "目录路径（默认为当前目录 '.'）"
                },
                "pattern": {
                    "type": "string",
                    "description": "文件名匹配模式（可选，如 '*.py'）"
                }
            },
            "required": ["directory"]
        }

    def execute(self, directory: str = ".", pattern: str = "*") -> ToolResult:
        """执行列出文件操作

        Args:
            directory: 目录路径
            pattern: 文件名匹配模式（支持 glob 通配符）

        Returns:
            ToolResult: 包含文件列表的结果
        """
        try:
            path = Path(directory)

            # 检查目录是否存在
            if not path.exists():
                return ToolResult.error(
                    error=f"目录不存在: {directory}",
                    tool_name=self.name,
                    retryable=False
                )

            # 检查是否是目录
            if not path.is_dir():
                return ToolResult.error(
                    error=f"路径不是目录: {directory}",
                    tool_name=self.name,
                    retryable=False
                )

            # 列出文件（使用 glob 匹配）
            files = []
            for item in sorted(path.glob(pattern)):
                # 标记文件类型
                if item.is_dir():
                    files.append(f"📁 {item.name}/")
                else:
                    # 获取文件大小
                    size = item.stat().st_size
                    size_str = self._format_size(size)
                    files.append(f"📄 {item.name} ({size_str})")

            if not files:
                return ToolResult.ok(
                    data=f"目录 '{directory}' 为空（或没有匹配 '{pattern}' 的文件）",
                    tool_name=self.name,
                    file_count=0
                )

            # 格式化输出
            result = f"目录 '{directory}' 中的文件：\n" + "\n".join(files)

            return ToolResult.ok(
                data=result,
                tool_name=self.name,
                file_count=len(files),
                directory=directory
            )

        except PermissionError:
            return ToolResult.error(
                error=f"没有权限访问目录: {directory}",
                tool_name=self.name,
                retryable=False
            )
        except Exception as e:
            return ToolResult.error(
                error=f"列出文件失败: {str(e)}",
                tool_name=self.name,
                retryable=True
            )

    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"
