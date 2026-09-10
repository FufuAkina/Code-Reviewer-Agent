"""TaskState测试
展示知识点：
1. tmp_path - pytest内置的临时目录fixture
2. freezegun - 时间模拟
3. 状态机测试 - 验证非法状态转换
4. 边界条件测试 - 截断、限制
"""
import pytest
from pathlib import Path
from datetime import datetime
from freezegun import freeze_time

from harness.state.task_state import TaskState, StepRecord


# ============ Fixture 区域 ============

@pytest.fixture
def task_state():
    """创建基础TaskState实例
    
    作用：每个测试都会得到一个全新的TaskState
    """
    return TaskState.create(user_request="测试用户请求")


@pytest.fixture
def sample_step():
    """创建示例StepRecord
    
    作用：避免在每个测试中重复创建StepRecord
    """
    return StepRecord(
        step=1,
        thought="我需要读取文件",
        action="read_file",
        action_input='{"path": "test.txt"}',
        observation="文件内容: Hello World"
    )


# ============ 测试1: 创建任务 ============

def test_create_task():
    """测试创建新任务"""
    task = TaskState.create(user_request="帮我写代码")
    
    assert len(task.task_id) == 8
    assert task.status == "running"
    assert task.user_request == "帮我写代码"
    assert task.current_step == 0
    assert len(task.completed_steps) == 0


# ============ 测试2: 添加步骤 ============

def test_add_step(task_state, sample_step):
    """测试添加执行步骤"""
    task_state.add_step(sample_step)
    
    assert len(task_state.completed_steps) == 1
    assert task_state.current_step == 1
    assert task_state.completed_steps[0] == sample_step

# ============ 测试3: 超长观察结果截断 ============

def test_truncate_long_observation(task_state):
    """测试超长观察结果被截断"""
    # 创建一个超长观察结果（2000个字符）
    long_observation = "A" * 2000
    
    step = StepRecord(
        step=1,
        thought="测试",
        action="test",
        action_input="{}",
        observation=long_observation
    )
    
    task_state.add_step(step)
    
    saved_obs = task_state.completed_steps[0].observation
    assert len(saved_obs) < 2000
    assert "省略" in saved_obs
    assert saved_obs.startswith("A" * 1000)

# ============ 测试4: 历史步骤数量限制 ============

@pytest.mark.parametrize("step_count,expected_len,should_delete_first", [
    (10, 10, False),   # 远低于边界
    (49, 49, False),   # 接近边界
    (50, 50, False),   # 刚好边界（关键）
    (51, 50, True),    # 超过边界
    (100, 50, True),   # 远超边界
])
def test_max_history_steps_boundary(task_state, step_count, expected_len, should_delete_first):
    """测试历史步骤边界条件
    
    验证点：
    1. 不超过50步时，不删除
    2. 超过50步时，删除最旧的
    3. 始终保留最新的步骤
    """
    for i in range(step_count):
        step = StepRecord(step=i+1, thought=f"步骤{i+1}", action=f"操作{i+1}", action_input="{}")
        task_state.add_step(step)
    
    # 验证长度
    assert len(task_state.completed_steps) == expected_len
    
    # 验证删除逻辑
    if should_delete_first:
        # 第1步应该被删除
        assert task_state.completed_steps[0].step == step_count - expected_len + 1
        # 例如：100步，保留50步，第一个是第51步
    else:
        # 第1步应该保留
        assert task_state.completed_steps[0].step == 1
    
    # 验证最新的步骤总是保留
    assert task_state.completed_steps[-1].step == step_count



# ============ 测试5: 记录错误 ============

def test_record_error(task_state):
    """测试记录错误
    
    验证点：
    1. error_count累加
    2. last_error被更新
    """
    task_state.record_error("第一个错误")
    task_state.record_error("第二个错误")
    
    assert task_state.error_count == 2
    assert task_state.last_error == "第二个错误"


# ============ 测试6: 状态转换（合法） ============

def test_mark_completed(task_state):
    """测试标记任务完成"""
    assert task_state.status == "running"
    task_state.mark_completed()
    assert task_state.status == "completed"

