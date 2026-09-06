"""读取文件插件"""
from pathlib import Path
from typing import Dict, Any
from .base import ToolPlugin

class ReadFilePlugin(ToolPlugin):
    """读取文件内容"""
    @property
    def name(self) -> str:
        return "read_file"
    
    @property
    def description(self) -> str:
        return "读取文件内容"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return{
            "file_path": {
                "type": "string",
                "description":  "文件路径(相对或绝对)"
            }
        }
        
    @property
    def required(self) -> list:
        return ["file_path"]
    
    def execute(self, file_path: str) -> str:
        """读取文件内容"""
        try:
            content = Path(file_path).read_text(encoding="utf-8")
            # 限制返回长度(防止超出上下文)
            return content[:2000] + ("..." if len(content) > 2000 else "")
        except Exception as e:
            return f"错误: {e}"