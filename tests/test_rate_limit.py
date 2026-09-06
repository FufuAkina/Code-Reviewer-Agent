"""测试限流机制"""

import pytest
import asyncio
import time
from retry_utils import TokenBucket

# 测试 1：初始化
def test_token_bucket_init():
    """测试 Token Bucket 初始化"""
    limiter = TokenBucket(rate=5.0, capacity=10.0)
    assert limiter.rate == 5.0
    assert limiter.capacity == 10.0
    assert limiter.tokens == 10.0

# 测试 2：无效参数
def test_token_bucket_invalid_rate():
    """测试无效的速率参数"""
    with pytest.raises(ValueError):
        TokenBucket(rate=0)
    
    with pytest.raises(ValueError):
        TokenBucket(rate=-1)

# 测试 3：立即获取令牌
@pytest.mark.asyncio
async def test_token_bucket_immediate_acquire():
    """测试立即获取令牌"""
    limiter = TokenBucket(rate=10.0, capacity=5.0)
    
    start = time.monotonic()
    
    # 前 5 个请求应该立即完成
    for _ in range(5):
        await limiter.acquire()
    
    elapsed = time.monotonic() - start
    assert elapsed < 0.5  # 应该在 0.5 秒内完成

# 测试 4：限流等待
@pytest.mark.asyncio
async def test_token_bucket_rate_limiting():
    """测试限流等待"""
    limiter = TokenBucket(rate=2.0, capacity=2.0)
    
    start = time.monotonic()
    
    # 前 2 个立即完成，第 3 个需要等待
    for _ in range(3):
        await limiter.acquire()
    
    elapsed = time.monotonic() - start
    assert elapsed >= 0.4  # 第 3 个需要等待约 0.5 秒 (1/2)
    assert elapsed < 1.0   # 但不会超过 1 秒

# 测试 5：异步上下文管理器
@pytest.mark.asyncio
async def test_token_bucket_context_manager():
    """测试异步上下文管理器"""
    limiter = TokenBucket(rate=5.0, capacity=2.0)
    
    async with limiter:
        pass  # 自动获取令牌
    
    assert limiter.tokens < 2.0  # 令牌已被消耗
