"""
Few-shot A/B 测试实验 V2
专门设计能体现 Few-shot 优势的测试用例
"""

import asyncio
import os
from real_agent import RealAgent

# 精心设计的测试用例（针对 Few-shot 覆盖的错误类型）
TEST_CASES = [
    {
        "id": 1,
        "task": "列出当前目录有哪些文件",
        "expected_actions": ["list_files", "finish"],
        "description": "基础工具调用",
        "error_type": "格式错误风险"
    },
    {
        "id": 2,
        "task": "读取 real_agent.py 的内容",
        "expected_actions": ["read_file", "finish"],
        "description": "单参数工具（易缺参数）",
        "error_type": "缺少必需参数"
    },
    {
        "id": 3,
        "task": "查看 simple_agent.py 文件的代码",
        "expected_actions": ["read_file", "finish"],
        "description": "自然语言变体（易用错工具名）",
        "error_type": "工具名错误"
    },
    {
        "id": 4,
        "task": "帮我看看 ab_test.py 里写了什么",
        "expected_actions": ["read_file", "finish"],
        "description": "口语化（易复述代码）",
        "error_type": "复述代码内容"
    },
    {
        "id": 5,
        "task": "给我读一下 .env 文件",
        "expected_actions": ["read_file", "finish"],
        "description": "口语化变体（易缺引号）",
        "error_type": "参数值缺引号"
    },
    {
        "id": 6,
        "task": "列出这个文件夹的文件",
        "expected_actions": ["list_files", "finish"],
        "description": "省略参数（易传错参数名）",
        "error_type": "参数名错误"
    },
    {
        "id": 7,
        "task": "显示当前目录下所有 Python 文件",
        "expected_actions": ["list_files", "finish"],
        "description": "自然表达（易误解需求）",
        "error_type": "工具选择错误"
    },
    {
        "id": 8,
        "task": "打开 real_agent.py",
        "expected_actions": ["read_file", "finish"],
        "description": "动词变体（易用错动词对应的工具）",
        "error_type": "工具名错误"
    }
]


