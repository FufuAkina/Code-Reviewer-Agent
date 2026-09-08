# 🤖 CodeAgent - AI 代码助手

  

基于 DeepSeek API 的智能代码助手，支持文件操作、代码分析等功能。采用 ReAct 架构实现工具调用和推理循环。

  

---

  

## ✨ 核心特性

  

- **🔧 工具系统**：插件化架构，支持动态加载工具

- **🔄 重试机制**：指数退避 + 抖动算法，提升 API 调用稳定性

- **⏱️ 速率限制**：Token Bucket 算法防止 API 超限

- **📊 分布式追踪**：双层 Trace ID 系统便于调试

- **🧪 完整测试**：25+ 单元测试覆盖核心功能

- **🐳 容器化部署**：Docker 一键部署，环境隔离

  

---

  

## 🛠️ 技术栈

  

- **Python 3.11+**

- **异步框架**：asyncio + aiohttp

- **LLM API**：DeepSeek Chat

- **测试框架**：pytest + pytest-asyncio

- **容器化**：Docker + Docker Compose

  

---

  

## 📦 安装

  

### **1. 克隆仓库**

  

```bash

git clone https://github.com/your-username/CodeAgent.git

cd CodeAgent

```

  

### **2. 创建虚拟环境**

  

```bash

python -m venv venv

  

# Windows

venv\Scripts\activate

  

# Linux/Mac

source venv/bin/activate

```

  

### **3. 安装依赖**

  

```bash

pip install -r requirements.txt

```

  

### **4. 配置环境变量**

  

复制 `.env.example` 为 `.env`，填入你的 API Key：

  

```bash

# Windows PowerShell

Copy-Item .env.example .env

  

# Linux/Mac

cp .env.example .env

```

  

编辑 `.env`：

  

```bash

DEEPSEEK_API_KEY=sk-your-api-key-here

DEEPSEEK_BASE_URL=https://api.deepseek.com

```

  

---

  

## 🚀 使用

  

### **运行 Agent**

  

```bash

python real_agent.py

```

  

### **运行测试**

  

```bash

# 运行所有测试

pytest tests/ -v

  

# 运行特定测试

pytest tests/test_retry.py -v

  

# 查看测试覆盖率

pytest tests/ --cov=. --cov-report=html

```

  

---

  

## 🐳 Docker 部署

  

### **构建镜像**

  

```bash

docker build -t code-agent:latest .

```

  

### **运行容器**

  

```bash

# 方式 1：docker-compose（推荐）

docker-compose run --rm code-agent

  

# 方式 2：直接运行

docker run --rm -e DEEPSEEK_API_KEY=your-key code-agent

```

  

### **在容器中运行测试**

  

```bash

docker-compose run --rm code-agent pytest tests/ -v

```

  

---

  

## 📂 项目结构

  

```

CodeAgent/

├── real_agent.py           # 主 Agent 类（ReAct 循环）

├── simple_agent.py         # 简化版 Agent（教学用）

├── config.py               # 配置管理（Config 类）

├── retry_utils.py          # 重试机制 + TokenBucket 限流

├── visualizer.py           # 执行轨迹可视化

├── code_reviewer.py        # 代码审查工具

├── ab_test.py              # A/B 测试框架（v1）

├── ab_test_v2.py           # A/B 测试框架（v2）

│

├── plugins/                # 插件目录

│   ├── base.py            # 插件基类（ABC）

│   ├── read_file.py       # 文件读取插件

│   ├── list_files.py      # 文件列表插件

│   └── analyze_code.py    # 代码分析插件

│

├── tests/                  # 测试目录

│   ├── test_retry.py      # 重试机制测试

│   ├── test_rate_limit.py # 速率限制测试

│   ├── test_plugins.py    # 插件系统测试

│   └── test_agent.py      # Agent 核心测试

│

├── Dockerfile              # Docker 镜像定义

├── docker-compose.yml      # Docker Compose 配置

├── .dockerignore          # Docker 忽略文件

│

├── requirements.txt        # Python 依赖

├── .env.example           # 环境变量示例

├── .gitignore             # Git 忽略文件

└── README.md              # 项目文档

```

  

---

  

## 🎯 核心功能

  

### **1. 工具调用**

  

支持 3 种内置工具：

  

- `read_file`：读取文件内容

- `list_files`：列出目录文件

- `analyze_code`：分析 Python 代码质量

  

示例：

  

