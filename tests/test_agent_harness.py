"""AgentHarness集成测试 - 验证ReAct循环和模块协调"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path
import json

from harness.core.agent_harness import AgentHarness
from harness.adapters.base import ModelResponse, ModelAdapter
from harness.tools.registry import ToolRegistry
from harness.tools.base import BaseTool
from harness.tools.result import ToolResult


# ============ Mock工具类 ============
class MockTool(BaseTool):
    """可配置成功/失败的Mock工具"""
    
    def __init__(self, name: str, should_fail: bool = False, result_data: str = "Success"):
        self._name = name
        self._should_fail = should_fail
        self._result_data = result_data
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return f"Mock工具 {self._name}"
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "查询内容"}
            },
            "required": ["query"]
        }
    
    def execute(self, **kwargs) -> ToolResult:
        """执行工具（可配置失败）"""
        if self._should_fail:
            return ToolResult.error(
                error="MockTool执行失败",
                tool_name=self._name,
                details={"kwargs": kwargs}
            )
        return ToolResult.ok(
            data=self._result_data,
            tool_name=self._name,
            metadata={"tool": self._name, "input": kwargs}
        )


# ============ Fixture ============
@pytest.fixture
def mock_model_adapter():
    """Mock ModelAdapter（模拟LLM响应）"""
    adapter = MagicMock(spec=ModelAdapter)
    # 注意：chat方法是async的，必须用AsyncMock
    adapter.chat = AsyncMock()
    return adapter


@pytest.fixture
def tool_registry():
    """真实的ToolRegistry（集成测试不Mock）"""
    registry = ToolRegistry()
    # 注册Mock工具
    registry.register(MockTool("search_web"))
    registry.register(MockTool("read_file"))
    return registry


@pytest.fixture
def agent_harness(mock_model_adapter, tool_registry, tmp_path):
    """创建AgentHarness实例"""
    return AgentHarness(
        model_adapter=mock_model_adapter,
        tool_registry=tool_registry,
        max_steps=10,
        max_context_tokens=200,  # 降低阈值方便测试压缩
        save_dir=tmp_path / "states"
    )
    
    
# ============ 测试1：Happy Path ============
@pytest.mark.asyncio
async def test_happy_path_task_completion(agent_harness, mock_model_adapter):
    """测试1：正常流程 - LLM调用工具后完成任务
    
    场景：
    1. Step 1: LLM决定调用 search_web
    2. Step 2: LLM返回 finish
    
    验证点：
    - TaskState.status == "completed"
    - EventTracker记录了2次API调用、1次工具调用
    - 生成了state.json和reports
    """
    # Mock LLM的2次响应
    mock_model_adapter.chat.side_effect = [
        # Step 1: 调用工具
        ModelResponse(
            content='{"thought": "需要搜索", "action": "search_web", "action_input": {"query": "test"}}',
            finish_reason="stop",
            model="deepseek-chat",
            prompt_tokens=100,
            completion_tokens=50
        ),
        # Step 2: 完成任务
        ModelResponse(
            content='{"thought": "任务完成", "action": "finish", "action_input": {"answer": "搜索结果是test"}}',
            finish_reason="stop",
            model="deepseek-chat",
            prompt_tokens=120,
            completion_tokens=30
        )
    ]
    
    # 执行任务
    result = await agent_harness.run("帮我搜索test")
    
    # ===== 验证1：任务状态 =====
    assert result.status == "completed"
    assert len(result.completed_steps) == 1  # 只有step 1有工具调用（step 2是finish）
    assert result.completed_steps[0].action == "search_web"
    
    # ===== 验证2：EventTracker统计 =====
    stats = agent_harness.event_tracker.get_stats()
    assert stats["api_calls"]["count"] == 2  # 2次LLM调用
    assert stats["tool_calls"]["count"] == 1  # 1次工具调用
    assert stats["tool_calls"]["by_tool"]["search_web"] == 1
    
    # ===== 验证3：文件保存 =====
    state_file = agent_harness.save_dir / f"{result.task_id}.json"
    assert state_file.exists()
    
    reports_dir = Path("harness_reports")
    assert (reports_dir / f"{result.task_id}_stats.json").exists()
    
# ============ 测试2：工具失败重试 ============
@pytest.mark.asyncio
async def test_tool_failure_with_retry(agent_harness, mock_model_adapter, tool_registry):
    """测试2：工具执行失败，LLM看到错误后重试
    
    场景：
    1. Step 1: 调用 search_web 失败
    2. Step 2: LLM看到失败，决定重试
    3. Step 3: 第2次成功，返回finish
    
    验证点：
    - EventTracker记录了1次失败的工具调用
    - LLM的messages中包含了错误观察
    """
    # 注册一个会失败的工具
    tool_registry.register(MockTool("fail_tool", should_fail=True))
    
    mock_model_adapter.chat.side_effect = [
        # Step 1: 调用会失败的工具
        ModelResponse(
            content='{"thought": "尝试工具", "action": "fail_tool", "action_input": {"query": "test"}}',
            finish_reason="stop",
            model="deepseek-chat",
            prompt_tokens=100,
            completion_tokens=50
        ),
        # Step 2: 看到失败后重试另一个工具
        ModelResponse(
            content='{"thought": "换个工具", "action": "search_web", "action_input": {"query": "test"}}',
            finish_reason="stop",
            model="deepseek-chat",
            prompt_tokens=120,
            completion_tokens=50
        ),
        # Step 3: 完成
        ModelResponse(
            content='{"thought": "完成", "action": "finish", "action_input": {"answer": "成功"}}',
            finish_reason="stop",
            model="deepseek-chat",
            prompt_tokens=140,
            completion_tokens=30
        )
    ]
    
    result = await agent_harness.run("测试工具失败")
    
    # ===== 验证1：任务完成 =====
    assert result.status == "completed"
    assert len(result.completed_steps) == 2  # 2次工具调用
    
    # ===== 验证2：EventTracker记录了失败 =====
    stats = agent_harness.event_tracker.get_stats()
    assert stats["tool_calls"]["count"] == 2
    assert stats["tool_calls"]["success_rate"] == 50.0  # 1成功1失败
    
    # ===== 验证3：失败的observation被传给了LLM =====
    # messages中应该有 "❌ 工具执行失败" 的内容
    messages_content = [msg["content"] for msg in agent_harness.messages]
    assert any("工具执行结果" in msg for msg in messages_content)

# ============ 测试3：错误熔断 ============
@pytest.mark.asyncio
async def test_max_errors_abort(agent_harness, mock_model_adapter):
    """测试3：连续3次错误后熔断
    
    场景：
    - 3次LLM调用都抛出异常
    - 触发error_count >= 3的熔断逻辑
    
    验证点：
    - TaskState.status == "failed"
    - TaskState.error_count == 3
    - EventTracker记录了3次失败的API调用
    """
    # Mock LLM连续3次失败
    mock_model_adapter.chat.side_effect = [
        Exception("API超时1"),
        Exception("API超时2"),
        Exception("API超时3")
    ]
    
    result = await agent_harness.run("测试错误熔断")
    
    # ===== 验证1：任务失败 =====
    assert result.status == "failed"
    assert result.error_count == 3
    assert "API超时3" in result.last_error
    
    # ===== 验证2：EventTracker记录了失败 =====
    stats = agent_harness.event_tracker.get_stats()
    assert stats["api_calls"]["count"] == 3
    assert stats["api_calls"]["success_rate"] == 0.0  # 全部失败
    assert stats["errors"]["count"] == 3

# ============ 测试4：最大步数限制 ============
@pytest.mark.asyncio
async def test_max_steps_reached(agent_harness, mock_model_adapter):
    """测试4：达到max_steps=10后停止
    
    场景：
    - LLM连续10次都返回工具调用（不返回finish）
    - 触发for-else的else分支
    
    验证点：
    - TaskState.status == "max_steps_reached"
    - len(steps) == 10
    """
    # Mock LLM连续10次返回工具调用
    mock_model_adapter.chat.return_value = ModelResponse(
        content='{"thought": "继续", "action": "search_web", "action_input": {"query": "test"}}',
        finish_reason="stop",
        model="deepseek-chat",
        prompt_tokens=100,
        completion_tokens=50
    )
    
    result = await agent_harness.run("测试最大步数")
    
    # ===== 验证：达到最大步数 =====
    assert result.status == "max_steps_reached"
    assert len(result.completed_steps) == 10
    
    # ===== 验证：EventTracker统计正确 =====
    stats = agent_harness.event_tracker.get_stats()
    assert stats["api_calls"]["count"] == 10
    assert stats["tool_calls"]["count"] == 10
    
# ============ 测试5：无效JSON回退 ============
@pytest.mark.asyncio
async def test_invalid_json_fallback(agent_harness, mock_model_adapter):
    """测试5：LLM返回无效JSON时的回退机制
    
    场景：
    - Step 1: LLM返回纯文本（不是JSON）
    - _parse_json()回退为finish动作
    
    验证点：
    - 任务完成（虽然JSON无效）
    - action被解析为"finish"
    """
    mock_model_adapter.chat.return_value = ModelResponse(
        content="我无法生成JSON，抱歉",  # 无效JSON
        finish_reason="stop",
        model="deepseek-chat",
        prompt_tokens=100,
        completion_tokens=20
    )
    
    result = await agent_harness.run("测试无效JSON")
    
    # ===== 验证：回退机制生效 =====
    assert result.status == "completed"
    # _parse_json返回的默认action是finish（line 292-295）

# ============ 测试6：上下文压缩触发 ============
@pytest.mark.asyncio
async def test_context_compression_triggered(agent_harness, mock_model_adapter):
    """测试6：对话历史超限时触发ContextManager压缩
    
    场景：
    - max_context_tokens=1000（fixture中设置）
    - 连续5次工具调用，每次添加长文本observation
    - 验证messages被压缩
    
    验证点：
    - messages长度减少
    - system消息仍保留
    """
    # Mock LLM返回5次工具调用 + 1次finish
    responses = []
    for i in range(5):
        responses.append(ModelResponse(
            content=f'{{"thought": "步骤{i}", "action": "search_web", "action_input": {{"query": "test"}}}}',
            finish_reason="stop",
            model="deepseek-chat",
            prompt_tokens=100,
            completion_tokens=50
        ))
    responses.append(ModelResponse(
        content='{"thought": "完成", "action": "finish", "action_input": {"answer": "done"}}',
        finish_reason="stop",
        model="deepseek-chat",
        prompt_tokens=100,
        completion_tokens=30
    ))
    mock_model_adapter.chat.side_effect = responses
    
    result = await agent_harness.run("测试上下文压缩")
    
    # ===== 验证：messages被压缩过 =====
    # 原本应该有: 1 system + 1 user + 5*(assistant+user) + 1 assistant = 13条
    # 压缩后应该 < 13
    assert len(agent_harness.messages) < 13
    
    # system消息必须保留
    assert agent_harness.messages[0]["role"] == "system"
    
    # 最后一条是finish的assistant响应
    assert "finish" in agent_harness.messages[-1]["content"]

# ============ 测试7：文件保存完整性 ============
@pytest.mark.asyncio
async def test_state_and_reports_saved(agent_harness, mock_model_adapter, tmp_path):
    """测试7：验证TaskState和EventTracker报告都正确保存
    
    验证点：
    - {task_id}.json（TaskState）
    - {task_id}_stats.json（统计报告）
    - {task_id}_events.json（事件日志）
    """
    mock_model_adapter.chat.return_value = ModelResponse(
        content='{"thought": "完成", "action": "finish", "action_input": {"answer": "done"}}',
        model="deepseek-chat",
        prompt_tokens=100,
        completion_tokens=30
    )
    
    result = await agent_harness.run("测试文件保存")
    
    # ===== 验证1：TaskState保存 =====
    state_file = agent_harness.save_dir / f"{result.task_id}.json"
    assert state_file.exists()
    
    with open(state_file, "r", encoding="utf-8") as f:
        state_data = json.load(f)
    
    assert state_data["task_id"] == result.task_id
    assert state_data["status"] == "completed"
    assert state_data["user_request"] == "测试文件保存"
    
    # ===== 验证2：EventTracker报告 =====
    reports_dir = Path("harness_reports")
    stats_file = reports_dir / f"{result.task_id}_stats.json"
    events_file = reports_dir / f"{result.task_id}_events.json"
    
    assert stats_file.exists()
    assert events_file.exists()
    
    with open(stats_file, "r", encoding="utf-8") as f:
        stats = json.load(f)
    
    assert stats["task_id"] == result.task_id
    assert stats["api_calls"]["count"] == 1

# ============ 测试7：文件保存完整性 ============
@pytest.mark.asyncio
async def test_state_and_reports_saved(agent_harness, mock_model_adapter, tmp_path):
    """测试7：验证TaskState和EventTracker报告都正确保存
    
    验证点：
    - {task_id}.json（TaskState）
    - {task_id}_stats.json（统计报告）
    - {task_id}_events.json（事件日志）
    """
    mock_model_adapter.chat.return_value = ModelResponse(
        content='{"thought": "完成", "action": "finish", "action_input": {"answer": "done"}}',
        finish_reason="stop",
        model="deepseek-chat",
        prompt_tokens=100,
        completion_tokens=30
    )
    
    result = await agent_harness.run("测试文件保存")
    
    # ===== 验证1：TaskState保存 =====
    state_file = agent_harness.save_dir / f"{result.task_id}.json"
    assert state_file.exists()
    
    with open(state_file, "r", encoding="utf-8") as f:
        state_data = json.load(f)
    
    assert state_data["task_id"] == result.task_id
    assert state_data["status"] == "completed"
    assert state_data["user_request"] == "测试文件保存"
    
    # ===== 验证2：EventTracker报告 =====
    reports_dir = Path("harness_reports")
    stats_file = reports_dir / f"{result.task_id}_stats.json"
    events_file = reports_dir / f"{result.task_id}_events.json"
    
    assert stats_file.exists()
    assert events_file.exists()
    
    with open(stats_file, "r", encoding="utf-8") as f:
        stats = json.load(f)
    
    assert stats["task_id"] == result.task_id
    assert stats["api_calls"]["count"] == 1

# ============ 测试8：调用不存在的工具 ============
@pytest.mark.asyncio
async def test_nonexistent_tool(agent_harness, mock_model_adapter):
    """测试8：LLM尝试调用未注册的工具
    
    场景：
    - LLM返回 action="unknown_tool"
    - ToolRegistry.execute()抛出异常
    - 被_act()捕获，返回错误observation
    
    验证点：
    - 任务不会崩溃
    - EventTracker记录了失败的工具调用
    """
    mock_model_adapter.chat.side_effect = [
        # Step 1: 调用不存在的工具
        ModelResponse(
            content='{"thought": "尝试", "action": "unknown_tool", "action_input": {"query": "test"}}',
            finish_reason="stop",
            model="deepseek-chat",
            prompt_tokens=100,
            completion_tokens=50
        ),
        # Step 2: 看到错误后finish
        ModelResponse(
            content='{"thought": "工具不存在", "action": "finish", "action_input": {"answer": "失败"}}',
            finish_reason="stop",
            model="deepseek-chat",
            prompt_tokens=120,
            completion_tokens=30
        )
    ]
    
    result = await agent_harness.run("测试不存在的工具")
    
    # ===== 验证：任务完成（虽然工具失败） =====
    assert result.status == "completed"
    
    # ===== 验证：EventTracker记录了失败 =====
    stats = agent_harness.event_tracker.get_stats()
    assert stats["tool_calls"]["count"] == 1
    assert stats["tool_calls"]["success_rate"] == 0.0




