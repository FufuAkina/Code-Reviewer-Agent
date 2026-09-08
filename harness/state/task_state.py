"""任务状态数据类"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
import uuid

@dataclass
class StepRecord:
    """单步执行记录"""
    step: int               # 步骤编号
    thought: str            # 推理过程
    action: str             # 执行动作
    action_input: str       # 动作参数
    observation: Optional[str] = None # 执行结果
    error: Optional[str] = None       # 错误信息
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
@dataclass
class TaskState:
    """任务状态
    
    作用:
    1.记录任务执行时所有信息
    2.支持保存/加载，实现任务终端回复
    3.提供任务摘要合同及
    """
    # 配置
    MAX_OBSERVATION_LENGTH = 1000 # 观察结果最大长度
    MAX_HISTORY_STEPS = 50        # 内存中最多保留50步
    
    # ==== 基本信息 ====
    task_id: str        # 任务唯一标识
    user_request: str   # 用户原始请求
    
    # ==== 执行状态 ====
    status: str = "running"   # 任务状态: running/completed/failed
    current_step: int = 0     # 当前第几步
    completed_steps: List[StepRecord] = field(default_factory=list) # 已完成的步数
    
    # ==== 计划和上下文 ====
    plan: Optional[str] = None   # Agent的执行计划
    context_summary: str = ""    # 上下文摘要
    
    # ==== 修改记录 ====
    modified_files: List[str] = field(default_factory=list)  # 修改了哪些文件
    tool_calls: List[str] = field(default_factory=list)      # 调用了哪些工具
    
    # ==== 时间和错误 ====
    start_time: str = field(default_factory=lambda:  datetime.now().isoformat())
    last_update_time: str = field(default_factory=lambda: datetime.now().isoformat())
    error_count: int = 0                # 错误次数
    last_error: Optional[str] = None    # 最后一次错误
    
    @classmethod
    def create(cls, user_request: str) -> "TaskState":
        """创建新任务
        
        Args:
            user_requests: 用户请求
            
        Returns:
            TaskState: 新任务状态
        """
        return cls(
            task_id=str(uuid.uuid4())[:8],
            user_request=user_request
        )
    
    def _truncate_observation(self, obs: str, max_length: int = 1000) -> str:
        """截断过长的观察结果
        
        Args:
            obs: 观察结果
            max_length: 最大长度
            
        Returns:
            截断后的文本
        """
        if len(obs) <= max_length:
            return obs
    
        return obs[:max_length] + f"\n...(省略 {len(obs) - max_length} 字符)"    
    
    def add_step(self, step_record: StepRecord):
        """添加执行步骤(优化版)"""
        # 1. 截断观察结果
        if step_record.observation:
            step_record.observation = self._truncate_observation(
                step_record.observation,
                self.MAX_OBSERVATION_LENGTH
            )
        
        # 2.添加到列表
        self.completed_steps.append(step_record)
        
        # 3.超过限制, 删除最旧的
        if len(self.completed_steps) > self.MAX_HISTORY_STEPS:
            self.completed_steps.pop(0)
            
        self.current_step = step_record.step
        self.last_update_time = datetime.now().isoformat()
        
    def record_error(self, error: str):
        """记录错误"""
        self.error_count += 1
        self.last_error = error
        self.last_update_time = datetime.now().isoformat()
        
    def mark_completed(self):
        """标记任务完成"""
        self.status = "completed"
        self.last_update_time = datetime.now().isoformat()
        
    def mark_failed(self, reason: str):
        """标记任务失败"""
        self.status = "failed"
        self.last_error = reason
        self.last_update_time = datetime.now().isoformat()
        
    def save(self, save_dir: Path):
        """保存任务状态到文件
        
        Args:
            save_dir: 保存目录
        """
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / f"{self.task_id}.json"
        
        # 转换为可序列化的字典
        data = {
            "task_id": self.task_id,
            "user_request": self.user_request,
            "status": self.status,
            "current_step": self.current_step,
            "recent_steps": [  # 只保留最近的10步
                {
                    "step": s.step,
                    "thought": s.thought,
                    "action": s.action,
                    "action_input": s.action_input,
                    "observation": s.observation,
                    "error": s.error,
                    "timestamp": s.timestamp
                }
                for s in self.completed_steps[-10:]
            ],
            "plan": self.plan,
            "context_summary": self.context_summary,
            "tool_calls": self.tool_calls,
            "start_time": self.start_time,
            "last_update_time": self.last_update_time,
            "error_count": self.error_count,
            "last_error": self.last_error
        }
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
            
    @classmethod
    def load(cls, file_path: Path) -> "TaskState":
        """从文件加载任务状态
        
        Args:
            file_path: 文件路径
            
        Returns:
            TaskState: 加载的任务状态
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 兼容两种格式: recent_steps(新) 和 completed_steps(旧)
        steps_data = data.get("recent_steps", data.get("completed_steps", []))
        
        # 重建 StepRecord 对象
        completed_steps = [
            StepRecord(
                step=s["step"],
                thought=s["thought"],
                action=s["action"],
                action_input=s["action_input"],
                observation=s.get("observation"),
                error=s.get("error"),
                timestamp=s["timestamp"]
            )
            for s in steps_data
        ]
        
        return cls(
            task_id=data["task_id"],
            user_request=data["user_request"],
            status=data["status"],
            current_step=data["current_step"],
            completed_steps=completed_steps,
            plan=data.get("plan"),
            context_summary=data.get("context_summary", ""),
            modified_files=data.get("modified_files", []),
            tool_calls=data.get("tool_calls", []),
            start_time=data["start_time"],
            last_update_time=data["last_update_time"],
            error_count=data.get("error_count", 0),
            last_error=data.get("last_error")
        )
        
    # 添加任务统计方法
    def get_summary(self) -> Dict[str, Any]:
        """获取任务摘要
        
        Returns:
            包含统计信息的字典
        """
        duration = None
        if self.start_time:
            start = datetime.fromisoformat(self.start_time)
            if self.status ==  "completed": 
                end = datetime.fromisoformat(self.last_update_time)
            else:
                end = datetime.now()
            duration = (end - start).total_seconds()
            
        return {
            "task_id": self.task_id,
            "status": self.status,
            "total_steps": len(self.completed_steps),
            "current_step": self.current_step,
            "error_count": self.error_count,
            "duration_seconds": duration,
            "tools_used": list(set(self.tool_calls)), # 去重
            "files_modified": len(self.modified_files)
        }
        
    # 添加任务超时jiance
    def is_timeout(self, timeout_seconds: int = 300) -> bool:
        """检查任务是否超时
        
        Args:
            timeout_seconds: 超时阈值(默认 5 min)
            
        Return:
            是否超时
        """
        if not self.last_update_time:
            return False
        
        last_update = datetime.fromisoformat(self.last_update_time)
        elapsed = (datetime.now() - last_update).total_seconds()
        return elapsed > timeout_seconds
    
    # 添加错误阈值检测
    def should_abort(self, max_errors: int = 3) -> bool:
        """判断是否应该放弃任务
        
        Args:
            max_errors: 最大错误次数
            
        Returns:
            是否应该放弃
        """
        return self.error_count >= max_errors