class ABTestRunnerV2:
    """改进版 A/B 测试运行器"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.results = {
            "without_fewshot": [],
            "with_fewshot": []
        }

    async def run_single_test(self, agent: RealAgent, test_case: dict) -> dict:
        """运行单个测试用例（改进判断逻辑）"""
        try:
            history = await agent.run(test_case["task"], max_steps=5)

            # 提取实际执行的 action 序列
            actual_actions = [step["action"] for step in history]

            # === 改进的成功判断逻辑 ===
            success = True
            failure_reason = None

            # 检查 1: 必须以 finish 结束
            if not actual_actions or actual_actions[-1] != "finish":
                success = False
                failure_reason = "未返回 finish"

            # 检查 2: 步数合理（不超过 3 步）
            elif len(actual_actions) > 3:
                success = False
                failure_reason = f"步数过多（{len(actual_actions)} 步）"

            # 检查 3: 检查最终答案质量
            else:
                final_step = history[-1]
                final_answer = final_step.get("input", {}).get("answer", "")

                # 3.1 答案不能包含明确的错误提示
                if any(keyword in final_answer for keyword in ["错误", "失败", "无法", "不存在"]):
                    # 但如果任务本身就是查找不存在的文件，这是正常的
                    if "不存在" not in test_case["task"]:
                        success = False
                        failure_reason = "答案包含错误信息"

                # 3.2 对于读文件任务，答案不能是空的或过短
                if "read_file" in actual_actions and len(final_answer) < 10:
                    success = False
                    failure_reason = "答案过短（可能格式错误）"

                # 3.3 检查是否复述了完整代码（Few-shot 示例 8 的反例）
                if "read_file" in actual_actions:
                    # 如果答案包含 "import"、"def"、"class" 等代码关键字，可能复述了代码
                    code_keywords = ["import ", "def ", "class ", "if __name__"]
                    if any(keyword in final_answer for keyword in code_keywords):
                        success = False
                        failure_reason = "复述了代码内容（应该简洁概括）"

            # 检查 4: 检查中间步骤是否有执行错误（但不是最终答案）
            if success:
                for i, step in enumerate(history[:-1]):  # 排除最后一步（finish）
                    obs = step.get("observation", "")
                    if obs.startswith("错误:") and "工具" in obs and "不存在" in obs:
                        success = False
                        failure_reason = f"工具调用失败（步骤 {i+1}）"
                        break

            return {
                "test_id": test_case["id"],
                "task": test_case["task"],
                "expected": test_case["expected_actions"],
                "actual": actual_actions,
                "success": success,
                "failure_reason": failure_reason,
                "steps": len(actual_actions),
                "history": history,
                "error_type": test_case["error_type"]
            }

        except Exception as e:
            return {
                "test_id": test_case["id"],
                "task": test_case["task"],
                "success": False,
                "failure_reason": f"异常: {str(e)}",
                "error": str(e)
            }

    async def run_group(self, use_fewshot: bool):
        """运行一组测试"""
        group_name = "with_fewshot" if use_fewshot else "without_fewshot"
        print(f"\n{'='*80}")
        print(f"🧪 测试组: {'✅ 有 Few-shot' if use_fewshot else '❌ 无 Few-shot'}")
        print(f"{'='*80}\n")

        results = []

        for i, test_case in enumerate(TEST_CASES, 1):
            print(f"\n[{i}/{len(TEST_CASES)}] 测试 #{test_case['id']}: {test_case['description']}")
            print(f"任务: \"{test_case['task']}\"")
            print(f"易错点: {test_case['error_type']}")
            print(f"{'-'*80}")

            # 为每个测试创建新的 Agent（避免历史干扰）
            agent = RealAgent(self.api_key, use_fewshot=use_fewshot)

            result = await self.run_single_test(agent, test_case)
            results.append(result)

            # 显示结果
            if result["success"]:
                print(f"\n✅ 成功")
            else:
                print(f"\n❌ 失败: {result.get('failure_reason', '未知')}")

            print(f"实际执行: {' → '.join(result['actual'])}")

            # 延迟（避免 API 限流）
            await asyncio.sleep(1.5)

        self.results[group_name] = results
        return results

    def print_summary(self):
        """打印详细对比报告"""
        print(f"\n\n{'='*80}")
        print("📊 Few-shot A/B 测试结果报告")
        print(f"{'='*80}\n")

        # === 总体成功率对比 ===
        rate_without = (sum(1 for r in self.results["without_fewshot"] if r["success"])
                       / len(self.results["without_fewshot"]) * 100)
        rate_with = (sum(1 for r in self.results["with_fewshot"] if r["success"])
                    / len(self.results["with_fewshot"]) * 100)

        print("【总体成功率】")
        print(f"  ❌ 无 Few-shot: {rate_without:.1f}%  ({sum(1 for r in self.results['without_fewshot'] if r['success'])}/{len(self.results['without_fewshot'])})")
        print(f"  ✅ 有 Few-shot: {rate_with:.1f}%  ({sum(1 for r in self.results['with_fewshot'] if r['success'])}/{len(self.results['with_fewshot'])})")

        improvement = rate_with - rate_without
        if improvement > 0:
            print(f"\n  📈 成功率提升: +{improvement:.1f}% ⬆️")
        elif improvement < 0:
            print(f"\n  📉 成功率下降: {improvement:.1f}% ⬇️")
        else:
            print(f"\n  ➡️  成功率相同: {improvement:.1f}%")

        # === 详细对比表 ===
        print(f"\n{'='*80}")
        print("【逐项对比】")
        print(f"{'='*80}")
        print(f"{'用例':<6} {'易错点':<18} {'无 Few-shot':<20} {'有 Few-shot':<20}")
        print(f"{'-'*80}")

        for i, test_case in enumerate(TEST_CASES):
            result_without = self.results["without_fewshot"][i]
            result_with = self.results["with_fewshot"][i]

            status_without = "✅ 成功" if result_without["success"] else f"❌ {result_without.get('failure_reason', '失败')}"
            status_with = "✅ 成功" if result_with["success"] else f"❌ {result_with.get('failure_reason', '失败')}"

            # 截断过长的失败原因
            status_without = status_without[:18] + "..." if len(status_without) > 18 else status_without
            status_with = status_with[:18] + "..." if len(status_with) > 18 else status_with

            print(f"#{test_case['id']:<5} {test_case['error_type']:<18} {status_without:<20} {status_with:<20}")

        # === 错误类型分析 ===
        print(f"\n{'='*80}")
        print("【错误类型分析】")
        print(f"{'='*80}")

        error_types = {}
        for i, test_case in enumerate(TEST_CASES):
            error_type = test_case["error_type"]
            result_without = self.results["without_fewshot"][i]
            result_with = self.results["with_fewshot"][i]

            if error_type not in error_types:
                error_types[error_type] = {"without": 0, "with": 0}

            if not result_without["success"]:
                error_types[error_type]["without"] += 1
            if not result_with["success"]:
                error_types[error_type]["with"] += 1

        for error_type, counts in error_types.items():
            reduction = counts["without"] - counts["with"]
            if reduction > 0:
                print(f"  ✅ {error_type}: 减少 {reduction} 次错误")
            elif reduction < 0:
                print(f"  ❌ {error_type}: 增加 {abs(reduction)} 次错误")
            else:
                print(f"  ➡️  {error_type}: 无变化")

        # === 平均步数对比 ===
        avg_steps_without = sum(r["steps"] for r in self.results["without_fewshot"]) / len(self.results["without_fewshot"])
        avg_steps_with = sum(r["steps"] for r in self.results["with_fewshot"]) / len(self.results["with_fewshot"])

        print(f"\n{'='*80}")
        print("【平均步数】")
        print(f"{'='*80}")
        print(f"  无 Few-shot: {avg_steps_without:.2f} 步")
        print(f"  有 Few-shot: {avg_steps_with:.2f} 步")

        if avg_steps_with < avg_steps_without:
            print(f"  ✅ Few-shot 减少了 {avg_steps_without - avg_steps_with:.2f} 步（更高效）")


async def main():
    # 获取 API Key
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 请设置环境变量 DEEPSEEK_API_KEY")
        return

    runner = ABTestRunnerV2(api_key)

    print("🚀 Few-shot A/B 测试实验 V2")
    print("="*80)
    print("测试策略:")
    print("  1. 8 个精心设计的用例（针对 Few-shot 覆盖的错误类型）")
    print("  2. 改进的成功判断逻辑（检测格式错误、代码复述等）")
    print("  3. 详细的错误类型分析")
    print("="*80)
    print("预计耗时: 约 30 秒（16 个测试 × 1.5 秒延迟）\n")

    input("按 Enter 开始测试...")

    # 运行两组测试
    await runner.run_group(use_fewshot=False)
    await runner.run_group(use_fewshot=True)

    # 打印对比报告
    runner.print_summary()

    print(f"\n{'='*80}")
    print("✅ 测试完成！")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
