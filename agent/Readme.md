后端配置：config.py - SERVER_URL，配置为后端地址 http://backend

启动agent：
python flaghunter.py
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

启动后访问http://frontend 进行任务下发。