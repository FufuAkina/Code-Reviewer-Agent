"""事件追踪器 - 记录 Agent 执行过程中的所有关键事件"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

@dataclass
class Event:
    """单个事件记录"""
    event_type: str  # "api_call", "tool_call", "error", "step_start", "step_end"
    timestamp: str
    data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
            
class EventTracker:
    """时间追踪器 - 记录和导出执行事件"""
    
    def __init__(self, task_id: str):
        self.task_id = task_id 
        self.events: List[Event] = []
        
    def log_api_call(self, model: str, prompt_tokens:  int, completion_tokens: int,
                     duration: float, success: bool = True, error: Optional[str] = None):
        """记录 API 调用"""
        event = Event(
            event_type="api_call",
            timestamp=datetime.now().isoformat(),
            data={
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "duration_ms":  round(duration * 1000, 2),   # 秒换算成毫秒，并保留两位小数
                "success": success,
                "error": error
            }
        )
        self.events.append(event)
        
    def log_tool_call(self, tool_name: str, success: bool, duration: float,
                      error: Optional[str] = None, **metadata):
        """记录工具调用"""
        event = Event(
            event_type="tool_call",
            timestamp=datetime.now().isoformat(),
            data={
                "tool_name": tool_name,
                "success": success,
                "duration_ms": round(duration * 1000, 2),
                "error": error,
                **metadata
            }
        )
        self.events.append(event)
        
    def log_error(self, error_type: str, message: str, retryable: bool = False, **context):
        """记录错误"""
        event = Event(
            event_type="error",
            timestamp=datetime.now().isoformat(),
            data={
                "error_type": error_type,
                "message": message,
                "retryable": retryable,
                **context
            }
        )
        self.events.append(event)
        
    def log_step(self, step: int, action: str, **data):
        """记录步骤"""
        event = Event(
            event_type="step",
            timestamp=datetime.now().isoformat(),
            data={
                "step": step,
                "action": action,
                **data
            }
        )
        self.events.append(event)
        
    def get_stats(self) -> Dict[str, Any]:
        """生成统计数据"""
        api_calls = [e for e in self.events if e.event_type == "api_call"]
        tool_calls = [e for e in self.events if e.event_type == "tool_call"]
        errors = [e for e in self.events if e.event_type == "error"]
        
        return {
            "task_id": self.task_id,
            "total_events": len(self.events),
            "api_calls": {
                "count": len(api_calls),
                "total_tokens": sum(e.data.get("total_tokens", 0) for e in api_calls),
                "avg_duration_ms": round(
                    sum(e.data.get("duration_ms", 0) for e in api_calls) / len(api_calls)
                ) if api_calls else 0,
                "success_rate": round(
                    sum(1 for e in api_calls if e.data.get("success")) / len(api_calls) * 100, 2
                ) if api_calls else 100.0
            },
            "tool_calls": {
                "count": len(tool_calls),
                "by_tool": self._count_by_field(tool_calls, "tool_name"),
                "success_rate": round(
                    sum(1 for e in tool_calls if e.data.get("success")) / len(tool_calls) * 100, 2
                ) if tool_calls else 100.0
            },
            "errors": {
                "count": len(errors),
                "by_type": self._count_by_field(errors, "error_type")
            }
        }
        
    def _count_by_field(self, events: List[Event], field: str) -> Dict[str, int]:
        """按字段field(变量)统计计数"""
        counts = {}
        for event in events:
            value = event.data.get(field, "unknown")  # value是具体字段(如工具名，错误名)
            counts[value] = counts.get(value, 0) + 1
        return counts
    
    def export_report(self, output_dir: Path):
        """导出完整报告"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 导出统计数据
        stats = self.get_stats()
        stats_file = output_dir / f"{self.task_id}_stats.json"
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
            
        # 导出完整事件日志
        events_data = [
            {
                "event_type": e.event_type,
                "time_stamp": e.timestamp,
                "data": e.data
            }
            for e in self.events
        ]
        events_file = output_dir / f"{self.task_id}_events.json"
        with open(events_file, "w", encoding="utf-8") as f:
            json.dump(events_data, f, indent=2, ensure_ascii=False)
        
        return stats_file, events_file    