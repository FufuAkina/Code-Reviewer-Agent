import asyncio
import json
import os
import re     # 检查函数长度
import uuid   # 添加Trace ID
from pathlib import Path
from typing import Dict, List, Any

import aiohttp

from visualizer import AgentVisualizer
from retry_utils import retry, TokenBucket   # 重试机制 + 限流
from config import Config  # 配置
from plugins.read_file import ReadFilePlugin
from plugins.list_files import ListFilesPlugin
from plugins.analyze_code import AnalyzeCodePlugin

# 加载所有插件
def load_plugins():
    """加载所有插件"""
    plugins = [
        ReadFilePlugin(),
        ListFilesPlugin(),
        AnalyzeCodePlugin(),
    ]
    
    tools = {}
    for plugin in plugins:
        tools[plugin.name] = plugin.to_dict()
        
    return tools

# 全局工具注册表
TOOLS = load_plugins()

# ==== 真实Agent ====
class RealAgent:
    def __init__(self, api_key: str, use_fewshot: bool = False):
        self.api_key = api_key
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.tools = TOOLS
        self.use_fewshot = use_fewshot
        self.history = []
        self.messages = [] # LLM对话历史

        # 初始化限流器
        self.rate_limiter = TokenBucket(
            rate=Config.RATE_LIMIT_RATE,
            capacity=Config.RATE_LIMIT_CAPACITY
        )
        
        # 为每个Agent实例生成唯一的Trace ID
        self.trace_id = str(uuid.uuid4())[:8]
        
    def _build_tool_schema(self) -> str:
        "构建工具的说明文档(给LLM看)"
        schema_text = "可用工具列表: \n\n"
        
        for name, tool in self.tools.items(): # 键值对
            schema_text += f"工具名称: {name}\n"
            schema_text += f"功能: {tool['description']}\n"
            schema_text += f"参数: \n"

            for param_name, param_info in tool['parameters'].items(): # 工具的参数名+内容("类型"、"描述")
                # 添加容错: 检查required字段是否存在
                required = "必需" if param_name in tool.get('required', []) else "可选"
                schema_text += f"  - {param_name} ({param_info['type']}, {required}): {param_info['description']}\n"

            schema_text += "\n"

        return schema_text
    
    def _get_system_prompt(self) -> str:
        "构建 System Prompt(核心)"
        
        base_prompt = f"""你是一个能使用工具的 AI Agent。
{self._build_tool_schema()}

你的任务是根据用户需求，逐步推理并调用工具完成任务。

【关键】你的回复必须是严格的 JSON 格式，不要添加任何解释、代码或其他内容：
{{
    "thought": "你的推理过程（为什么选择这个工具）",
    "action": "工具名称",
    "action_input": {{"参数名": "参数值"}}
}}

当任务完成时，返回：
{{
    "thought": "任务已完成的原因",
    "action": "finish",
    "action_input": {{"answer": "最终答案（简洁概括，不要复述完整内容）"}}
}}

重要规则：
1. 只返回 JSON，不要用 ```json``` 包裹，不要添加任何解释
2. 只能使用上面列出的工具
3. action_input 中的参数值必须是字符串，用引号包裹
4. 工具执行结果已经在"工具执行结果"中显示，不要在 answer 中重复
5. answer 应该简洁概括，不要复述完整的工具输出内容
"""
        
        if not self.use_fewshot:
            return base_prompt
        else:
            # ==== Few-shot 示例 ====
            fewshot_examples = """
━━━━━━━━━━━━━━━━━━━━━━
Few-shot 示例（学习如何正确调用工具）：

示例 1（正确 ✅）：
用户："列出当前目录有哪些文件"
{
    "thought": "用户想查看文件列表，我应该使用 list_files 工具，参数是当前目录",
    "action": "list_files",
    "action_input": {"directory": "."}
}

示例 2（正确 ✅）：
用户："读取 config.py 的内容"
{
    "thought": "用户想读取文件，我应该使用 read_file 工具，参数是文件路径",
    "action": "read_file",
    "action_input": {"file_path": "config.py"}
}

示例 3（正确 ✅）：
用户："列出文件"
工具执行结果："main.py\nutils.py\nconfig.py"
{
    "thought": "已经列出了文件，任务完成",
    "action": "finish",
    "action_input": {"answer": "当前目录的文件有：main.py、utils.py、config.py"}
}

示例 4（正确 ✅）：
用户："读取 test.py"
工具执行结果："import os\ndef main():\n    print('hello')\n..."
{
    "thought": "已经成功读取文件内容，任务完成",
    "action": "finish",
    "action_input": {"answer": "已成功读取 test.py，文件包含 import 语句和 main 函数"}
}

示例 5（错误 ❌，不要模仿）：
{
    "action": "read_file",
    "action_input": {}
}
错误原因：缺少必需参数 file_path

示例 6（错误 ❌，不要模仿）：
{
    "action": "read_file",
    "action_input": {"file_path": config.py}
}
错误原因：参数值没有用引号包裹，应该是 "config.py"

示例 7（错误 ❌，不要模仿）：
{
    "thought": "读取文件",
    "action": "open_file",
    "action_input": {"file": "test.py"}
}
错误原因：工具名称错误（应该是 read_file），参数名错误（应该是 file_path）

示例 8（错误 ❌，不要模仿）：
工具执行结果："import os..."
回复：python
import os
...
错误原因：不要复述代码内容，应该返回 JSON 格式的 finish

示例 9（代码审查 ✅）：
用户："审查 main.py 的代码质量"
{
    "thought": "用户需要代码审查，我应该使用 analyze_code 工具分析代码质量",
    "action": "analyze_code",
    "action_input": {"file_path": "main.py"}
}
工具执行结果：{"file": "main.py", "total_issues": 3, "issues": [{"line": 10, "type": "函数过长", ...}]}

下一步：
{
    "thought": "已获取代码分析结果，发现 3 个问题，整理成报告",
    "action": "finish",
    "action_input": {
        "answer": "代码审查完成，发现 3 个问题：\n1. [第10行] 函数过长：函数 process_data 有 65 行\n2. [第25行] 缺少返回类型注解：函数 load_config\n3. [第1行] 缺少异常处理：代码包含文件操作但没有 try-except"
    }
}

示例 10（错误 ❌，不要模仿）：
用户："审查 test.py"
{
    "thought": "根据经验判断代码质量",
    "action": "finish",
    "action_input": {"answer": "代码质量良好，没有明显问题"}
}
错误原因：没有先调用 analyze_code 工具，凭空猜测结果，缺乏依据
━━━━━━━━━━━━━━━━━━━━━━
"""
            return base_prompt + fewshot_examples
    
    @retry(
        max_attempts=3,
        base_delay=1.0,
        retryable_exceptions=(aiohttp.ClientError, asyncio.TimeoutError, Exception)
    )    
    async def think(self, task: str, observation: str = None) -> dict:
        "调用 LLM 推理"
        # 第一次调用: 初始化信息
        if not self.messages:
            print(f"🔍 [Trace: {self.trace_id}] 新任务开始: {task[:50]}...")
            self.messages.append({
                "role": "system",
                "content": self._get_system_prompt()
            })
            self.messages.append({
                "role": "user",
                "content": f"任务: {task}"
            })
            
        # 后续调用: 添加工具执行结果(observation)
        if observation is not None:
            self.messages.append({
                "role": "user",
                "content": f"工具执行结果：\n{observation}\n\n请继续思考下一步，或者如果任务完成就返回 finish。"
            })
            
        # 限流控制
        async with self.rate_limiter:
            # 调用DeepSeek API(retry代替了原来的try-except)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": self.messages,
                        "temperature": 0.0,
                        "max_tokens": 500
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise Exception(f"API 错误 {resp.status}: {error_text}")

                    result = await resp.json()
                    response = result["choices"][0]["message"]["content"]

                    # 记录 LLM 回复
                    self.messages.append({
                        "role": "assistant",
                        "content": response
                    })

                    # 解析 JSON
                    decision = self._parse_response(response)
                    print(f"✅ [Trace: {self.trace_id}] API 调用成功")
                    return decision
             
    def _parse_response(self, response: str) -> dict:
        "解析 LLM 返回的 JSON"
        try:
            # 处理 Markdown 包裹的 JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
                
            # 去除首尾空白
            response = response.strip()
            
            # 解析JSON
            decision = json.loads(response)
            
            # 验证必需字段
            required_fields = ["thought", "action", "action_input"] 
            for field in required_fields:
                if field not in decision:
                    raise ValueError(f"缺少必需字段: {field}")
                
            return decision
        
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON 解析失败: {e}")
            print(f"原始回复: {response}")
            return {
                "thought": "JSON 格式错误",
                "action": "finish",
                "action_input": {"answer": f"解析错误，原始回复：{response[:100]}"}
            }
            
        except Exception as e:
            print(f"⚠️  解析错误: {e}")
            return {
                "thought": "解析失败",
                "action": "finish",
                "action_input": {"answer": str(e)}
            }
            
    def act(self, action: str, action_input: dict) -> str:
        "执行工具(复用SimpleAgent)"
        if action == "finish":
            return action_input.get("answer", "完成")
        
        tool = self.tools.get(action)
        if not tool:
            return f"错误：工具 '{action}' 不存在，可用工具：{list(self.tools.keys())}"
        
        try:
            result = tool["function"](**action_input)
            return result
        except TypeError as e:
            return f"参数错误: {e}，工具 {action} 需要的参数：{tool['required']}"
        except Exception as e:
            return f"执行错误: {e}"
        
    async def run(self, task: str, max_steps: int = 5):
        "ReAct 主循环"
        print(f"🎯 任务: {task}")
        print(f"{'='*60}\n")
        
        observation  = None
        
        for step in range(1, max_steps + 1):
            print(f"{'='*60}")
            print(f"Step {step}")
            print(f"{'='*60}")
            
            # 1. Think
            decision = await self.think(task, observation)
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
            
            # 2. Act（执行）
            if decision["action"] == "finish":
                print(f"\n✅ 最终答案: {decision['action_input']['answer']}")
                print(f"{'='*60}\n")
                break
            
            observation = self.act(decision["action"], decision["action_input"])
            print(f"👀 Observation: {observation[:300]}{'...' if len(observation) > 300 else ''}")
            print()
            
            # 记录结果
            self.history[-1]["observation"] = observation
        else:
            print(f"⚠️  达到最大步数 {max_steps}，任务未完成")
        
        return self.history
    
    
