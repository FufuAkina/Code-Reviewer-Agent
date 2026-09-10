"""ContextManager测试"""
import pytest
from harness.core.context_manager import ContextManager


# ============ Fixture ============
@pytest.fixture
def manager():
    """创建ContextManager实例（使用粗略估算，避免tiktoken依赖）"""
    return ContextManager(max_tokens=100, keep_recent=3, use_tiktoken=False)


@pytest.fixture
def sample_messages():
    """创建示例消息列表"""
    return [
        {"role": "system", "content": "你是AI助手"},  # 10字符
        {"role": "user", "content": "问题1"},          # 3字符
        {"role": "assistant", "content": "回答1"},     # 3字符
        {"role": "user", "content": "问题2"},          # 3字符
        {"role": "assistant", "content": "回答2"},     # 3字符
        {"role": "user", "content": "问题3"},          # 3字符
        {"role": "assistant", "content": "回答3"},     # 3字符
    ]


# ============ 模块1：Token估算测试 ============

def test_estimate_tokens_rough(manager):
    """测试1：粗略估算token

    公式：len(text) // 2
    """
    # 中文文本
    text = "你好世界"  # 4字符
    tokens = manager.estimate_tokens(text)
    assert tokens == 2  # 4 // 2

    # 英文文本
    text = "Hello World"  # 11字符
    tokens = manager.estimate_tokens(text)
    assert tokens == 5  # 11 // 2


def test_count_messages_tokens(manager, sample_messages):
    """测试2：统计消息列表token

    计算公式：
    - 每条消息content的tokens
    - 每条消息metadata开销 +4
    """
    tokens = manager.count_messages_tokens(sample_messages)

    # 计算：
    # msg1: "你是AI助手" 6字符 = 6//2=3, +4 = 7
    # msg2-7: "问题1"等 3字符 = 3//2=1, +4 = 5, *6 = 30
    # 总计: 7 + 30 = 37
    assert tokens == 37


# ============ 模块2：压缩策略测试（核心） ============

def test_compress_no_need(manager, sample_messages):
    """测试3：未超限时不压缩

    当前39 tokens < 100 max_tokens
    """
    result = manager.compress(sample_messages)

    # 不应该压缩
    assert len(result) == 7
    assert result == sample_messages


def test_compress_keep_system_and_recent(manager):
    """测试4：超限时保留system+最近3条

    策略：
    1. 保留第一条system消息
    2. 保留最近keep_recent=3条
    3. 删除中间的旧消息
    """
    # 构造超限场景
    messages = [
        {"role": "system", "content": "A" * 10},   # 10字符 = 5 tokens
        {"role": "user", "content": "B" * 20},     # 20字符 = 10 tokens
        {"role": "assistant", "content": "C" * 20},
        {"role": "user", "content": "D" * 20},
        {"role": "assistant", "content": "E" * 20},
        {"role": "user", "content": "F" * 20},     # 最近3条
        {"role": "assistant", "content": "G" * 20},
        {"role": "user", "content": "H" * 20},
    ]

    result = manager.compress(messages)

    # 应该保留：system + 最近3条 = 4条
    assert len(result) == 4
    assert result[0]["role"] == "system"
    assert result[1]["content"] == "F" * 20  # 最近第3条
    assert result[2]["content"] == "G" * 20
    assert result[3]["content"] == "H" * 20


def test_compress_no_system_message(manager):
    """测试5：没有system消息时的压缩

    只保留最近keep_recent=3条
    """
    messages = [
        {"role": "user", "content": "A" * 50},      # 增大到50字符，确保超限
        {"role": "assistant", "content": "B" * 50},
        {"role": "user", "content": "C" * 50},
        {"role": "assistant", "content": "D" * 50},
        {"role": "user", "content": "E" * 50},     # 最近3条
        {"role": "assistant", "content": "F" * 50},
        {"role": "user", "content": "G" * 50},
    ]

    result = manager.compress(messages)

    # 应该保留最近3条
    assert len(result) == 3
    assert result[0]["content"] == "E" * 50
    assert result[1]["content"] == "F" * 50
    assert result[2]["content"] == "G" * 50


