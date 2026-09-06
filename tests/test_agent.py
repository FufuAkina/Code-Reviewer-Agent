"""测试 Agent 核心功能"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from real_agent import RealAgent, TOOLS

# 测试 1：工具加载
def test_tools_loaded():
    """测试工具是否正确加载"""
    assert len(TOOLS) == 3
    assert "read_file" in TOOLS
    assert "list_files" in TOOLS
    assert "analyze_code" in TOOLS

# 测试 2：Agent 初始化
def test_agent_initialization():
    """测试 Agent 初始化"""
    agent = RealAgent(api_key="sk-test", use_fewshot=False)
    
    assert agent.api_key == "sk-test"
    assert agent.tools == TOOLS
    assert len(agent.history) == 0
    assert len(agent.messages) == 0
    assert hasattr(agent, "trace_id")
    assert hasattr(agent, "rate_limiter")

# 测试 3：工具执行
def test_agent_act_finish():
    """测试 finish 动作"""
    agent = RealAgent(api_key="sk-test", use_fewshot=False)
    result = agent.act("finish", {"answer": "完成"})
    assert result == "完成"

def test_agent_act_invalid_tool():
    """测试无效工具"""
    agent = RealAgent(api_key="sk-test", use_fewshot=False)
    result = agent.act("invalid_tool", {})
    assert "不存在" in result

# 测试 4：响应解析
def test_agent_parse_response_valid_json():
    """测试解析有效的 JSON 响应"""
    agent = RealAgent(api_key="sk-test", use_fewshot=False)
    
    response = '{"thought": "测试", "action": "list_files", "action_input": {}}'
    decision = agent._parse_response(response)
    
    assert decision["thought"] == "测试"
    assert decision["action"] == "list_files"
    assert decision["action_input"] == {}

def test_agent_parse_response_markdown_wrapped():
    """测试解析 Markdown 包裹的 JSON"""
    agent = RealAgent(api_key="sk-test", use_fewshot=False)
    
    response = '```json\n{"thought": "测试", "action": "finish", "action_input": {"answer": "完成"}}\n```'
    decision = agent._parse_response(response)
    
    assert decision["action"] == "finish"

def test_agent_parse_response_invalid_json():
    """测试解析无效的 JSON"""
    agent = RealAgent(api_key="sk-test", use_fewshot=False)
    
    response = 'invalid json'
    decision = agent._parse_response(response)
    
    assert decision["action"] == "finish"
    assert "解析错误" in decision["thought"] or "JSON" in decision["thought"]
