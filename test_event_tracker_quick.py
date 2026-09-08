import time
from pathlib import Path
from harness.core.event_tracker import EventTracker


def test_event_tracker():
    tracker = EventTracker(task_id="test_001")
    
    # 模拟 API 调用
    tracker.log_api_call(
        model="deepseek-chat",
        prompt_tokens=100,
        completion_tokens=50,
        duration=0.5,
        success=True
    )
    
    # 模拟工具调用
    tracker.log_tool_call(
        tool_name="read_file",
        success=True,
        duration=0.1,
        file_size=1024
    )
    
    # 模拟错误
    tracker.log_error(
        error_type="APIError",
        message="Rate limit exceeded",
        retryable=True
    )
    
    # 查看统计
    stats = tracker.get_stats()
    print("\n📊 统计数据:")
    print(f"总事件数: {stats['total_events']}")
    print(f"API 调用: {stats['api_calls']['count']} 次")
    print(f"工具调用: {stats['tool_calls']['count']} 次")
    print(f"错误: {stats['errors']['count']} 次")
    
    # 导出报告
    output_dir = Path("event_reports")
    stats_file, events_file = tracker.export_report(output_dir)
    print(f"\n✅ 报告已导出:")
    print(f"  统计: {stats_file}")
    print(f"  事件: {events_file}")


if __name__ == "__main__":
    test_event_tracker()
