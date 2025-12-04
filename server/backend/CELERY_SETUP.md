# Celery异步任务设置指南

## 安装依赖

```bash
pip install -r requirements.txt
```

## 启动Redis服务器

Celery需要Redis作为消息代理，请确保Redis已安装并运行：

```bash
# macOS (使用Homebrew)
brew install redis
brew services start redis

# 或者直接启动
redis-server
```

## 启动应用

### 1. 启动Flask应用
```bash
python app.py
```

### 2. 启动Celery Worker（新终端窗口）
```bash
python celery_worker.py
```

或者使用celery命令：
```bash
celery -A tasks worker --loglevel=info
```

### 3. 启动Celery监控（可选）
```bash
celery -A tasks flower
```

## API使用说明

### 创建并自动启动任务
```bash
POST /api/tasks
{
    "target": "http://example.com",
    "description": "测试任务",
    "auto_start": true
}
```

### 手动启动任务
```bash
POST /api/tasks/{task_id}/start
```

### 停止任务
```bash
POST /api/tasks/{task_id}/stop
```

### 获取任务执行状态
```bash
GET /api/tasks/status/{celery_task_id}
```

## 注意事项

1. 确保Redis服务正在运行
2. Flask应用和Celery Worker需要同时运行
3. 任务执行过程中会实时更新数据库
4. 可以通过API监控任务进度