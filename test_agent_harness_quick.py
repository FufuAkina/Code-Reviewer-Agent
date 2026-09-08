import asyncio
import os
from pathlib import Path

from harness.core.agent_harness import AgentHarness
from harness.adapters.deepseek import DeepSeekAdapter
from harness.tools.registry import ToolRegistry
from harness.tools.read_file import ReadFileTool
from harness.tools.list_files import ListFilesTool


async def test_agent_harness():
    # 1. 初始化组件
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 请设置环境变量 DEEPSEEK_API_KEY")
        return
    
    model_adapter = DeepSeekAdapter(
        api_key=api_key,
        base_url="https://api.deepseek.com",
        model="deepseek-chat"
    )
    
    tool_registry = ToolRegistry()
    tool_registry.register(ReadFileTool())
    tool_registry.register(ListFilesTool())
    
    # 2. 创建 AgentHarness
    harness = AgentHarness(
        model_adapter=model_adapter,
        tool_registry=tool_registry,
        max_steps=5
    )
    
    # 3. 运行任务
    result = await harness.run("列出当前目录的文件")
    
    # 4. 查看结果
    print(f"\n{'='*60}")
    print(f"📋 任务状态: {result.status}")
    print(f"📊 总步数: {result.current_step}")
    print(f"❌ 错误数: {result.error_count}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(test_agent_harness())
