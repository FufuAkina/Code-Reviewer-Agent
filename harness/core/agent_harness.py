"""AgentHarness - 组装所有模块的核心引擎"""
import asyncio
import time
import uuid
from typing import Optional, Dict, Any, List
from pathlib import Path

from harness.adapters.base import ModelAdapter
from harness.adapters.deepseek import DeepSeekAdapter
from harness.state.task_state import TaskState, StepRecord
from harness.tools.registry import ToolRegistry
from harness.tools.result import ToolResult
from harness.core.event_tracker import EventTracker
from harness.core.context_manager import ContextManager

class AgentHarness:
    """Agent 执行引擎 - ReAct 循环"""
    
    def __init__(
        self,
        model_adapter: ModelAdapter,
        tool_registry: ToolRegistry,
        max_steps: int = 10,
        max_context_tokens: int = 30000,
        save_dir: Optional[Path] = None
    ):
        self.model_adapter = model_adapter
        self.tool_registry = tool_registry
        self.max_steps = max_steps
        self.save_dir = save_dir or Path("harness_states")
        
        # 初始化子模块
        self.context_manager = ContextManager(
            max_tokens=max_context_tokens,
            keep_recent=10,
            use_tiktoken=True
        )
        
        # 运行时状态(每次 run 时初始化)
        self.task_state: Optional[TaskState] = None
        self.event_tracker: Optional[EventTracker] = None
        self.messages: List[Dict[str, str]] = []
        
    def _build_system_prompt(self) -> str:
        """构建 System Prompt"""
        tool_schema = self._build_tools_schema()
        
        return f"""你是一个能使用工具的 AI Agent。
        {tool_schema}

        你的任务是根据用户需求，逐步推理并调用工具完成任务。

        【关键】你的回复必须是严格的 JSON 格式：
        {{
            "thought": "你的推理过程",
            "action": "工具名称",
            "action_input": {{"参数名": "参数值"}}
        }}

        当任务完成时，返回：
        {{
            "thought": "任务已完成",
            "action": "finish",
            "action_input": {{"answer": "最终答案"}}
        }}

        重要规则：
        1. 只返回 JSON，不要用 ```json``` 包裹
        2. 只能使用上面列出的工具
        3. action_input 的参数值必须是字符串
        """
        
    def _build_tools_schema(self) -> str:
        """构建工具文档"""
        tool_names = self.tool_registry.list_tools()
        schema_text = "可用工具列表:\n\n"

        for tool_name in tool_names:
            tool = self.tool_registry.get(tool_name)
            if not tool:
                continue

            schema_text += f"工具名称: {tool.name}\n"
            schema_text += f"功能: {tool.description}\n"
            schema_text += f"参数:\n"

            params = tool.parameters.get("properties", {})
            required = tool.parameters.get("required", [])

            for param_name, param_info in params.items():
                required_mark = "必需" if param_name in required else "可选"
                schema_text += f"  - {param_name} ({param_info.get('type', 'string')}, {required_mark}): {param_info.get('description', '')}\n"

            schema_text += "\n"

        return schema_text
    
    
    async def run(self, user_request: str) -> TaskState:
        """执行任务: ReAct主循环"""
        # 初始化状态
        task_id = str(uuid.uuid4())[:8]
        self.task_state = TaskState(
            task_id=task_id,
            user_request=user_request
        )
        self.event_tracker = EventTracker(task_id=task_id)
        self.messages = []
        
        print(f"\n{'='*60}")
        print(f"🎯 任务 [{task_id}]: {user_request}")
        print(f"{'='*60}\n")
        
        # 初始化对话
        self.messages.append({
            "role": "system",
            "content": self._build_system_prompt()
        })
        self.messages.append({
            "role": "user",
            "content": f"任务: {user_request}"
        })
        
        # ReAct 循环
        for step in range(1, self.max_steps + 1):
            print(f"\n{'='*60}")
            print(f"Step {step}")
            print(f"{'='*60}")
            
            try:
                # 1. Think (调用LLM)
                decision = await self._think(step)
                
                # 2. Act (执行工具)
                if decision["action"] == "finish":
                    self.task_state.status = "completed"
                    self.task_state.save(self.save_dir)
                    print(f"\n✅ 任务完成: {decision['action_input'].get('answer', '完成')}")
                    break
                
                observation = self._act(decision["action"], decision["action_input"])
                
                # 3. 记录步骤
                self._record_step(step, decision, observation)
                
                # 4. 添加观察结果到对话
                self.messages.append({
                    "role": "user",
                    "content":  f"工具执行结果:\n{observation}\n\n请继续或返回 finish。"
                })
                
                # 5. 压缩上下文(如果需要)
                self.messages = self.context_manager.compress(self.messages)
                
            except Exception as e:
                print (f"❌ Step {step} 错误: {e}")
                self.event_tracker.log_error(
                    error_type=type(e).__name__,
                    message=str(e),
                    retryable=False,
                    step=step
                )
                self.task_state.error_count += 1
                self.task_state.last_error = str(e)
                
                if self.task_state.error_count >= 3:
                    self.task_state.status = "failed"
                    break
                
        else:
            print(f"\n⚠️  达到最大步数 {self.max_steps}")
            self.task_state.status = "max_steps_reached"

        # 保存状态和报告
        self.task_state.save(self.save_dir)
        self._export_reports()

        return self.task_state
    
    async def _think(self, step: int) -> Dict[str, Any]:
        """调用 LLM 推理 """
        start_time = time.monotonic()

        try:
            # 记录事件
            self.event_tracker.log_step(step, "think", status="started")

            # 调用ModelAdapter
            response = await self.model_adapter.chat(
                messages=self.messages,
                temperature=0.0,
                max_tokens=500
            )

            duration = time.monotonic() - start_time
            
            # 记录 API 调用
            self.event_tracker.log_api_call(
                model=response.model,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                duration=duration,
                success=True
            )
            
            # 解析 JSON
            decision = self._parse_json(response.content)
            
            print(f"💭 Thought: {decision.get('thought', 'N/A')}")
            print(f"🔧 Action: {decision.get('action', 'N/A')}")
            print(f"📥 Input: {decision.get('action_input', {})}")
            
            # 添加到对话历史
            self.messages.append({
                "role": "assistant",
                "content": response.content
            })
            
            return decision
        
        except Exception as e:
            duration = time.monotonic() - start_time
            self.event_tracker.log_api_call(
                model="unknown",
                prompt_tokens=0,
                completion_tokens=0,
                duration=duration,
                success=False,
                error=str(e)
            )
            raise
        
    def _act(self, action: str, action_input: Dict[str, Any]) -> str:
        """执行工具"""
        start_time = time.monotonic()

        try:
            result = self.tool_registry.execute(action, **action_input)
            duration = time.monotonic() - start_time
            
            # 记录工具调用
            self.event_tracker.log_tool_call(
                tool_name=action,
                success=result.success,
                duration=duration,
                error=result.error if not result.success else None
            )
            
            observation = result.to_observation()
            print(f"👀 Observation: {observation[:200]}{'...' if len(observation) > 200 else ''}")
            
            return observation
        
        except Exception as e:
            duration = time.monotonic() - start_time
            self.event_tracker.log_tool_call(
                tool_name=action,
                success=False,
                duration=duration,
                error=str(e)
            )
            return f"❌ 工具执行失败: {e}"
        
        
    def _record_step(self, step: int, decision: Dict[str, Any], observation: str):
        """记录步骤的状态"""
        step_record = StepRecord(
            step=step,
            thought=decision.get("thought", ""),
            action=decision.get("action", ""),
            action_input=decision.get("action_input", {}),
            observation=observation
        )
        self.task_state.add_step(step_record)
        
    def _parse_json(self, text: str) -> Dict[str, Any]:
        """解析 LLM 返回的 JSON"""
        import json
        import re
        
        # 移除 markdown 包裹
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON 解析失败: {e}")
            print(f"原始文本: {text[:200]}")
            return {
                "thought": "JSON 格式错误",
                "action": "finish",
                "action_input": {"answer": f"解析错误: {text[:100]}"}
            }
            
    def _export_reports(self):
        """导出统计报告"""
        if not self.event_tracker:
            return
        
        reports_dir = Path("harness_reports")
        stats_file, events_file = self.event_tracker.export_report(reports_dir)
        
        print(f"\n📊 报告已导出:")
        print(f"  统计: {stats_file}")
        print(f"  事件: {events_file}")