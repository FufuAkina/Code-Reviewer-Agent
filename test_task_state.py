from harness.state.task_state import TaskState, StepRecord
from pathlib import Path

# 测试创建
state = TaskState.create("读取 config.py")
print(f"✅ 创建任务: {state.task_id}")

# 测试添加步骤
step = StepRecord(
    step=1,
    thought="需要读取文件",
    action="read_file",
    action_input={"file_path": "config.py"},
    observation="x" * 2000  # 2000 字符，测试截断
)
state.add_step(step)
print(f"✅ 添加步骤，observation 长度: {len(state.completed_steps[0].observation)}")  # 应该是 1000

# 测试保存
state.save(Path("./test_states"))
print(f"✅ 保存成功: ./test_states/{state.task_id}.json")

# 测试加载
loaded = TaskState.load(Path(f"./test_states/{state.task_id}.json"))
print(f"✅ 加载成功: {loaded.user_request}")

# 测试摘要
summary = state.get_summary()
print(f"✅ 任务摘要: {summary}")
