"""测试重试机制"""

import pytest
import asyncio
from retry_utils import retry, exponential_backoff_with_jitter

# 测试 1：指数退避计算
def test_exponential_backoff():
    """测试指数退避算法"""
    # 不加抖动，结果应该是固定的
    assert exponential_backoff_with_jitter(0, base_delay=1.0, jitter=False) == 1.0
    assert exponential_backoff_with_jitter(1, base_delay=1.0, jitter=False) == 2.0
    assert exponential_backoff_with_jitter(2, base_delay=1.0, jitter=False) == 4.0
    assert exponential_backoff_with_jitter(3, base_delay=1.0, jitter=False) == 8.0
    
    # 测试最大延迟限制
    assert exponential_backoff_with_jitter(10, base_delay=1.0, max_delay=60.0, jitter=False) == 60.0

# 测试 2：成功不重试
@pytest.mark.asyncio
async def test_retry_success_no_retry():
    """测试成功情况下不重试"""
    call_count = [0]
    
    @retry(max_attempts=3, base_delay=0.1)
    async def success_func():
        call_count[0] += 1
        return "success"
    
    result = await success_func()
    assert result == "success"
    assert call_count[0] == 1  # 只调用一次

# 测试 3：失败后重试
@pytest.mark.asyncio
async def test_retry_with_failure():
    """测试失败后重试"""
    call_count = [0]
    
    @retry(max_attempts=3, base_delay=0.1, retryable_exceptions=(ValueError,))
    async def flaky_func():
        call_count[0] += 1
        if call_count[0] < 3:
            raise ValueError("模拟失败")
        return "success"
    
    result = await flaky_func()
    assert result == "success"
    assert call_count[0] == 3  # 重试 2 次后成功

# 测试 4：达到最大重试次数
@pytest.mark.asyncio
async def test_retry_max_attempts():
    """测试达到最大重试次数"""
    call_count = [0]
    
    @retry(max_attempts=3, base_delay=0.1, retryable_exceptions=(ValueError,))
    async def always_fail():
        call_count[0] += 1
        raise ValueError("永远失败")
    
    with pytest.raises(ValueError):
        await always_fail()
    
    assert call_count[0] == 3  # 调用了 3 次

# 测试 5：不可重试的异常
@pytest.mark.asyncio
async def test_retry_non_retryable_exception():
    """测试不可重试的异常"""
    call_count = [0]
    
    @retry(max_attempts=3, base_delay=0.1, retryable_exceptions=(ValueError,))
    async def type_error_func():
        call_count[0] += 1
        raise TypeError("不可重试的异常")
    
    with pytest.raises(TypeError):
        await type_error_func()
    
    assert call_count[0] == 1  # 不重试，只调用一次
