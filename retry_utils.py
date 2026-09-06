"""重试机制与速率限制工具模块"""

import asyncio
import random
import time
import uuid
from functools import wraps
from typing import Callable, Type, Tuple

def exponential_backoff_with_jitter(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float= 60.0,
    jitter: bool = True
) -> float:
    """计算指数退避的延迟时间
    
    Args:
        attempt: 当前重试次数（从0开始）
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        jitter: 是否添加随机抖动
        
    Returns:
        延迟时间（秒）
        
    Example:
        attempt=0 -> 1秒
        attempt=1 -> 2秒
        attempt=2 -> 4秒
        attempt=3 -> 8秒
    """
    delay = min(base_delay * (2 ** attempt), max_delay)
    
    # 添加随即抖动(+-25％)
    if jitter:
        jitter_range = delay * 0.25
        delay = delay + random.uniform(-jitter_range, jitter_range)
        
    return max(0, delay)  # 确保非负

def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Callable[[Exception, int, float], None] = None
):
    """异步重试装饰器
    
    Args:
        max_attempts: 最大尝试次数（包括首次）
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        retryable_exceptions: 可重试的异常类型元组
        on_retry: 重试回调函数 (exception, attempt, delay) -> None
        
    Example:
        @retry(max_attempts=3, base_delay=2.0)
        async def api_call():
            # 自动重试的异步函数
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            
            # 生成Trace ID
            trace_id = str(uuid.uuid4())[:8] # 取前8位2ID
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    # 尝试执行函数
                    return await func(*args, **kwargs)
                
                except retryable_exceptions as e:
                    # 使用服务端的等待时间
                    if getattr(e, "retry_after", None) is not None:
                        delay = e.retry_after
                        print(f"📋 使用服务器指定的等待时间: {delay}秒")
                    else:
                        delay = exponential_backoff_with_jitter(
                            attempt,
                            base_delay=base_delay,
                            max_delay=max_delay
                        )
                    
                    if attempt == max_attempts - 1:
                        raise
                    
                    # 调用重试回调：充重试机制中的"通知系统"
                    if on_retry:
                        on_retry(e, attempt + 1, delay)
                    else:
                        # 默认重试日志 -> 重试日志中加上Trace ID
                        import sys
                        print(f"\n⚠️  [Trace: {trace_id}] 请求失败: {e}", file=sys.stderr)
                        print(f"🔄 [Trace: {trace_id}] 第 {attempt + 1}/{max_attempts} 次重试，等待 {delay:.1f} 秒...\n", file=sys.stderr)
                        
                    # 等待后重试
                    await asyncio.sleep(delay)

            # 理论上不会到这里，但为了类型安全
            if last_exception:
                raise last_exception

        return wrapper
    return decorator
    
    
class TokenBucket:
    """Token Bucket 速率限制算法
    
    原理：
    - 桶中有固定容量的令牌
    - 每次请求消耗1个令牌
    - 令牌以固定速率补充
    - 令牌不足时需要等待
    
    Example:
        # 每秒最多5个请求
        limiter = TokenBucket(rate=5, capacity=5)
        
        async with limiter:
            await api_call()  # 自动限流
    """
    def __init__(self, rate: float, capacity: float = None):
        if rate <= 0:
            raise ValueError("rate 必须大于 0")
        
        self.rate = rate
        self.capacity = rate if capacity is None else capacity
        self.tokens = self.capacity # 初始token
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()
        
    def _refill(self):
        """补充令牌"""
        now = time.monotonic()
        elapsed = now - self.last_update
        
        # 根据经过的时间补充令牌
        new_tokens = elapsed * self.rate
        self.tokens =  min(self.tokens + new_tokens, self.capacity)
        self.last_update = now
        
    async def acquire(self, tokens: float = 1.0):
        """获取令牌（阻塞直到有足够令牌）
        
        Args:
            tokens: 需要的令牌数
        """
        if tokens <= 0 or tokens > self.capacity:
            raise ValueError("tokens必须位于0和capacity之间")
        
        async with self._lock:
            while True:
                self._refill()
                
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return
                
                # 计算需要等待的时间
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.rate
                
                await asyncio.sleep(wait_time)
                
    async def __aenter__(self):
        """异步上下文管理器入口: 决定async with什么时候发生"""
        await self.acquire()  # 自动获取token，使用完后自动释放
        return self  # as 后的对象的返回
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        return False
    

# 测试代码
if __name__ == "__main__":
    import sys
    
    # 测试1： 指数退避计算
    print("🧪 测试1: 指数退避延迟计算")
    print("=" * 50)
    for i in  range(6):
        delay = exponential_backoff_with_jitter(i, base_delay=1.0, jitter=False)
        delay_jitter = exponential_backoff_with_jitter(i, base_delay=1.0, jitter=True)
        print(f"  attempt {i}: {delay:.2f}秒 (抖动后: {delay_jitter:.2f}秒)")
        
    # 测试2: 重试装饰器
    print("\n🧪 测试2: 重试装饰器")
    print("=" * 50)

    async def test_retry():
        attempt_count = [0]  # 使用列表避免闭包问题

        @retry(
            max_attempts=3,
            base_delay=0.5,
            retryable_exceptions=(ValueError,),
            on_retry=lambda e, attempt, delay: print(
                f"  ⚠️  重试 {attempt}/3，等待 {delay:.2f}秒... (错误: {e})"
            )
        )
        async def flaky_function():
            attempt_count[0] += 1
            print(f"  🔄 执行第 {attempt_count[0]} 次")

            if attempt_count[0] < 3:
                raise ValueError("模拟失败")
            return "成功！"

        try:
            result = await flaky_function()
            print(f"  ✅ 结果: {result}")
        except Exception as e:
            print(f"  ❌ 最终失败: {e}")

    asyncio.run(test_retry())
    
    # 测试3：Token Bucket
    print("\n🧪 测试3: Token Bucket 速率限制")
    print("=" * 50)
    
    async def test_rate_limit():
        # 每秒2个令牌
        limiter = TokenBucket(rate=2.0, capacity=2.0)
        
        print("  发起5个请求（速率限制: 2请求/秒）...")
        start = time.monotonic()
        
        for i in range(5):
            async with limiter:
                elapsed = time.monotonic() - start
                print(f"  ✅ 请求 {i+1} 完成（耗时 {elapsed:.2f}秒）")
                
    asyncio.run(test_rate_limit())
    
    print("\n✅ 所有测试完成")