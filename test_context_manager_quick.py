from harness.core.context_manager import ContextManager


def test_context_manager():
    # 测试数据
    messages = [
        {"role": "system", "content": "你是一个 AI 助手，能使用工具完成任务。" * 10},
        {"role": "user", "content": "读取 config.py 的内容"},
        {"role": "assistant", "content": '{"thought": "需要读取文件", "action": "read_file", "action_input": {"file_path": "config.py"}}'},
        {"role": "user", "content": "工具执行结果：" + "import os\n" * 50},
        {"role": "assistant", "content": '{"thought": "任务完成", "action": "finish", "action_input": {"answer": "已读取文件"}}'},
    ]
    
    print("=" * 60)
    print("📊 对比测试：tiktoken vs 粗略估算")
    print("=" * 60)
    
    # 方式 1：tiktoken（准确）
    print("\n【方式 1：tiktoken（准确）】")
    manager_tiktoken = ContextManager(max_tokens=500, keep_recent=3, use_tiktoken=True)
    tokens_tiktoken = manager_tiktoken.count_messages_tokens(messages)
    print(f"📊 总 tokens (tiktoken): {tokens_tiktoken}")
    
    # 方式 2：粗略估算
    print("\n【方式 2：粗略估算】")
    manager_estimate = ContextManager(max_tokens=500, keep_recent=3, use_tiktoken=False)
    tokens_estimate = manager_estimate.count_messages_tokens(messages)
    print(f"📊 总 tokens (估算): {tokens_estimate}")
    
    # 误差分析
    print("\n" + "=" * 60)
    diff = abs(tokens_tiktoken - tokens_estimate)
    error_rate = (diff / tokens_tiktoken * 100) if tokens_tiktoken > 0 else 0
    print(f"📈 误差: {diff} tokens ({error_rate:.1f}%)")
    print("=" * 60)
    
    # 压缩测试
    print("\n【压缩测试（使用 tiktoken）】")
    compressed = manager_tiktoken.compress(messages)
    print(f"📦 压缩后消息数: {len(messages)} → {len(compressed)}")
    compressed_tokens = manager_tiktoken.count_messages_tokens(compressed)
    print(f"✅ 压缩后 tokens: {compressed_tokens} (目标: <= 500)")


if __name__ == "__main__":
    test_context_manager()
