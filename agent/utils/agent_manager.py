import json
import time
import traceback
import uuid
import requests
import socket
import platform
import os
import psutil
import threading
from datetime import datetime
from config import config
from utils.logger import logger


class AgentManager:
    def __init__(self):
        self.agent_id = None
        self.heartbeat_thread = None
        self.task_monitor_thread = None
        self.is_running = True
        self.last_heartbeat = None
        self.start_time = datetime.now()
        self.current_task_id = None
        self.task_check_interval = 5  # 检查任务的间隔（秒）
        
    def register_agent(self):
        """注册Agent到服务器"""
        try:
            # 获取主机信息
            hostname = socket.gethostname()
            platform_info = platform.platform()
            
            agent_data = {
                "name": f"{config.NAME}({config.API_MODEL_ACTION})",
                "host": hostname,
                "port": 0,  # ctfSolver不需要监听端口
                "status": "idle",
                "capabilities": config.AGENT_CAPABILITIES,
                "metadata": {
                    "hostname": hostname,
                    "platform": platform_info,
                    "start_time": self.start_time.isoformat(),
                    "python_version": platform.python_version(),
                    "version": config.AGENT_VERSION
                }
            }
            
            response = requests.post(
                f"{config.SERVER_URL}/api/agents/register",
                json=agent_data,
                timeout=10.0
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                if result.get("success"):
                    agent_info = result.get("data", {})
                    self.agent_id = agent_info.get("id")
                    config.AGENT_ID = self.agent_id
                    logger.info(f"Agent注册成功，ID: {self.agent_id}")
                    return True
                else:
                    logger.error(f"Agent注册失败: {result.get('message', '未知错误')}")
                    return False
            else:
                logger.error(f"Agent注册失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Agent注册异常: {str(e)}")
            return False
    
    def send_heartbeat(self):
        """发送心跳包"""
        if not self.agent_id:
            logger.warning("Agent未注册，无法发送心跳")
            return False
            
        try:
            heartbeat_data = {
                "status": config.AGENT_STATUS,
                "metadata": {
                    "last_seen": datetime.now().isoformat(),
                    "current_task": self.current_task_id,
                    "uptime": str(datetime.now() - self.start_time),
                    "explored_pages": len(getattr(config, 'EXPLORED_PAGES', []))
                }
            }
            
            response = requests.post(
                f"{config.SERVER_URL}/api/agents/{self.agent_id}/heartbeat",
                json=heartbeat_data,
                timeout=5.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    self.last_heartbeat = datetime.now()
                    logger.debug(f"心跳发送成功: {self.agent_id}")
                    return True
                else:
                    logger.warning(f"心跳发送失败: {result.get('message', '未知错误')}")
                    return False
            else:
                logger.warning(f"心跳发送失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"心跳发送异常: {str(e)}")
            return False
    
    def start_heartbeat_loop(self):
        """启动心跳循环"""
        self.is_running = True
        logger.info(f"启动心跳循环，间隔: {config.HEARTBEAT_INTERVAL}秒")
        
        while self.is_running:
            self.send_heartbeat()
            time.sleep(config.HEARTBEAT_INTERVAL)
    
    def stop_heartbeat_loop(self):
        """停止心跳循环"""
        self.is_running = False
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=5)
        logger.info("心跳循环已停止")

    def get_assigned_tasks(self):
        """获取分配给当前Agent的pending状态任务"""
        if not self.agent_id:
            return []
            
        try:
            response = requests.get(
                f"{config.SERVER_URL}/api/tasks?agent_id={self.agent_id}&status=pending",
                timeout=5.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    tasks = result.get("data", [])
                    logger.debug(f"获取到 {len(tasks)} 个pending状态的任务")
                    return tasks
                else:
                    logger.warning(f"获取任务失败: {result.get('message', '未知错误')}")
                    return []
            else:
                logger.warning(f"获取任务失败: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"获取任务异常: {str(e)}")
            return []

    def update_task_status(self, task_id, status=None, is_running=None, flag=None):
        """更新任务状态"""
        try:
            update_data = {}
            
            if status is not None:
                update_data["status"] = status
                
            if is_running is not None:
                update_data["is_running"] = is_running
                
            if flag is not None:
                update_data["flag"] = flag
            
            if not update_data:
                return True
            
            response = requests.put(
                f"{config.SERVER_URL}/api/tasks/{task_id}",
                json=update_data,
                timeout=5.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    logger.debug(f"任务状态更新成功: {task_id}")
                    return True
                else:
                    logger.warning(f"任务状态更新失败: {result.get('message', '未知错误')}")
                    return False
            else:
                logger.warning(f"任务状态更新失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"任务状态更新异常: {str(e)}")
            return False

    def create_page(self, task_id, page_data):
        """为任务创建页面记录"""
        try:
            page_data["task_id"] = task_id
            # 添加发现时间
            page_data["discovered_at"] = datetime.utcnow().isoformat() + 'Z'
            
            response = requests.post(
                f"{config.SERVER_URL}/api/pages",
                json=page_data,
                timeout=10.0
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                if result.get("success"):
                    logger.debug(f"页面创建成功: {page_data.get('name', 'Unknown')}")
                    return result.get("data")
                else:
                    logger.warning(f"页面创建失败: {result.get('message', '未知错误')}")
                    return None
            else:
                logger.warning(f"页面创建失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"创建页面异常: {str(e)}")
            return None

    def create_vulnerability(self, task_id, vuln_data):
        """为任务创建漏洞记录"""
        try:
            vuln_data["task_id"] = task_id
            # 添加发现时间
            vuln_data["discovered_at"] = datetime.utcnow().isoformat() + 'Z'
            
            response = requests.post(
                f"{config.SERVER_URL}/api/vulns",
                json=vuln_data,
                timeout=10.0
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                if result.get("success"):
                    logger.info(f"漏洞创建成功: {vuln_data.get('vuln_type', 'Unknown')}")
                    return result.get("data")
                else:
                    logger.warning(f"漏洞创建失败: {result.get('message', '未知错误')}")
                    return None
            else:
                logger.warning(f"漏洞创建失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"创建漏洞异常: {str(e)}")
            return None

    def create_flag(self, task_id, flag):
        """为任务提交flag"""
        if not task_id:
            return None
        try:
            flag_data = {
                "flag": flag
            }
            
            response = requests.put(
                f"{config.SERVER_URL}/api/tasks/{task_id}",
                json=flag_data,
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    logger.info(f"Flag提交成功: {flag}")
                    return result.get("data")
                else:
                    logger.warning(f"Flag提交失败: {result.get('message', '未知错误')}")
                    return None
            else:
                logger.warning(f"Flag提交失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"提交Flag异常: {str(e)}")
            return None

    def send_message(self, task_id, message_type, content, metadata=None, status="completed"):
        """发送消息到后端"""
        if not task_id:
            return {"id": str(uuid.uuid4())}
        try:
            message_data = {
                "session_id": task_id,  # 使用task_id作为session_id
                "role": "assistant",  # AI助手角色
                "content": content,
                "type": message_type,  # pure, solution, page, summary等
                "status": status
            }

            if metadata:
                message_data["metadata"] = metadata
            
            response = requests.post(
                f"{config.SERVER_URL}/api/messages",
                json=message_data,
                timeout=10.0
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                if result.get("success"):
                    logger.info(f"消息发送成功: {message_type} - {content[:50]}...")
                    return result.get("data")
                else:
                    logger.warning(f"消息发送失败: {result.get('message', '未知错误')}")
                    return None
            else:
                logger.warning(f"消息发送失败: {response.status_code} {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"发送消息异常: {str(e)}")
            return None

    def update_message(self, message_id, content=None, metadata=None, status=None):
        """更新消息状态"""
        try:
            update_data = {}
            
            if content is not None:
                update_data["content"] = content
                
            if metadata is not None:
                update_data["metadata"] = metadata
                
            if status is not None:
                update_data["status"] = status
            
            if not update_data:
                return True
            
            response = requests.put(
                f"{config.SERVER_URL}/api/messages/{message_id}",
                json=update_data,
                timeout=5.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    logger.debug(f"消息状态更新成功: {message_id}")
                    return True
                else:
                    logger.warning(f"消息状态更新失败: {result.get('message', '未知错误')}")
                    return False
            else:
                logger.warning(f"消息状态更新失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"消息状态更新异常: {str(e)}")
            return False

    def send_pure_message_with_status(self, task_id, content, status="running"):
        """发送带状态的纯文本消息"""

        metadata = {"status": status}
        message = self.send_message(task_id, "pure", content, metadata, status)
        if status == 'running':
            if message:
                config.messages.append(message['id'])
        return message

    def update_pure_message_status(self, message_id, status="finish", content=None):
        """更新纯文本消息的状态"""
        metadata = {"status": status}

        if message_id in config.messages:
            config.messages.remove(message_id)
        return self.update_message(message_id, content, metadata, "completed")

    def send_pure_message(self, task_id, content):
        """发送纯文本消息（保持向后兼容）"""
        return self.send_message(task_id, "pure", content)

    def send_page_message(self, task_id, pages, content="发现新页面"):
        """发送页面发现消息"""
        metadata = {
            "pages": pages
        }
        return self.send_message(task_id, "page", content, metadata)

    def send_solution_message(self, task_id, solutions, content="发现解决方案"):
        """发送解决方案消息"""
        metadata = {
            "solutions": solutions
        }
        return self.send_message(task_id, "solution", content, metadata)

    def send_vulnerability_message(self, task_id, vulnerabilities, content="发现漏洞"):
        """发送漏洞消息"""
        metadata = {
            "vulnerabilities": vulnerabilities
        }
        return self.send_message(task_id, "vulnerability", content, metadata)

    def send_summary_message(self, task_id, summary_data, content="扫描总结"):
        """发送总结消息"""
        return self.send_message(task_id, "summary", content, summary_data)

    def process_task(self, task):
        """处理单个任务"""
        task_id = task.get("id")
        target = task.get("target")
        description = task.get("description", "")

        config.FLAG = None
        config.EXPLORED_PAGES = []
        config.EXPLORED_PAGE_RESPONSES = []
        config.FORMS = {}
        config.EXPLORE_URLS = []
        config.messages = []

        logger.info(f"开始处理任务: {task_id} - {target}")
        
        # 设置当前任务
        self.current_task_id = task_id
        config.TASK_ID = task_id
        config.TARGET = target
        config.DESCRIPTION = description
        config.AGENT_STATUS = "running"
        
        try:
            # 将任务状态从pending更新为running
            self.update_task_status(task_id, status="running")
            logger.info(f"任务状态已更新为running: {task_id}")
            
            # 启动FlagHunter扫描任务
            import sys
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from flaghunter import FlagHunter
            
            # 创建FlagHunter实例
            hunter = FlagHunter(url=target, description=description)

            config.HUNTER = hunter
            
            # 同步执行扫描任务
            hunter.hunt()
            
            logger.info(f"扫描任务已完成: {target}")
            
            # 扫描完成后，检查是否找到flag
            if config.FLAG:
                # 更新任务状态为finished，并设置flag
                self.update_task_status(task_id, status="finished", flag=config.FLAG)
                logger.info(f"任务完成，找到flag: {config.FLAG}")
                config.FLAG = None
            else:
                # 扫描完成但未找到flag，仍标记为finished
                self.update_task_status(task_id, status="finished")
                logger.info(f"任务完成，未找到flag")
            
        except Exception as e:
            pass
        finally:
            # 清理当前任务状态
            self.current_task_id = None
            config.TASK_ID = None
            config.AGENT_STATUS = "idle"

    def task_monitor_loop(self):
        """任务监控循环"""
        logger.info("启动任务监控循环")
        
        while self.is_running:
            try:
                # 检查分配给当前Agent的pending状态任务
                tasks = self.get_assigned_tasks()

                # 如果有新的pending任务且当前没有在处理任务
                if tasks and not self.current_task_id:
                    # 处理第一个任务（简单起见，一次只处理一个任务）
                    task = tasks[0]
                    self.process_task(task)


                # 等待一段时间再检查
                time.sleep(self.task_check_interval)
                
            except Exception as e:
                traceback.print_exc()
                logger.error(f"任务监控循环异常: {str(e)}")
                time.sleep(10)  # 出错时等待更长时间

    def start_task_monitor(self):
        """启动任务监控"""
        if not self.task_monitor_thread or not self.task_monitor_thread.is_alive():
            self.task_monitor_thread = threading.Thread(target=self.task_monitor_loop, daemon=True)
            self.task_monitor_thread.start()
            logger.info("任务监控已启动")

    def stop_task_monitor(self):
        """停止任务监控"""
        if self.task_monitor_thread and self.task_monitor_thread.is_alive():
            self.task_monitor_thread.join(timeout=5)
        logger.info("任务监控已停止")

    def unregister_agent(self):
        """注销Agent"""
        if not self.agent_id:
            return
            
        try:
            response = requests.delete(
                f"{config.SERVER_URL}/api/agents/{self.agent_id}",
                timeout=5.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    logger.info(f"Agent注销成功: {self.agent_id}")
                else:
                    logger.warning(f"Agent注销失败: {result.get('message', '未知错误')}")
            else:
                logger.warning(f"Agent注销失败: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Agent注销异常: {str(e)}")
        finally:
            self.agent_id = None
            config.AGENT_ID = None

    def start(self):
        """启动Agent管理器"""
        logger.info("启动Agent管理器")
        
        # 注册Agent
        if self.register_agent():
            # 启动心跳循环
            self.heartbeat_thread = threading.Thread(target=self.start_heartbeat_loop, daemon=True)
            self.heartbeat_thread.start()
            
            # 启动任务监控
            self.start_task_monitor()
            
            logger.info("Agent管理器启动成功")
            return True
        else:
            logger.error("Agent注册失败，无法启动管理器")
            return False

    def stop(self):
        """停止Agent管理器"""
        logger.info("停止Agent管理器")
        
        # 停止心跳循环
        self.stop_heartbeat_loop()
        
        # 停止任务监控
        self.stop_task_monitor()
        
        # 注销Agent
        self.unregister_agent()
        
        logger.info("Agent管理器已停止")


# 全局Agent管理器实例
agent_manager = AgentManager()