```python

import asyncio

from real_agent import RealAgent

import os

  

async def main():

    api_key = os.getenv("DEEPSEEK_API_KEY")

    agent = RealAgent(api_key)

    await agent.run("读取 config.py 的内容")

  

asyncio.run(main())

```

  

### **2. 重试机制**

  

指数退避算法自动重试失败的 API 调用：

  

```python

@retry(

    max_attempts=3,

    base_delay=1.0,

    retryable_exceptions=(aiohttp.ClientError, asyncio.TimeoutError)

)

async def api_call():

    # 自动重试，延迟：1s → 2s → 4s

    pass

```

  

**算法原理**：

  

```python

delay = min(base_delay * (2 ** attempt), max_delay)

if jitter:

    jitter_range = delay * 0.25

    delay = delay + random.uniform(-jitter_range, jitter_range)

```

  

### **3. 速率限制**

  

Token Bucket 算法防止 API 超限：

  

```python

rate_limiter = TokenBucket(rate=0.13, capacity=2.0)

  

async with rate_limiter:

    # 受限流保护的 API 调用

    await api_call()

```

  

**参数说明**：

- `rate=0.13`：每秒补充 0.13 个 token（10 RPM）

- `capacity=2.0`：桶容量 2 个 token（允许初始突发）

  

### **4. 分布式追踪**

  

双层 Trace ID 系统：

  

```

🔍 [Trace: a1b2c3d4] 新任务开始: 列出当前目录...

✅ [Trace: a1b2c3d4] API 调用成功

```

  

- **Agent 实例 ID**：区分不同 Agent

- **Retry 调用 ID**：追踪重试次数

  

---

  

## 🧪 测试

  

项目包含 25+ 单元测试，覆盖核心功能：

  

- **重试机制**（5 个测试）

- **速率限制**（5 个测试）

- **插件系统**（8 个测试）

- **Agent 核心**（7 个测试）

  

运行测试：

  

```bash

pytest tests/ -v

```

  

预期输出：

  

```

========================= 25 passed in X.XXs =========================

```

  

---

  

## 📊 工程化改造

  

本项目实现了以下工程化特性：

  

| 特性 | 实现 | 对应岗位需求 |

|------|------|--------------|

| 重试机制 | 指数退避 + 抖动算法 | API 稳定性保障 |

| 速率限制 | Token Bucket 算法 | 防止 API 超限 |

| 结构化日志 | 双层 Trace ID | 分布式追踪调试 |

| 插件架构 | ABC 基类 + 动态加载 | 可扩展设计 |

| 单元测试 | pytest + 25+ 测试 | 代码质量保障 |

| 容器化部署 | Docker + Compose | 环境隔离 + 一键部署 |

  

---

  

## 📝 配置说明

  

### **环境变量（.env）**

  

```bash

# API 配置

DEEPSEEK_API_KEY=sk-your-api-key-here

DEEPSEEK_BASE_URL=https://api.deepseek.com

```

  

### **Config 类（config.py）**

  

```python

class Config:

    # API 配置

    API_KEY = os.getenv("DEEPSEEK_API_KEY")

    BASE_URL = os.getenv("DEEPSEEK_BASE_URL")

    MODEL = "deepseek-chat"

    MAX_TOKENS = 2000

    TEMPERATURE = 0.3

    # 重试配置

    RETRY_MAX_ATTEMPTS = 3

    RETRY_BASE_DELAY = 1.0

    RETRY_MAX_DELAY = 60.0

    # 速率限制配置

    RATE_LIMIT_ENABLED = True

    RATE_LIMIT_RATE = 0.13          # 10 RPM = 0.13 RPS

    RATE_LIMIT_CAPACITY = 2.0       # 允许初始突发 2 个请求

```

  

---

  

## 🏗️ Agent Harness 架构 

  

本项目已完成核心 Agent Harness 架构的实现，采用模块化设计，支持多 LLM 模型适配、状态管理、工具系统、事件追踪等特性。

  

### **核心模块**

  
#### **1. ModelAdapter（模型适配层）**

📁 `harness/adapters/`

  

**功能**：统一多个 LLM 提供商的 API 接口

  

**已实现**：

- `BaseModelAdapter`：抽象基类，定义统一的 `generate()` 接口

- `DeepSeekAdapter`：DeepSeek API 适配器，支持工具调用和流式输出

  

**设计模式**：适配器模式（Adapter Pattern）

  

```python

from harness.adapters import DeepSeekAdapter

  

adapter = DeepSeekAdapter(api_key="sk-xxx", base_url="https://api.deepseek.com")

response = await adapter.generate(

    messages=[{"role": "user", "content": "Hello"}],

    tools=[...],

    stream=False

)

```

  

