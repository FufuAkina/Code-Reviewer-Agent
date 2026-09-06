"""
Few-shot A/B 测试实验
对比有无 Few-shot 的成功率差异
"""

import asyncio
import os
from real_agent import RealAgent

# 测试用例集（覆盖常见错误场景）
TEST_CASES = [
    {
        "id": 1,
        "task": "列出当前目录有哪些文件",
        "expected_actions": ["list_files", "finish"],
        "description": "基础工具调用"
    },
    {
        "id": 2,
        "task": "读取 simple_agent.py 的内容",
        "expected_actions": ["read_file", "finish"],
        "description": "单参数工具"
    },
    {
        "id": 3,
        "task": "查看 real_agent.py 文件",
        "expected_actions": ["read_file", "finish"],
        "description": "自然语言变体（测试工具识别）"
    },
    {
        "id": 4,
        "task": "告诉我这个文件夹里有什么文件",
        "expected_actions": ["list_files", "finish"],
        "description": "口语化表达"
    },
    {
        "id": 5,
        "task": "列出 Desktop/Agent 目录的文件",
        "expected_actions": ["list_files", "finish"],
        "description": "带路径参数"
    }
]


class ABTestRunner:
    """A/B 测试运行器"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.results = {
            "without_fewshot": [],
            "with_fewshot": []
        }

    async def run_single_test(self, agent: RealAgent, test_case: dict) -> dict:
        """运行单个测试用例"""
        try:
            history = await agent.run(test_case["task"], max_steps=5)

            # 提取实际执行的 action 序列
            actual_actions = [step["action"] for step in history]

            # 判断是否成功
            success = (
                "finish" in actual_actions and  # 必须有 finish
                len(actual_actions) <= 3 and     # 步数合理（不超过 3 步）
                not any("错误" in step.get("observation", "") for step in history)  # 无错误
            )

            return {
                "test_id": test_case["id"],
                "task": test_case["task"],
                "expected": test_case["expected_actions"],
                "actual": actual_actions,
                "success": success,
                "steps": len(actual_actions),
                "history": history
            }

        except Exception as e:
            return {
                "test_id": test_case["id"],
                "task": test_case["task"],
                "success": False,
                "error": str(e)
            }

    async def run_group(self, use_fewshot: bool):
        """运行一组测试（5 个用例）"""
        group_name = "with_fewshot" if use_fewshot else "without_fewshot"
        print(f"\n{'='*70}")
        print(f"🧪 测试组: {'有 Few-shot' if use_fewshot else '无 Few-shot'}")
        print(f"{'='*70}\n")

        results = []

        for i, test_case in enumerate(TEST_CASES, 1):
            print(f"\n[{i}/{len(TEST_CASES)}] 测试用例 #{test_case['id']}: {test_case['description']}")
            print(f"任务: {test_case['task']}")
            print(f"{'-'*70}")

            # 为每个测试创建新的 Agent（避免历史干扰）
            agent = RealAgent(self.api_key, use_fewshot=use_fewshot)

            result = await self.run_single_test(agent, test_case)
            results.append(result)

            # 显示结果
            status = "✅ 成功" if result["success"] else "❌ 失败"
            print(f"\n结果: {status}")
            print(f"实际执行: {' → '.join(result['actual'])}")
            print(f"预期执行: {' → '.join(test_case['expected_actions'])}")

            # 延迟（避免 API 限流）
            await asyncio.sleep(2)

        self.results[group_name] = results
        return results

    def print_summary(self):
        """打印对比总结"""
        print(f"\n\n{'='*70}")
        print("📊 A/B 测试结果对比")
        print(f"{'='*70}\n")

        for group_name in ["without_fewshot", "with_fewshot"]:
            results = self.results[group_name]
            success_count = sum(1 for r in results if r["success"])
            total = len(results)
            success_rate = (success_count / total * 100) if total > 0 else 0

            label = "无 Few-shot" if group_name == "without_fewshot" else "有 Few-shot"
            print(f"{label}:")
            print(f"  成功: {success_count}/{total}")
            print(f"  成功率: {success_rate:.1f}%")
            print()

        # 计算提升
        rate_without = (sum(1 for r in self.results["without_fewshot"] if r["success"])
                       / len(self.results["without_fewshot"]) * 100)
        rate_with = (sum(1 for r in self.results["with_fewshot"] if r["success"])
                    / len(self.results["with_fewshot"]) * 100)

        improvement = rate_with - rate_without
        print(f"📈 成功率提升: {improvement:+.1f}%")

        # 详细对比表
        print(f"\n{'='*70}")
        print("详细对比:")
        print(f"{'='*70}")
        print(f"{'用例':<6} {'描述':<20} {'无 Few-shot':<15} {'有 Few-shot':<15}")
        print(f"{'-'*70}")

        for i, test_case in enumerate(TEST_CASES):
            result_without = self.results["without_fewshot"][i]
            result_with = self.results["with_fewshot"][i]

            status_without = "✅" if result_without["success"] else "❌"
            status_with = "✅" if result_with["success"] else "❌"

            print(f"#{test_case['id']:<5} {test_case['description']:<20} "
                  f"{status_without:<15} {status_with:<15}")


async def main():
    # 获取 API Key
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 请设置环境变量 DEEPSEEK_API_KEY")
        return

    runner = ABTestRunner(api_key)

    # 运行两组测试
    print("🚀 开始 A/B 测试实验...")
    print("预计耗时: 约 2 分钟（10 个测试用例 × 2 秒延迟）\n")

    # 组 A: 无 Few-shot
    await runner.run_group(use_fewshot=False)

    # 组 B: 有 Few-shot
    await runner.run_group(use_fewshot=True)

    # 打印对比结果
    runner.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
