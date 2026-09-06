"""代码分析插件"""
import json
import re
from pathlib import Path
from typing import Dict, Any
from .base import ToolPlugin

class  AnalyzeCodePlugin(ToolPlugin):
    """分析 Python 代码质量"""
    @property
    def name(self) -> str:
        return "analyze_code"
    
    @property
    def description(self) -> str:
        return "分析Python代码质量，返回问题列表(包括:函数过长、缺少类型注释、缺少异常处理、缺少文档字符串)"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "file_path":{
                "type": "string",
                "description": "要分析的Python文件路径"
            }
        }
        
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "file_path": {
                "type": "string",
                "description": "要分析的Python文件路径"
            }
        }
        
    @property
    def required(self) -> list:
        return ["file_path"]
    
    def execute(self, file_path: str) -> str:
        """分析代码质量"""
        try:
            content = Path(file_path).read_text(encoding="utf-8")
            issues = []
            
            # 1.检查函数长度(超过50行、连续的函数)
            func_pattern = r'\s*def\s+(\w+)\s*\('
            lines = content.split("\n")
            
            func_starts = {}
            for i, line in enumerate(lines, 1):
                match = re.match(func_pattern, line)
                if match:
                    func_name = match.group(1)
                    func_starts[func_name] = i
                    
            # 简化版：智能检测连续的函数
            func_names = list(func_starts.keys()) #每个函数def所在的行位置
            for j in range(len(func_names) -1):
                func_name = func_names[j]
                start = func_starts[func_name]
                end = func_starts[func_names[j+1]]
                length = end - start
                
                if length > 50:
                    issues.append({
                        "lines": start,
                        "type": "函数过长",
                        "severity": "warning",
                        "detail": f"函数 {func_name} 有 {length} 行(建议＜50行)"
                    })
                        
            # 检查2: 缺少类型注解
            func_def_pattern =  r'def\s+(\w+)\s*\([^)]*\)\s*:'
            for match in re.finditer(func_def_pattern, content):
                func_def = match.group(0)
                func_name = match.group(1)
                
                if func_name.startswith("__"):
                    continue
                
                if "->" not in func_def:
                    line_num = content[:match.start()].count("\n") + 1
                    issues.append({
                        "line": line_num,
                        "type": "缺少返回类型注解",
                        "severity": "info",
                        "detail": f"函数 {func_name} 缺少返回类型注解(->)"
                    })
                    
            # 检查3：缺少异常处理
            has_risky_ops = any(keyword in content for keyword in ["open(", "josn.loads", "jons.load", "requests."])
            has_try_except = "try:" in content
            
            if has_risky_ops and not has_try_except:
                issues.append({
                    "line": 1,
                    "type": "缺少异常处理",
                    "severity": "error",
                    "detail": "代码包含可能抛出异常的操作(文件/网络/JSON)"
                })
                
            # 检查4： 缺少docstring
            for match in re.finditer(func_def_pattern, content):
                func_name = match.group(1)
                
                if func_name.startswith("__"):
                    continue
                
                after_def = content[match.end(): match.end() + 150]
                if '"""' not in after_def and "'''" not in after_def:
                    line_num = content[:match.start()].count("\n") + 1
                    issues.append({
                        "line": line_num,
                        "type": "缺少文档字符串",
                        "severity": "info",
                        "detail": f"函数{func_name}去烧docstring"
                    })
                    
            # 返回结果
            result = {
                "file": file_path,
                "total_issues": len(issues),
                "issues": issues[:15]
            }
            
            return json.dumps(result, indent=2, ensure_ascii=False)
        
        
        except Exception as e:
            return f"错误: {e}"
        
            