**扩展性**：只需继承 `BaseModelAdapter` 即可添加新的 LLM 支持（如 OpenAI、Claude、Gemini）

  

---

  

#### **2. TaskState（任务状态管理）**

📁 `harness/state/`

  

**功能**：管理 Agent 任务的生命周期和状态持久化

  

**核心类**：

- `TaskState`：任务状态数据类，包含任务 ID、状态、消息历史、工具调用记录等

- `StateManager`：状态管理器，负责状态的保存、加载、快照

  

**状态机**：

```

PENDING → RUNNING → (COMPLETED | FAILED | TIMEOUT)

```

  

**持久化**：

- 自动保存到 `harness_states/{task_id}.json`

- 支持状态快照和恢复

- 便于调试和故障排查

  

```python

from harness.state import TaskState, StateManager

  

state = TaskState(task_id="task_123", user_query="读取文件")

state.add_message(role="user", content="读取 config.py")

state.transition_to("running")

  

StateManager.save_state(state)  # 自动持久化

```

  

---

  

#### **3. ToolRegistry（工具系统）**

📁 `harness/tools/`

  

**功能**：插件化工具管理，支持动态注册和调用

  

**核心组件**：

- `BaseTool`：工具抽象基类

- `ToolResult`：工具执行结果封装（成功/失败/错误信息）

- `ToolRegistry`：工具注册中心，支持动态注册和 JSON Schema 生成

  

**已实现工具**：

- `ReadFileTool`：读取文件内容

- `ListFilesTool`：列出目录文件

  

**注册示例**：

```python

from harness.tools import ToolRegistry, ReadFileTool, ListFilesTool

  

registry = ToolRegistry()

registry.register(ReadFileTool())

registry.register(ListFilesTool())

  

# 自动生成 OpenAI 工具 Schema

tools_schema = registry.to_openai_tools()

```

  

**工具调用流程**：

1. Agent 决策需要调用工具

2. Registry 查找并执行工具

3. 返回 `ToolResult`（包含结果或错误）

4. Agent 根据结果继续推理

  

---

  

#### **4. EventTracker（事件追踪）**

📁 `harness/events/`

  

**功能**：记录 Agent 执行过程中的所有关键事件，便于调试和性能分析

  

**事件类型**：

- `task_start`：任务开始

- `llm_call`：LLM API 调用

- `tool_call`：工具调用

- `state_transition`：状态转换

- `error`：错误事件

- `task_complete`：任务完成

  

**结构化日志**：

```json

{

  "event_id": "evt_abc123",

  "event_type": "tool_call",

  "timestamp": "2024-09-08T10:30:00Z",

  "task_id": "task_123",

  "data": {

    "tool_name": "read_file",

    "args": {"file_path": "config.py"},

    "result": "success"

  }

}

```

  
  

**持久化**：

- 自动保存到 `event_reports/{task_id}_events.json`

- 支持事件过滤和查询

- 便于生成执行报告

  

```python

from harness.events import EventTracker

  

tracker = EventTracker(task_id="task_123")

tracker.track_event("tool_call", {"tool_name": "read_file"})

tracker.save_report()  # 保存事件日志

```

  

---

  

#### **5. ContextManager（上下文管理）**

📁 `harness/context/`

  

**功能**：管理对话上下文窗口，防止 token 超限

  

**核心策略**：

- **滑动窗口**：保留最近 N 条消息

- **摘要压缩**：将旧消息总结为摘要（未来实现）

- **优先级保留**：始终保留 system prompt 和用户初始查询

  

**配置**：

```python

context_manager = ContextManager(max_messages=10)

context_manager.add_message({"role": "user", "content": "Hello"})

context_manager.add_message({"role": "assistant", "content": "Hi!"})

  

# 自动截断超出窗口的消息

messages = context_manager.get_messages()

```

  

**优化效果**：

- 防止 LLM API 因 token 超限而失败

- 提升长对话场景的稳定性

  

---

  

#### **6. AgentHarness（核心引擎）**

📁 `harness/core/`

  

**功能**：Agent 核心执行引擎，协调所有模块完成 ReAct 循环

  

**架构图**：

```

AgentHarness

├── ModelAdapter      # LLM 调用

├── ToolRegistry      # 工具管理

├── StateManager      # 状态持久化

├── EventTracker      # 事件日志

└── ContextManager    # 上下文管理

```

  

**ReAct 循环流程**：

