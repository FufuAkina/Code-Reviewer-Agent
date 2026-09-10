"""EventTracker测试"""
import pytest
from pathlib import Path
import json

from harness.core.event_tracker import EventTracker, Event


# ============ Fixture ============
@pytest.fixture
def tracker():
    """创建EventTracker实例"""
    return EventTracker(task_id="test_task_123")


# ============ 模块1：基本事件记录 ============

def test_log_api_call(tracker):
    """测试1：记录API调用"""
    tracker.log_api_call(
        model="deepseek-chat",
        prompt_tokens=100,
        completion_tokens=50,
        duration=1.5,
        success=True
    )

    assert len(tracker.events) == 1

    event = tracker.events[0]
    assert event.event_type == "api_call"
    assert event.data["model"] == "deepseek-chat"
    assert event.data["total_tokens"] == 150
    assert event.data["duration_ms"] == 1500.0
    assert event.data["success"] is True


def test_log_tool_call(tracker):
    """测试2：记录工具调用"""
    tracker.log_tool_call(
        tool_name="read_file",
        success=True,
        duration=0.5,
        file_path="/tmp/test.txt"  # 额外的metadata
    )

    assert len(tracker.events) == 1

    event = tracker.events[0]
    assert event.event_type == "tool_call"
    assert event.data["tool_name"] == "read_file"
    assert event.data["duration_ms"] == 500.0
    assert event.data["file_path"] == "/tmp/test.txt"  # 验证**kwargs被记录


def test_log_error(tracker):
    """测试3：记录错误"""
    tracker.log_error(
        error_type="APIError",
        message="请求超时",
        retryable=True,
        step=5  # 额外的context
    )

    event = tracker.events[0]
    assert event.event_type == "error"
    assert event.data["error_type"] == "APIError"
    assert event.data["message"] == "请求超时"
    assert event.data["retryable"] is True
    assert event.data["step"] == 5


def test_log_step(tracker):
    """测试4：记录步骤"""
    tracker.log_step(
        step=1,
        action="think",
        thought="我需要读取文件"
    )

    event = tracker.events[0]
    assert event.event_type == "step"
    assert event.data["step"] == 1
    assert event.data["action"] == "think"
    assert event.data["thought"] == "我需要读取文件"


# ============ 模块2：统计计算（核心） ============

def test_get_stats_empty():
    """测试5：空事件列表的统计

    关键：避免除零错误
    """
    tracker = EventTracker(task_id="empty")
    stats = tracker.get_stats()

    assert stats["total_events"] == 0
    assert stats["api_calls"]["count"] == 0
    assert stats["api_calls"]["avg_duration_ms"] == 0  # 不能崩溃
    assert stats["api_calls"]["success_rate"] == 100.0  # 空列表默认100%


def test_get_stats_api_calls(tracker):
    """测试6：API调用统计

    测试点：
    - token累加
    - 平均耗时计算
    - 成功率计算
    """
    # 记录3次API调用
    tracker.log_api_call(model="m1", prompt_tokens=100, completion_tokens=50, duration=1.0, success=True)
    tracker.log_api_call(model="m2", prompt_tokens=200, completion_tokens=100, duration=2.0, success=True)
    tracker.log_api_call(model="m3", prompt_tokens=150, completion_tokens=75, duration=1.5, success=False)

    stats = tracker.get_stats()
    api = stats["api_calls"]

    assert api["count"] == 3
    assert api["total_tokens"] == 675  # 150 + 300 + 225
    assert api["avg_duration_ms"] == 1500  # (1000 + 2000 + 1500) / 3
    assert api["success_rate"] == 66.67  # 2/3 * 100


def test_get_stats_tool_calls_by_tool(tracker):
    """测试7：按工具名统计

    测试点：_count_by_field方法
    """
    tracker.log_tool_call("read_file", success=True, duration=0.1)
    tracker.log_tool_call("read_file", success=True, duration=0.2)
    tracker.log_tool_call("write_file", success=True, duration=0.3)
    tracker.log_tool_call("read_file", success=False, duration=0.4)

    stats = tracker.get_stats()
    tools = stats["tool_calls"]

    assert tools["count"] == 4
    assert tools["by_tool"]["read_file"] == 3
    assert tools["by_tool"]["write_file"] == 1
    assert tools["success_rate"] == 75.0  # 3/4 * 100


def test_get_stats_errors_by_type(tracker):
    """测试8：按错误类型统计"""
    tracker.log_error("APIError", "超时1", retryable=True)
    tracker.log_error("APIError", "超时2", retryable=True)
    tracker.log_error("ToolError", "文件不存在", retryable=False)

    stats = tracker.get_stats()
    errors = stats["errors"]

    assert errors["count"] == 3
    assert errors["by_type"]["APIError"] == 2
    assert errors["by_type"]["ToolError"] == 1


# ============ 模块3：文件导出测试 ============

def test_export_report(tracker, tmp_path):
    """测试9：导出完整报告

    测试点：
    - 生成2个JSON文件
    - 文件内容正确
    """
    # 记录事件
    tracker.log_api_call(model="test", prompt_tokens=100, completion_tokens=50, duration=1.0)
    tracker.log_tool_call("read_file", success=True, duration=0.5)

    # 导出报告
    stats_file, events_file = tracker.export_report(tmp_path)

    # 验证文件存在
    assert stats_file.exists()
    assert events_file.exists()

    # 验证stats.json内容
    with open(stats_file, "r", encoding="utf-8") as f:
        stats = json.load(f)

    assert stats["task_id"] == "test_task_123"
    assert stats["api_calls"]["count"] == 1
    assert stats["tool_calls"]["count"] == 1

    # 验证events.json内容
    with open(events_file, "r", encoding="utf-8") as f:
        events_data = json.load(f)

    assert len(events_data) == 2


def test_export_report_empty(tracker, tmp_path):
    """测试10：导出空报告

    测试点：即使没有事件，也能正常导出
    """
    stats_file, events_file = tracker.export_report(tmp_path)

    # 读取stats.json
    with open(stats_file, "r", encoding="utf-8") as f:
        stats = json.load(f)

    assert stats["total_events"] == 0
    assert stats["api_calls"]["count"] == 0

    # 读取events.json
    with open(events_file, "r", encoding="utf-8") as f:
        events_data = json.load(f)

    assert len(events_data) == 0


# ============ 模块4：边界和异常测试 ============

@pytest.mark.parametrize("duration,expected_ms", [
    (1.0, 1000.0),
    (0.123, 123.0),
    (0.0056, 5.6),
    (10.999, 10999.0)
])
def test_duration_conversion(tracker, duration, expected_ms):
    """测试11：时长转换的精度

    测试点：秒转毫秒，保留2位小数
    """
    tracker.log_api_call(
        model="test",
        prompt_tokens=10,
        completion_tokens=10,
        duration=duration
    )

    assert tracker.events[0].data["duration_ms"] == expected_ms


def test_event_order_preserved(tracker):
    """测试12：事件顺序保持

    测试点：按记录顺序存储，不会乱序
    """
    tracker.log_api_call(model="test", prompt_tokens=10, completion_tokens=10, duration=1.0)
    tracker.log_tool_call("read", success=True, duration=0.5)
    tracker.log_error("TestError", "测试错误", retryable=False)

    assert tracker.events[0].event_type == "api_call"
    assert tracker.events[1].event_type == "tool_call"
    assert tracker.events[2].event_type == "error"
