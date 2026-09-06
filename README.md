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
├── real_agent.py           # 主 Agent 类（ReAct 循环）
├── simple_agent.py         # 简化版 Agent（教学用）
├── config.py               # 配置管理（Config 类）
├── retry_utils.py          # 重试机制 + TokenBucket 限流
├── visualizer.py           # 执行轨迹可视化
├── code_reviewer.py        # 代码审查工具
├── ab_test.py              # A/B 测试框架（v1）
├── ab_test_v2.py           # A/B 测试框架（v2）
│
├── plugins/                # 插件目录
│   ├── base.py            # 插件基类（ABC）
│   ├── read_file.py       # 文件读取插件
│   ├── list_files.py      # 文件列表插件
│   └── analyze_code.py    # 代码分析插件
│
├── tests/                  # 测试目录
│   ├── test_retry.py      # 重试机制测试
│   ├── test_rate_limit.py # 速率限制测试
│   ├── test_plugins.py    # 插件系统测试
│   └── test_agent.py      # Agent 核心测试
│
├── Dockerfile              # Docker 镜像定义
├── docker-compose.yml      # Docker Compose 配置
├── .dockerignore          # Docker 忽略文件
│
├── requirements.txt        # Python 依赖
├── .env.example           # 环境变量示例
├── .gitignore             # Git 忽略文件
└── README.md              # 项目文档
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
    RATE_LIMIT_RATE = 0.13          # 10 RPM = 0.13 RPS
    RATE_LIMIT_CAPACITY = 2.0       # 允许初始突发 2 个请求
```

---

## 🎓 学习路线

本项目适合以下学习路径：

### **Day 1：Agent 基础**
- 理解 Agent 核心概念（感知 → 决策 → 执行）
- 实现 SimpleAgent（工具注册 + 模拟推理）
- 文件：`simple_agent.py`

### **Day 2：ReAct 架构**
- 学习 ReAct 循环（Think → Act → Observe）
- 集成真实 LLM（DeepSeek API）
- 文件：`real_agent.py`

### **Day 3：提示工程**
- System Prompt 设计
- Few-shot 示例优化
- JSON 格式约束

### **Day 4：可视化 + A/B 测试**
- 执行轨迹可视化（Mermaid 流程图）
- A/B 测试框架
- 代码审查工具
- 文件：`visualizer.py`、`ab_test_v2.py`、`code_reviewer.py`

### **Day 5：工程化改造**
- 重试机制（指数退避）
- 速率限制（Token Bucket）
- 结构化日志（Trace ID）
- 插件架构（ABC）
- 单元测试（pytest）
- Docker 部署
- 文件：`retry_utils.py`、`plugins/`、`tests/`

---
