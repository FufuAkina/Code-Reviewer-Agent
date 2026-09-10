"""Tool Registry测试"""
import pytest
from unittest.mock import MagicMock

from harness.tools.registry import ToolRegistry
from harness.tools.base import BaseTool
from harness.tools.result import ToolResult

class MockTool(BaseTool):
    """Mock工具(用于测试)
    
    关键: 必须实现BaseTool的所有抽象属性和方法
    """
    def __init__(self, name: str, should_fail: bool = False):
        self._name = name
        self._should_fail = should_fail
        
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return f"这是测试工具 {self._name}"
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "输入参数"
                }
            },
            "required": ["input"]
        }
        
    def execute(self, **kwargs) -> ToolResult:
        if self._should_fail:
            raise ValueError("故意抛出的错误")
        
        return ToolResult.ok(
            data=f"执行成功：{kwargs.get('input', '')}",
            tool_name=self.name
        )
            
@pytest.fixture
def registry():
    """创建ToolRegistry实例"""
    return ToolRegistry()

@pytest.fixture
def mock_tool():
    """创建Mock工具"""
    return MockTool(name="test_tool")

# ==== 测试1: 基本注册功能 ====
def test_registry_tool(registry, mock_tool):
    """测试注册工具"""
    registry.register(mock_tool)
    
    # 验证: 能够获取到工具
    assert registry.get("test_tool") == mock_tool
    assert "test_tool" in registry.list_tools()
    
# ==== 测试2: 重复注册应该失败 ====
def test_registry_duplicate_tool(registry, mock_tool):
    """测试重复注册工具
    
    - 防止覆盖已注册工具
    - “如果插件系统允许重复注册，会有什么安全风险？”
    """
    registry.register(mock_tool)
    
    # 验证: 重复注册则抛出 ValueError
    with pytest.raises(ValueError, match="工具 'test_tool' 已存在"):
        registry.register(mock_tool)
        
# ==== 测试3: 获取不存在的工具 ====
def test_get_nonexistent_tool(registry):
    """测试获取不存在的工具"""
    result = registry.get("不存在的工具")
    
    # 验证: 返回None(而不是抛出异常)
    assert result is None
    
# ==== 测试4: 执行成功场景 ====
def test_execute_tool_success(registry):
    """测试执行工具(成功)"""
    tool = MockTool(name="calc")
    registry.register(tool)
    
    # 执行工具
    result = registry.execute("calc", input="1+1")
    
    # 验证结果
    assert result.success is True
    assert "执行成功" in result.data
    assert result.tool_name == "calc"
    
# ==== 测试5：执行不存在的工具 ====
def test_execute_nonexistent_tool(registry):
    """测试执行不存在的工具
    
    为什么要测？
    - Agent可能调用错误的工具名（拼写错误）
    - 系统应该返回友好错误，而不是崩溃
    """
    result = registry.execute("不存在的工具")
    
    # 验证：返回错误结果
    assert result.success is False
    assert "不存在" in result.error
    assert result.retryable is False  # 不可重试


# ==== 测试6：工具执行抛异常 ====
def test_execute_tool_exception(registry):
    """测试工具执行时抛出异常
    
    为什么要测？
    - 工具代码可能有bug（除零错误、文件不存在等）
    - ToolRegistry应该捕获异常，返回ToolResult.error
    """
    tool = MockTool(name="buggy_tool", should_fail=True)
    registry.register(tool)
    
    # 执行会抛异常的工具
    result = registry.execute("buggy_tool", input="test")
    
    # 验证：异常被捕获，返回错误结果
    assert result.success is False
    assert "执行失败" in result.error
    assert "故意抛出的错误" in result.error


# ==== 测试7：转换为LLM格式 ====
def test_to_llm_format(registry):
    """测试转换为LLM Function Calling格式
    
    为什么要测？
    - 这是给LLM看的工具列表
    - 格式错误会导致LLM无法调用工具
    """
    tool1 = MockTool(name="tool1")
    tool2 = MockTool(name="tool2")
    registry.register(tool1)
    registry.register(tool2)
    
    llm_format = registry.to_llm_format()
    
    # 验证格式
    assert len(llm_format) == 2
    assert llm_format[0]["type"] == "function"
    assert llm_format[0]["function"]["name"] == "tool1"
    assert "description" in llm_format[0]["function"]
    assert "parameters" in llm_format[0]["function"]


# ==== 测试8：批量注册工具 ====
@pytest.mark.parametrize("tool_count", [1, 5, 10])
def test_register_multiple_tools(registry, tool_count):
    """测试批量注册工具
    
    parametrize的应用：测试1/5/10个工具的场景
    """
    tools = [MockTool(name=f"tool_{i}") for i in range(tool_count)]
    
    for tool in tools:
        registry.register(tool)
    
    # 验证：所有工具都注册成功
    assert len(registry.list_tools()) == tool_count
    assert len(registry.to_llm_format()) == tool_count