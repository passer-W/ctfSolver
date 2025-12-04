# CTF自动解题工具

## 项目背景

本项目是**腾讯云AI渗透智能渗透黑客松**比赛的参赛作品，由西安交通大学的**xjtuHunter**队伍开发，并获得**第二名**的优异成绩。

## 腾讯众测官方网站

https://zc.tencent.com

## 核心维护者

* 九暑（passerW）


## 项目概述

ctfSolver 是一款基于人工智能的 CTF（Capture The Flag）自动解题平台，依托大语言模型的自主探索与推理能力，精准攻克 CTF 赛题中复杂的漏洞利用挑战，能够提供覆盖多场景、多类型漏洞的端到端自动化解题方案，显著提升复杂安全竞技场景下的解题效率与适应性。


## 技术亮点

### 🚀 创新架构
- **多Agent协同工作**：采用explorer、scanner、solutioner、executor、actioner五大核心Agent，各司其职又协同配合
- **AI驱动决策**：利用大语言模型分析漏洞、生成利用思路和代码
- **前后端分离**：Flask后端提供API服务，前端界面提供友好的任务管理和监控

### ⚡ 核心能力
- **智能页面探索**：自动爬取和分析目标网站的页面结构、JavaScript文件和API端点
- **多维度漏洞扫描**：支持XSS、SQL注入、命令注入、LFI、IDOR等多种常见Web漏洞检测
- **跨场景漏洞利用**：提供不同场景的上下文记忆，组合多类型漏洞解决复杂CTF问题
- **自动化漏洞利用**：根据漏洞类型自动生成并执行利用脚本

### 🛠️ 工具扩展机制
- 支持Base64解码、JSFuck解码、PHP Filter Chain生成等安全工具
- 内置HTTP请求工具、Python代码执行和Shell命令执行功能
- 支持自定义工具扩展，满足复杂场景需求

### 🔄 并发处理优化
- 多线程并发页面探索和漏洞扫描
- 异步任务处理，提升整体解题效率
- 线程安全的结果管理和数据处理

## 应用场景

- CTF比赛自动化解题
- 网络安全培训和教育
- 安全产品评估和测试
- 漏洞研究和POC开发

## 项目结构

```
├── agent/              # 核心智能体引擎
│   ├── addons/         # 工具扩展模块
│   ├── agents/         # 多Agent功能模块（vuln漏洞提供部分示例）
│   ├── config/         # 配置文件和资源（知识库提供部分示例）
│   ├── tasks/          # 任务存储目录
│   ├── test/           # 单元测试
│   ├── utils/          # 实用工具函数
│   ├── contest_hunter.py # 比赛自动化工具
│   ├── flaghunter.py   # 主要Flag捕获工具
│   └── requirements.txt # 依赖包
├── server/             # 服务器端
│   ├── backend/        # Flask后端服务
│   ├── frontend/       # 前端界面
│   └── docker-compose.yaml # Docker部署配置
└── README.md           # 项目说明
```

## 功能特性

### 核心功能
- **页面探索**：自动爬取和分析目标网站的页面结构
- **解题支持**：根据题目场景自动生成利用脚本和漏洞利用思路
- **漏洞利用**：根据漏洞利用思路自动完成Payload构造、攻击链组合与Flag提取等完整攻击链条。

### AI Agent模块
- **explorer**：页面探索Agent
- **scanner**：漏洞扫描Agent
- **solutioner**：解题Agent
- **executor**：命令执行Agent
- **actioner**：动作执行Agent

### 工具扩展
- Base64解码
- JSFuck解码
- PHP Filter Chain生成
- HTTP请求工具
- Python代码执行
- Shell命令执行

## 安装说明

### 环境要求
- Python 3.8+
- pip
- SQLite3

### 安装步骤

1. 克隆项目
```bash
git clone <项目地址>
cd ctfSolver
```

2. 安装依赖
```bash
cd agent
pip install -r requirements.txt
```

3. 配置API密钥

编辑`agent/config/config.py`文件，配置API密钥：

