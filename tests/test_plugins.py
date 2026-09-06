"""测试插件系统"""

import pytest
from pathlib import Path
from plugins.read_file import ReadFilePlugin
from plugins.list_files import ListFilesPlugin
from plugins.analyze_code import AnalyzeCodePlugin

# 测试 1：插件基本属性
def test_read_file_plugin_properties():
    """测试 ReadFilePlugin 属性"""
    plugin = ReadFilePlugin()
    assert plugin.name == "read_file"
    assert plugin.description == "读取文件内容"
    assert "file_path" in plugin.parameters
    assert "file_path" in plugin.required

def test_list_files_plugin_properties():
    """测试 ListFilesPlugin 属性"""
    plugin = ListFilesPlugin()
    assert plugin.name == "list_files"
    assert plugin.description == "列出目录中的文件"
    assert "directory" in plugin.parameters
    assert len(plugin.required) == 0  # directory 是可选的

def test_analyze_code_plugin_properties():
    """测试 AnalyzeCodePlugin 属性"""
    plugin = AnalyzeCodePlugin()
    assert plugin.name == "analyze_code"
    assert "代码质量" in plugin.description
    assert "file_path" in plugin.parameters

# 测试 2：插件转换为字典
def test_plugin_to_dict():
    """测试插件转换为 Agent 工具格式"""
    plugin = ReadFilePlugin()
    tool_dict = plugin.to_dict()
    
    assert "function" in tool_dict
    assert "description" in tool_dict
    assert "parameters" in tool_dict
    assert "required" in tool_dict
    assert callable(tool_dict["function"])

# 测试 3：ReadFilePlugin 执行
def test_read_file_plugin_execute(tmp_path):
    """测试 ReadFilePlugin 执行"""
    # 创建临时文件
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!", encoding="utf-8")
    
    plugin = ReadFilePlugin()
    result = plugin.execute(file_path=str(test_file))
    
    assert "Hello, World!" in result

def test_read_file_plugin_error():
    """测试 ReadFilePlugin 错误处理"""
    plugin = ReadFilePlugin()
    result = plugin.execute(file_path="nonexistent_file.txt")
    
    assert "错误" in result

# 测试 4：ListFilesPlugin 执行
def test_list_files_plugin_execute(tmp_path):
    """测试 ListFilesPlugin 执行"""
    # 创建临时文件
    (tmp_path / "file1.txt").write_text("content1")
    (tmp_path / "file2.txt").write_text("content2")
    
    plugin = ListFilesPlugin()
    result = plugin.execute(directory=str(tmp_path))
    
    assert "file1.txt" in result
    assert "file2.txt" in result

# 测试 5：AnalyzeCodePlugin 执行
def test_analyze_code_plugin_execute(tmp_path):
    """测试 AnalyzeCodePlugin 执行"""
    # 创建测试 Python 文件
    test_file = tmp_path / "test.py"
    test_file.write_text("""
def long_function():
    pass
    
def no_type_annotation(x):
    return x + 1
""", encoding="utf-8")
    
    plugin = AnalyzeCodePlugin()
    result = plugin.execute(file_path=str(test_file))
    
    assert "total_issues" in result
    assert "issues" in result