def test_mark_failed(task_state):
    """测试标记任务失败"""
    assert task_state.status == "running"
    task_state.mark_failed("网络超时")
    assert task_state.status == "failed"
    assert task_state.last_error == "网络超时"


# ============ 测试7: 状态转换（非法） ============

def test_cannot_complete_failed_task(task_state):
    """测试已失败的任务不能标记为完成"""
    task_state.mark_failed("某个错误")
    
    with pytest.raises(ValueError, match="只能从running状态"):
        task_state.mark_completed()

def test_cannot_fail_completed_task(task_state):
    """测试已完成的任务不能标记为失败"""
    task_state.mark_completed()
    
    with pytest.raises(ValueError, match="只能从running状态"):
        task_state.mark_failed("不应该成功")


# ============ 测试8: 文件保存和加载 ============

def test_save_and_load(task_state, sample_step, tmp_path):
    """测试保存和加载任务状态"""
    task_state.add_step(sample_step)
    task_state.plan = "执行计划"
    task_state.tool_calls.append("read_file")
    
    task_state.save(tmp_path)
    
    saved_file = tmp_path / f"{task_state.task_id}.json"
    assert saved_file.exists()
    
    loaded = TaskState.load(saved_file)
    
    assert loaded.task_id == task_state.task_id
    assert loaded.user_request == task_state.user_request
    assert loaded.plan == "执行计划"
    assert len(loaded.completed_steps) == 1


# ============ 测试9: 超时检测 ============

@freeze_time("2024-01-01 12:00:00")
def test_is_timeout():
    """测试超时检测"""
    task = TaskState.create("测试任务")
    
    with freeze_time("2024-01-01 12:04:00"):
        assert task.is_timeout(timeout_seconds=300) is False
    
    with freeze_time("2024-01-01 12:06:00"):
        assert task.is_timeout(timeout_seconds=300) is True


# ============ 测试10: 错误阈值检测 ============

def test_should_abort(task_state):
    """测试错误次数达到阈值
    
    验证点：
    1. 2次错误不应该放弃
    2. 3次错误应该放弃
    """
    # 记录2次错误
    task_state.record_error("错误1")
    task_state.record_error("错误2")
    
    assert task_state.should_abort(max_errors=3) is False
    
    # 记录第3次错误
    task_state.record_error("错误3")
    
    assert task_state.should_abort(max_errors=3) is True
# ============ 测试11: 任务摘要 ============

@freeze_time("2024-01-01 12:00:00")
def test_get_summary(sample_step):
    """测试获取任务摘要"""
    task = TaskState.create("测试任务")
    task.add_step(sample_step)
    task.tool_calls.extend(["read_file", "write_file", "read_file"])
    task.modified_files.append("test.py")
    
    with freeze_time("2024-01-01 12:05:00"):
        task.mark_completed()
    
    summary = task.get_summary()
    
    assert summary["status"] == "completed"
    assert summary["total_steps"] == 1
    assert summary["duration_seconds"] == 300
    assert len(summary["tools_used"]) == 2  # 去重
    assert summary["files_modified"] == 1

# ============ 测试12: 兼容旧格式 ============

def test_load_legacy_format(tmp_path):
    """测试加载旧格式的任务文件"""
    legacy_data = {
        "task_id": "test_123",
        "user_request": "测试请求",
        "status": "completed",
        "current_step": 1,
        "completed_steps": [  # 旧字段名
            {
                "step": 1,
                "thought": "测试",
                "action": "test",
                "action_input": "{}",
                "observation": "结果",
                "error": None,
                "timestamp": "2024-01-01T12:00:00"
            }
        ],
        "start_time": "2024-01-01T12:00:00",
        "last_update_time": "2024-01-01T12:05:00"
    }
    
    import json
    legacy_file = tmp_path / "test_123.json"
    with open(legacy_file, "w", encoding="utf-8") as f:
        json.dump(legacy_data, f)
    
    loaded = TaskState.load(legacy_file)
    
    assert loaded.task_id == "test_123"
    assert len(loaded.completed_steps) == 1
    assert loaded.completed_steps[0].step == 1