# 测试
async def main():
    # 从环境变量读取 API Key
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 请设置环境变量 DEEPSEEK_API_KEY")
        return
    
    # 创建Agent(目前不适用Few-shot)
    agent = RealAgent(api_key, use_fewshot=False)
    
    # 测试任务1: 简单任务
    print("\n" + "="*60)
    print("测试 1：列出文件")
    print("="*60)
    await agent.run("列出当前目录有哪些文件")
    
    # 重置 Agent
    agent = RealAgent(api_key, use_fewshot=False)
    
     # 测试任务 2：多步任务
    print("\n" + "="*60)
    print("测试 2：读取文件")
    print("="*60)
    await agent.run("读取 simple_agent.py 的内容")
    
    # 打印history + 保存
    print("\n" + "="*60)
    print("📊 执行摘要")
    print("="*60)
    for step in agent.history:
        print(f"\nStep {step['step']}:")
        print(f"  💭 {step['thought'][:60]}...")
        print(f"  🔧 {step['action']}")
        if step['action'] != 'finish':
            obs = step.get('observation', '')[:80].replace('\n', ' ')
            print(f"  📊 {obs}...")
    
    with open("agent_history.json", "w",  encoding="utf-8") as f:
        json.dump(agent.history, f, indent=2, ensure_ascii=False)
        
    print("\n✅ 完整历史已保存到 agent_history.json")
    
    # === 任务执行完成后，生成可视化报告 ===
    print("\n" + "="*60)
    print("🎨 生成执行轨迹可视化报告...")
    print("="*60)

    # 创建可视化工具
    visualizer = AgentVisualizer(agent.history, "读取 simple_agent.py 的内容")

    # 生成数据
    stats = visualizer.generate_stats()
    mermaid = visualizer.generate_mermaid()

    # 生成报告文件
    report = []
    report.append("# Agent 执行轨迹报告\n")
    report.append(f"**任务**: 读取 simple_agent.py 的内容\n")
    report.append(f"**执行时间**: {len(agent.history)} 步\n")
    report.append("\n## 📊 统计数据\n")
    report.append(f"- 总步数: {stats['total_steps']}\n")
    report.append(f"- 执行状态: {'✅ 成功' if stats['success'] else '❌ 失败'}\n")
    report.append(f"- 工具使用:\n")
    for tool, count in stats['tool_counts'].items():
        report.append(f"  - {tool}: {count} 次\n")

    if stats['duplicate_calls']:
        report.append(f"- ⚠️ 重复调用: Step {stats['duplicate_calls']}\n")

    report.append("\n## 🎨 执行流程图\n")
    report.append("```mermaid\n")
    report.append(mermaid)
    report.append("\n```\n")

    # 保存到文件
    with open("trace_report.md", "w", encoding="utf-8") as f:
        f.writelines(report)

    print("✅ 可视化报告已生成: trace_report.md")
    print("✅ 执行历史已保存: agent_history.json")
    
    
if __name__ == "__main__":
    asyncio.run(main())
            