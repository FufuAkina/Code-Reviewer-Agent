"代码审查Agent: 综合ReAct + Tool Schema + Few-shot + 可视化"
import asyncio
import os 
import json

from real_agent import RealAgent
from visualizer import AgentVisualizer

class CodeReviewerAgent:
    """代码审查专用 Agent"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        # 启用 Few-shot 模式
        self.agent = RealAgent(api_key, use_fewshot=True)
        
    async def review_file(self, file_path: str) -> dict:
        """
        审查单个 Python 文件
        
        参数:
            file_path: Python文件路径
            
        返回:
            {
                "file":文件路径,
                "result":审查结果,
                "stats":统计执行,
                "history":执行历史
            }
        """
        task = f"审查 {file_path} 的代码质量， 包括函数长度1、类型注解、异常处理和文档字符串"
        
        print(f"\n{'='*70}")
        print(f"🔍 代码审查 Agent 启动")
        print(f"{'='*70}")
        print(f"目标文件: {file_path}")
        print(f"{'='*70}\n")
        
        # 执行审查(ReAct 循环)
        history = await self.agent.run(task, max_steps=5)
        
        # 提取最终结果
        if history and history[-1]["action"]  == "finish":
            final_answer = history[-1]["input"].get("answer", "审查失败")
        else:
            final_answer = "审查未完成(可能超时或者出错)"
        
        # 生成可视化
        visualizer = AgentVisualizer(history, task)
        stats = visualizer.generate_stats()
        mermaid = visualizer.generate_mermaid()
        
        # 保存报告
        report_filename = f"review_{file_path.replace('.py','')}_report.md"
        self._save_report(file_path, final_answer, stats, mermaid, report_filename)
        
        print(f"\n{'='*70}")
        print(f"✅ 审查完成")
        print(f"{'='*70}")
        print(f"📄 报告: {report_filename}")
        print(f"{'='*70}\n")
        
        return {
            "file": file_path,
            "result": final_answer,
            "stats": stats,
            "history": history
        }
        
    def _save_report(self, file_path: str, result:  str, stats: dict, mermaid: str, filename: str ):
        """保存审查报告(Markdown格式)"""
        lines = []
        lines.append(f"# 代码审查报告\n\n")
        lines.append(f"**文件**: `{file_path}`\n\n")
        lines.append(f"**审查时间**: 执行 {stats['total_steps']} 步\n\n")
        lines.append(f"---\n\n")
        
        lines.append(f"## 📋 审查结果\n\n")
        lines.append(f"{result}\n\n")
        lines.append(f"---\n\n")
        
        lines.append(f"## 📊 执行统计\n\n")
        lines.append(f"- **总步数**: {stats['total_steps']}\n")
        lines.append(f"- **执行状态**: {'✅ 成功' if stats['success'] else '❌ 失败'}\n")
        lines.append(f"- **工具使用**:\n")
        
        for tool, count in stats['tool_counts'].items():
            lines.append(f" -n '{tool}': {count} 次\n")
            
        if stats['duplicate_calls']:
            lines.append(f"- ⚠️ **重复调用**: Step {stats['duplicate_calls']}\n")
            
        lines.append(f"\n---\n\n")
        
        lines.append(f"🎨 执行流程图\n\n")
        lines.append(f"```mermaid\n{mermaid}\n```\n")
        
        with open(filename, "w", encoding="utf-8") as f:
            f.writelines(lines)
            
async def main():
    """主函数"""
    # 1. 获取API Key
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 错误：未设置环境变量 DEEPSEEK_API_KEY")
        print("请在 .env 文件中设置或运行：")
        print("  export DEEPSEEK_API_KEY=your_key")
        return
    
    # 2. 创建审查 Agent
    reviewer = CodeReviewerAgent(api_key)
    
    # 3. 执行审查
    target_file = "simple_agent.py"
    
    print(f"\n{'='*70}")
    print(f"🚀 代码审查 Agent - Day 4 项目实战")
    print(f"{'='*70}\n")
    
    result = await reviewer.review_file(target_file)
    
    # 4.显示结果
    print("\n📄 审查结果:\n")
    print(result['result'])
    print(f"\n💡 提示：详细报告已保存，用 Markdown 预览器查看流程图")

if __name__ == "__main__":
    asyncio.run(main())
    