import asyncio
import json
from pathlib import Path

# == 工具定义 ==
def read_file(file_path: str) -> str:
    "读取文件内容"
    try:
        return Path(file_path).read_text(encoding="utf-8")
    except Exception as e:
        return f"错误: {e}"
    
def list_files(directory: str=".") -> str:
    "列出目录文件"
    try:
        files = [f.name for f in Path(directory).iterdir() if f.is_file()]
        return "\n".join(files[:10])  # 只返回前10个
    except Exception as e:
        return f"错误: {e}"
    
# == 工具注册表 ==
TOOLS = {
    "read_file": {
        "function": read_file,
        "description": "读取文件内容",
        "parameters": {"file_path": "文件路径"}
    },
    "list_files":{
        "function": list_files,
        "description": "列出目录文件",
        "parameters": {"directory": "目录路径(可选)"}
    }
}

# == 简化版Agent(不接真实LLM) ==
class SimpleAgent:
    def __init__(self):
        self.tools = TOOLS
        self.history = []  # 执行历史
        
    def think(self, task: str, observation: str = None) -> dict:
        """模拟 LLM 推理（智能版）"""
    
        # 如果是第一步（无 observation）
        if observation is None:
            if "列出" in task or "有哪些文件" in task:
                return {
                    "thought": "用户想看文件列表，第一步应该列出文件",
                    "action": "list_files",
                    "action_input": {"directory": "."}
                }
            elif "读取" in task:
                # 提取文件名（简化处理）
                file_name = "README.md"  # 实际应该从 task 中提取
                return {
                    "thought": f"用户想读文件，第一步应该读取 {file_name}",
                    "action": "read_file",
                    "action_input": {"file_path": file_name}
                }
        
        # 如果有 observation（后续步骤）
        else:
            # 检查 observation 是否包含错误
            if "错误" in observation or "Error" in observation:
                return {
                    "thought": "工具执行失败，需要处理错误",
                    "action": "finish",
                    "action_input": {"answer": f"执行失败：{observation}"}
                }
            
            # 检查是否完成任务
            if "列出" in task and observation:
                return {
                    "thought": "已经列出文件，任务完成",
                    "action": "finish",
                    "action_input": {"answer": observation}
                }
            elif "读取" in task and observation:
                return {
                    "thought": "已经读取文件，任务完成",
                    "action": "finish",
                    "action_input": {"answer": observation}
                }
        
        # 默认：任务完成
        return {
            "thought": "无法继续，结束任务",
            "action": "finish",
            "action_input": {"answer": observation or "未知"}
        }
                
    def act(self, action: str, action_input: dict) -> str:
        "执行工具"
        if action == "finish":
            return action_input["answer"]
        
        tool = self.tools.get(action)
        if not tool:
            return f"错误: 工具 {action} 不存在"
        
        try:
            result = tool["function"](**action_input)
            return result
        except Exception as e:
            return f"执行错误: {e}"
        
    def run(self, task: str, max_steps: int = 5):
        "主循环: ReAct Loop"
        print(f"🎯 任务: {task}\n")
        observation = None
        
        for step in range(1, max_steps + 1):
            print(f"==== Step {step} ====")
            
            # 1. Think(推理) - 调用推理函数
            decision = self.think(task, observation)
            print(f"💭 Thought: {decision['thought']}")
            print(f"🔧 Action: {decision['action']}")
            print(f"📥 Input: {decision['action_input']}")
            
            # 记录历史
            self.history.append({
                "step": step,
                "thought": decision["thought"],
                "action": decision["action"],
                "input": decision["action_input"]
            })
            
            # 2.Act(执行) -> 调用 act 函数
            if decision["action"] == "finish":
                print(f"✅ 最终答案: {decision['action_input']['answer']}\n")
                break
            
            observation = self.act(decision["action"], decision["action_input"])
            print(f"👀 Observation: {observation[:200]}...\n")  # 只显示前200字符
            
            # 记录结果
            self.history[-1]["observation"] = observation
            
        return self.history
    
# ==== 测试 ====
nt = SimpleAgent()
nt.run("列出当前目录有哪些文件")