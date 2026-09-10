"""DeepSeek适配器测试"""
import pytest
import aiohttp
from unittest.mock import AsyncMock, MagicMock, patch

from harness.adapters.deepseek import DeepSeekAdapter
from harness.adapters.base import(
    ModelResponse,
    AuthenticationError,
    RateLimiterError,
    ServerError,
    APIError
)

@pytest.fixture
def adapter():
    """创建DeepSeekAdapter实例
    
    fixture的作用:
    1.每个测试函数自动获得这个adapter
    2.测试完后自动销毁(不污染其他测试)
    """
    return DeepSeekAdapter(
        api_key="test_key__12345",
        base_url="https://api.deepseek.com",
        model="deepseek-chat"
    )
    
@pytest.mark.asyncio
async def test_chat_success(adapter):
    """测试正常调用成功
    
    测试策略:
    1.Mock掉aiohttp.ClientSession(不真实发送请求)
    2.返回预设的JSON(模拟DeepSeek API响应)
    3.验证返回的ModelResponse是否正确解析
    """
    # 构造假的API返回
    mock_response_data = {
        "choices": [
            {
                "message": {"content": "你好， 我是AI助手"},
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20
        },
        "model": "deepseek-chat"
    }
    
    # 创建Mock对象
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=mock_response_data)
    
    # 创建异步上下文管理器Mock
    mock_context_manager = AsyncMock()
    mock_context_manager.__aenter__.return_value = mock_resp
    mock_context_manager.__aexit__.return_value = None
    
    # Mock session.post()返回上下文管理器
    mock_session = MagicMock()
    mock_session.post.return_value = mock_context_manager
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None
    
    # 拦截aiohttp.ClientSession, 替换为我们的mock
    with patch("aiohttp.ClientSession", return_value=mock_session):
        # 执行测试
        result = await adapter.chat(
            messages=[{"role": "user", "content": "你好"}],
            temperature=0.7,
            max_tokens=100
        )
        
    # 验证结果
    assert isinstance(result, ModelResponse)
    assert result.content == "你好， 我是AI助手"
    assert result.finish_reason == "stop"
    assert result.prompt_tokens ==  10
    assert result.completion_tokens == 20
    assert result.total_tokens == 30
 
# 新增测试实验: 截断问题   
@pytest.mark.asyncio
async def test_finish_reason_length(adapter):
    """测试输出被截断的场景
    
    为什么要测试这个？
    - 发现你的系统是否处理了截断情况
    - 验证token计数准确性
    - 为"超长任务续写"功能打基础
    """
    mock_response_data = {
        "choices": [{
            "message": {"content": "这是一个很长的回答，但是被截"},
            "finish_reason": "length"  # 👈 关键！
        }],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 500  # 达到max_tokens上限
        },
        "model": "deepseek-chat"
    }
    
    # Mock配置（和之前一样）
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=mock_response_data)
    
    mock_context_manager = AsyncMock()
    mock_context_manager.__aenter__.return_value = mock_resp
    mock_context_manager.__aexit__.return_value = None
    
    mock_session = MagicMock()
    mock_session.post.return_value = mock_context_manager
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        result = await adapter.chat(
            messages=[{"role": "user", "content": "分析这个文件"}],
            max_tokens=500
        )
    
    # 验证：系统能正确识别截断
    assert result.finish_reason == "length"  # 👈 如果这里失败，说明解析有问题
    assert result.completion_tokens == 500

# parametrize测试错误码
@pytest.mark.parametrize("status_code, expected_exception, error_message",[
    (401, AuthenticationError, "API Key无效"),
    (429, RateLimiterError, "请求过于频繁"),
    (500, ServerError, "服务器错误 500"),
    (503, ServerError, "服务器错误 503"),
    (400, APIError, "API 错误 400"), # 其他错误
])
@pytest.mark.asyncio
async def test_api_errors(adapter, status_code, expected_exception, error_message):
    """批量测试API错误场景
    
    parametrize的3个参数：
    1. status_code: HTTP状态码（401/429/500等）
    2. expected_exception: 期望抛出的异常类型
    3. error_message: 期望的错误消息关键字
    
    为什么要测试这些？
    - 401: API Key过期，系统应该立即报错（不可重试）
    - 429: 速率限制，系统应该自动重试（可重试）
    - 500/503: 服务器错误，系统应该重试（可重试）
    - 400: 其他错误，记录日志
    """
    # Mock错误效应
    mock_resp = AsyncMock()
    mock_resp.status = status_code
    mock_resp.text = AsyncMock(return_value=f"Error: {error_message}")
    
    # Mock上下文管理器
    mock_context_manager = AsyncMock()
    mock_context_manager.__aenter__.return_value = mock_resp
    mock_context_manager.__aexit__.return_value = None
    
    mock_session = MagicMock()
    mock_session.post.return_value = mock_context_manager
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None
    
    # 执行测试: 沿着呢个抛出正确的异常
    with patch("aiohttp.ClientSession", return_value=mock_session):
        with pytest.raises(expected_exception) as exc_info:
            await adapter.chat(
                messages=[{"role": "user", "content":  "测试"}],
                max_tokens=100
            )
            
        # 验证异常是否包含关键字
        assert error_message in str(exc_info.value)