def test_compress_extreme_case(manager):
    """测试6：极端情况 - 保留部分仍超限

    当保留的消息本身就超过max_tokens时，
    启动熔断：keep_recent // 2
    """
    # 每条消息约54 tokens (100//2 + 4)
    # 3条消息 = 162 tokens > 100 max_tokens
    messages = [
        {"role": "system", "content": "S" * 100},
        {"role": "user", "content": "A" * 100},     # 最近3条
        {"role": "assistant", "content": "B" * 100},
        {"role": "user", "content": "C" * 100},
    ]

    result = manager.compress(messages)

    # 熔断：keep_recent // 2 = 3 // 2 = 1
    # 保留：system + 最近1条 = 2条
    assert len(result) == 2
    assert result[0]["role"] == "system"
    assert result[1]["content"] == "C" * 100  # 最近1条


# ============ 模块3：边界和异常测试 ============

def test_compress_empty_messages(manager):
    """测试7：空消息列表"""
    result = manager.compress([])
    assert result == []


def test_compress_single_message(manager):
    """测试8：单条消息"""
    messages = [{"role": "user", "content": "Hello"}]
    result = manager.compress(messages)
    assert len(result) == 1
    assert result == messages


@pytest.mark.parametrize("max_tokens,keep_recent,expected_len", [
    (1000, 5, 7),   # 不超限，保留全部
    (20, 2, 3),     # 超限，保留system+2条（降低max_tokens）
    (15, 1, 2),     # 超限，保留system+1条（降低max_tokens）
])
def test_compress_different_configs(sample_messages, max_tokens, keep_recent, expected_len):
    """测试9：不同配置参数的压缩结果"""
    manager = ContextManager(max_tokens=max_tokens, keep_recent=keep_recent, use_tiktoken=False)
    result = manager.compress(sample_messages)
    assert len(result) == expected_len


def test_tiktoken_fallback():
    """测试10：tiktoken初始化失败时的回退

    测试点：
    - 请求use_tiktoken=True但tiktoken不可用
    - 应该回退到粗略估算，不应该崩溃
    """
    # 即使tiktoken不可用，也应该能创建manager
    manager = ContextManager(use_tiktoken=True)

    # 应该能正常估算（可能用粗略估算）
    tokens = manager.estimate_tokens("测试文本")
    assert tokens > 0


# ============ 模块4：实际场景测试 ============

def test_realistic_conversation_compression():
    """测试11：真实对话场景

    模拟：
    - 一个30轮对话
    - max_tokens=200
    - 验证压缩后仍能保持对话连贯性
    """
    manager = ContextManager(max_tokens=200, keep_recent=5, use_tiktoken=False)

    # 构造30轮对话
    messages = [{"role": "system", "content": "你是AI助手"}]
    for i in range(1, 31):
        messages.append({"role": "user", "content": f"问题{i}"})
        messages.append({"role": "assistant", "content": f"回答{i}"})

    result = manager.compress(messages)

    # 应该保留：system + 最近5条 = 6条
    assert len(result) == 6
    assert result[0]["role"] == "system"
    assert result[-1]["content"] == "回答30"  # 最新的回答
    assert result[-2]["content"] == "问题30"  # 最新的问题


def test_metadata_overhead():
    """测试12：验证metadata开销计算

    测试点：每条消息 +4 tokens的开销
    """
    manager = ContextManager(use_tiktoken=False)

    # 空内容消息
    messages = [{"role": "user", "content": ""}]
    tokens = manager.count_messages_tokens(messages)

    # 应该是：0//2 + 4 = 4
    assert tokens == 4

    # 多条空消息
    messages = [{"role": "user", "content": ""} for _ in range(5)]
    tokens = manager.count_messages_tokens(messages)

    # 应该是：4 * 5 = 20
    assert tokens == 20
