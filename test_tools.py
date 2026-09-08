from harness.tools.registry import ToolRegistry
from harness.tools.read_file import ReadFileTool

# 测试注册
registry = ToolRegistry()
registry.register(ReadFileTool())
print(f"✅ 已注册工具: {registry.list_tools()}")

# 测试执行（成功）
result = registry.execute("read_file", file_path="config.py")
print(f"✅ 执行结果: success={result.success}")

# 测试执行（失败）
result = registry.execute("read_file", file_path="not_exist.py")
print(f"✅ 错误信息: {result.error}")