```python

while not done:

    # 1. Think：LLM 推理决策

    response = await model_adapter.generate(messages, tools)

    # 2. Act：执行工具调用

    if has_tool_calls:

        results = await tool_registry.execute(tool_calls)

    # 3. Observe：观察结果并更新状态

    state.add_message(role="assistant", content=response)

    state.add_tool_result(results)

    # 4. 持久化 + 事件追踪

    state_manager.save(state)

    event_tracker.track("tool_call", {...})

```

  

**使用示例**：

```python

from harness.core import AgentHarness

import asyncio

  

async def main():

    harness = AgentHarness(

        api_key="sk-xxx",

        base_url="https://api.deepseek.com"

    )

    result = await harness.run("读取 config.py 并分析内容")

    print(result.final_answer)

  

asyncio.run(main())

```

  

**特性**：

- ✅ 自动状态持久化

- ✅ 完整事件日志

- ✅ 上下文窗口管理

- ✅ 工具调用循环

- ✅ 错误处理和重试

  

---

  

### **工程化特性对比**

  

| 特性 | （初版） | Harness） |

|------|--------------|-------------------|

| 模型支持 | 仅 DeepSeek | 支持多模型（适配器模式） |

| 状态管理 | 内存临时存储 | 持久化 + 状态机 |

| 工具系统 | 硬编码 | 插件化注册中心 |

| 日志追踪 | print 输出 | 结构化事件日志 |

| 上下文管理 | 无限制（易超限） | 滑动窗口 + 优先级保留 |

| 可测试性 | 难以测试 | 模块化 + 单元测试 |

  

---

  

### **测试覆盖**

  

已完成单元测试：

  

```bash

# 状态管理测试

python test_task_state.py

  

# 事件追踪测试

python test_event_tracker_quick.py

  

# 上下文管理测试

python test_context_manager_quick.py

  

# 工具系统测试

python test_tools.py

python test_list_files_quick.py

  

# 核心引擎测试

python test_agent_harness_quick.py

```

  

**测试输出目录**：

- `harness_states/`：状态持久化文件

- `event_reports/`：事件日志

- `harness_reports/`：执行报告

- `test_states/`：测试状态快照

  

---

  
  

### **项目结构（更新后）**

  

```

CodeAgent/

├── harness/                    # 🆕 Agent Harness 核心模块

│   ├── adapters/              # 模型适配层

│   │   ├── base.py           # 抽象基类

│   │   └── deepseek.py       # DeepSeek 适配器

│   │

│   ├── state/                 # 状态管理

│   │   ├── task_state.py     # 任务状态

│   │   └── state_manager.py  # 状态管理器

│   │

│   ├── tools/                 # 工具系统

│   │   ├── base.py           # 工具基类

│   │   ├── registry.py       # 工具注册中心

│   │   ├── result.py         # 结果封装

│   │   ├── read_file.py      # 文件读取工具

│   │   └── list_files.py     # 文件列表工具

│   │

│   ├── events/                # 事件追踪

│   │   └── tracker.py        # 事件追踪器

│   │

│   ├── context/               # 上下文管理

│   │   └── manager.py        # 上下文管理器

│   │

│   └── core/                  # 核心引擎

│       └── agent_harness.py  # Agent Harness 主类

│

├── test_agent_harness_quick.py   # 🆕 核心引擎测试

├── test_task_state.py             # 🆕 状态管理测试

├── test_event_tracker_quick.py    # 🆕 事件追踪测试

├── test_context_manager_quick.py  # 🆕 上下文管理测试

├── test_tools.py                  # 🆕 工具系统测试

├── test_list_files_quick.py       # 🆕 文件列表工具测试

│

├── harness_states/            # 🆕 状态持久化目录（不提交）

├── event_reports/             # 🆕 事件日志目录（不提交）

├── harness_reports/           # 🆕 执行报告目录（不提交）

├── test_states/               # 🆕 测试状态目录（不提交）

│

├── real_agent.py              # 初版 Agent（保留用于对比）

├── simple_agent.py            # 简化版 Agent（教学用）

├── config.py                  # 配置管理

├── retry_utils.py             # 重试机制 + 限流

│

├── plugins/                   # 初版插件目录（保留）

│   ├── __init__.py

│   ├── base.py

│   ├── read_file.py

│   ├── list_files.py

│   └── analyze_code.py

│

├── requirements.txt           # 依赖

├── .env                       # 环境变量（不提交）

├── .gitignore                 # Git 忽略

└── README.md                  # 本文档

```

  

---

  

**🎉 感谢使用 CodeAgent！**