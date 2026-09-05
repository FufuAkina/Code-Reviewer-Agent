"""
Agent 执行轨迹可视化工具
"""

import json
from pathlib import Path


class AgentVisualizer:
    """Agent 执行历史可视化"""
    
    def __init__(self, history: list, task: str):
        """
        初始化可视化工具
        
        参数:
            history: Agent 的执行历史（来自 agent.history）
            task: 任务描述（字符串）
        """
        self.history = history
        self.task = task
    
    def generate_stats(self) -> dict:
        """
        生成统计数据
        
        返回:
            {
                "total_steps": 总步数,
                "tool_counts": {"工具名": 使用次数},
                "success": 是否成功,
                "duplicate_calls": [重复步骤编号列表]
            }
        """
        # 1. 总步数
        total_steps = len(self.history)
        
        # 2. 统计工具使用次数
        tool_counts = {}
        for step in self.history:
            action = step["action"]
            if action != "finish":  # 不统计 finish
                # 字典的 get() 方法：如果 key 不存在返回默认值 0
                tool_counts[action] = tool_counts.get(action, 0) + 1
        
        # 3. 是否成功（最后一步是 finish）
        success = self.history[-1]["action"] == "finish"
        
        # 4. 检测重复调用
        duplicate_calls = []
        for i in range(len(self.history) - 1):
            current = self.history[i]
            next_step = self.history[i + 1]
            
            # 比较 action 和 input 是否完全相同
            if (current["action"] == next_step["action"] and 
                current["input"] == next_step["input"]):
                duplicate_calls.append(i + 1)
        
        return {
            "total_steps": total_steps,
            "tool_counts": tool_counts,
            "success": success,
            "duplicate_calls": duplicate_calls
        }

    
    def generate_mermaid(self) -> str:
        """
        生成 Mermaid 流程图代码
        
        返回:
            Mermaid 格式的字符串
        """
        lines = []
        
        # 1. 图类型声明
        lines.append("graph TD")
        
        # 2. 起始节点
        lines.append(f"    Start([用户任务: {self.task}])")
        lines.append("    Start --> Step1")
        lines.append("")
        
        # 3. 遍历每一步
        for i, step in enumerate(self.history, 1):
            step_num = step["step"]
            thought = step["thought"]
            action = step["action"]
            action_input = step["input"]
            
            # 截断过长的文本（Mermaid 不支持太长的标签）
            thought_short = thought[:40] + "..." if len(thought) > 40 else thought
            
            # Step 节点
            lines.append(f"    Step{step_num}[Step {step_num}: Think]")
            
            # Thought 连线
            lines.append(f'    Step{step_num} --> |"💭 {thought_short}"| Action{step_num}')
            
            # Action 节点
            if action == "finish":
                # 如果是 finish，显示答案
                answer = action_input.get("answer", "完成")[:30]
                lines.append(f"    Action{step_num}[🏁 finish]")
                lines.append(f'    Action{step_num} --> |"✅ {answer}..."| End([完成])')
                break
            else:
                # 如果是工具调用，显示工具名
                lines.append(f"    Action{step_num}[🔧 {action}]")
                
                # Observation 连线（连到下一步）
                obs = step.get("observation", "无结果")
                obs_short = obs[:30].replace("\n", " ") + "..." if len(obs) > 30 else obs
                
                next_step_num = step_num + 1
                lines.append(f'    Action{step_num} --> |"📊 {obs_short}"| Step{next_step_num}')
                lines.append("")
        
        # 4. 添加样式
        lines.append("")
        lines.append("    style Start fill:#e1f5ff")
        lines.append("    style End fill:#c8e6c9")
        
        # 给所有 Action 节点添加样式
        for i in range(1, len(self.history) + 1):
            lines.append(f"    style Action{i} fill:#fff9c4")
        
        return "\n".join(lines)



if __name__ == "__main__":
    # 从文件读取 history
    with open("agent_history.json", "r", encoding="utf-8") as f:
        history = json.load(f)
    
    # 创建可视化工具
    visualizer = AgentVisualizer(history, "读取 simple_agent.py 的内容")
    
    # 测试统计功能
    print("📊 统计数据:")
    stats = visualizer.generate_stats()
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    # 测试 Mermaid 生成
    print("\n🎨 Mermaid 流程图:")
    print("=" * 60)
    mermaid = visualizer.generate_mermaid()
    print(mermaid)
    
    # 保存到文件
    with open("trace.md", "w", encoding="utf-8") as f:
        f.write("# Agent 执行轨迹\n\n")
        f.write("```mermaid\n")
        f.write(mermaid)
        f.write("\n```")
    
    print("\n✅ Mermaid 代码已保存到 trace.md")

