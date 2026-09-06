"""列出文件插件"""
from pathlib import Path
from typing import Dict, Any
from .base import ToolPlugin

class ListFilesPlugin(ToolPlugin):
    """列出目录文件"""
    @property
    def name(self) -> str:
        return "list_files"
    
    @property
    def description(self) -> str:
        return "列出目录中的文件"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "directory": {
                "type": "string",
                "description": "目录路径，默认为当前目录"
            }
        }
        
    @property
    def required(self) -> list:
        return [] # directory是可选参数
    
    def execute(self, directory: str = ".") -> str:
        """列出目录文件"""
        try: 
            files = [f.name for f in Path(directory).iterdir() if f.is_file()]
            result = "\n".join(files[:20])
            if len(files) > 20:
                result += f"\n... 共{len(files)}个文件， 仅显示前20个"
            return result
        except Exception as e:
            return f"错误: {e}"
    