```python
# DeepSeek API配置
DEEPSEEK_API_KEY = "your-deepseek-api-key"

# 腾讯云API配置
TENCENT_API_KEY = "your-tencent-api-key"
```

## 使用方法

### 后端配置

编辑`agent/config/config.py`文件，配置后端服务器地址：

```python
# 后端服务器配置
SERVER_URL = "http://backend"  # 后端服务器地址
```

### 基本使用

1. 启动Flag Hunter
```bash
cd agent
python flaghunter.py --name "ctfSolver" --challengecode "example" --mode "deepseek"
```

或者简单启动：
```bash
cd agent
python flaghunter.py
```



### 参数说明

- `--name`：Agent名称
- `--challengecode`：题目代码
- `--apitoken`：API令牌
- `--mode`：LLM模式（deepseek, tencent等）

### 前端界面

启动Agent后，可以访问前端界面进行任务下发：
```
http://frontend
```

### 启动日志示例

```
[INFO] 2025-11-27 14:28:17 [root:config.py:115] 数据库已初始化，路径：/Users/passerw/Documents/ctfSolver2/config/chat.db
[INFO] 2025-11-27 14:28:17 [root:flaghunter.py:457] ctfSolver启动中...
[INFO] 2025-11-27 14:28:17 [root:flaghunter.py:468] 正在启动Agent管理器...
[INFO] 2025-11-27 14:28:17 [root:agent_manager.py:536] 启动Agent管理器
[INFO] 2025-11-27 14:28:17 [root:agent_manager.py:61] Agent注册成功，ID: 850d7599-c579-4a2f-8ace-f7afc2e7ddfd
[INFO] 2025-11-27 14:28:17 [root:agent_manager.py:117] 启动心跳循环，间隔: 30秒
[INFO] 2025-11-27 14:28:17 [root:agent_manager.py:473] 启动任务监控循环
[INFO] 2025-11-27 14:28:17 [root:agent_manager.py:500] 任务监控已启动
[INFO] 2025-11-27 14:28:17 [root:agent_manager.py:547] Agent管理器启动成功
[INFO] 2025-11-27 14:28:17 [root:flaghunter.py:470] Agent管理器启动成功
[INFO] 2025-11-27 14:28:17 [root:flaghunter.py:474] Agent已就绪，等待任务...
```

## 工作流程

1. **页面探索**：自动爬取目标网站的所有页面
2. **漏洞检测**：对每个页面进行漏洞扫描
3. **漏洞利用**：对发现的漏洞尝试利用
4. **Flag提取**：从响应中识别并提取Flag提交至后端

## 配置文件

- `agent/config/config.py`：主配置文件
- `agent/config/pocs/`：POC脚本目录
- `agent/config/payload/`：Payload模板目录
- `agent/config/knowledge/`：知识库文件

## 开发说明

### 添加新的Agent模块

1. 在`agent/agents/`目录下创建新的Agent文件
2. 实现Agent类，继承自基础Agent类
3. 在`agent/utils/agent_manager.py`中注册新Agent

### 添加新的工具扩展

1. 在`agent/addons/`目录下创建新的工具文件
2. 实现工具类，包含`run`方法
3. 在`agent/config/addons.txt`中添加工具信息


## 服务器端部署

### Docker部署

1. 进入server目录
```bash
cd server
```

2. 启动Docker容器
```bash
docker-compose up -d
```

3. 访问前端界面
```
http://localhost:85
```

4. 后端API地址
```
http://localhost:5000
```

### 后端服务说明

- **Flask应用**：提供RESTful API接口
- **Celery**：用于异步任务处理
- **SQLite3**：数据存储
- **Redis**：Celery消息代理（需要单独安装）

## 注意事项

1. 本工具仅用于合法的CTF比赛和安全研究
2. 使用前请确保遵守比赛规则和相关法律法规
3. 请勿在未授权的系统上使用本工具
4. 服务器部署需要Docker和Docker Compose
5. Redis服务需要单独安装和配置

## 许可证

MIT License
