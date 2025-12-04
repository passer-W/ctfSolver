#!/usr/bin/env python3
"""
AI Agent自动攻防挑战赛 - 自动化解题工具
根据比赛API文档实现自动化解题流程
"""

# 模块级 imports 修改
import json
import time
import requests
import traceback
import signal
import sys
import os
from typing import List, Dict, Optional
from flaghunter import FlagHunter
from utils.logger import logger
from config import config

import subprocess
import random
import string
from datetime import datetime



class ContestHunter:
    """比赛自动化解题工具"""
    
    def __init__(self, api_token: str, base_url: str = "http://10.0.0.6:8000", mode: str = "deepseek"):
        """
        初始化比赛工具
        
        Args:
            api_token: API认证令牌
            base_url: API基础URL
            mode: LLM模式（默认 deepseek）
        """
        self.api_token = api_token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.solved_challenges = set()  # 已解决的题目
        self.running = True
        # 新增：并发与后端参数、作业状态
        self.server_url = config.SERVER_URL
        self.max_concurrency = 3
        self.max_runtime_seconds = 30 * 60  # 10分钟
        self.active_jobs: Dict[str, Dict] = {}  # {challenge_code: {'proc': Popen, 'agent_id': str, 'start_ts': float}}
        self.dispatched_codes: set[str] = set()  # 本轮已派发的题目
        # 新增：每题运行次数与提示获取记录
        self.run_counts: Dict[str, int] = {}
        self.hint_fetched: set[str] = set()
        # 新增：模式传递到 flaghunter.py
        self.mode = mode

        self.extra_index = 3

        self.extra_key = ""
    
    def get_challenges(self) -> Optional[List[Dict]]:
        """获取当前阶段赛题列表"""
        try:
            url = f"{self.base_url}/api/v1/challenges"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                challenges = data.get("challenges", [])
                solved = sum(1 for c in challenges if c.get("solved", False))
                logger.info(f"获取到 {len(challenges)} 个赛题（已解决 {solved}/{len(challenges)}）")

                challenge_codes = sorted([c["challenge_code"] for c in challenges])

                if self.extra_index >= len(challenge_codes):
                    self.extra_index = 0

                self.extra_key = challenge_codes[self.extra_index]

                challenges = [c for c in challenges if c["challenge_code"] != self.extra_key]

                return challenges
            elif response.status_code == 401:
                logger.error("API认证失败，请检查API_TOKEN")
                return None
            elif response.status_code == 429:
                logger.warning("请求过于频繁，等待后重试")
                time.sleep(5)
                return self.get_challenges()
            else:
                logger.error(f"获取赛题失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"获取赛题异常: {str(e)}")
            return None
    
    def get_hint(self, challenge_code: str) -> Optional[Dict]:
        """获取题目提示"""
        try:
            url = f"{self.base_url}/api/v1/hint/{challenge_code}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                hint_data = response.json()
                logger.info(f"获取题目 {challenge_code} 提示: {hint_data.get('hint_content', '')}")
                if hint_data.get('first_use', False):
                    logger.warning(f"首次查看提示，将扣除 {hint_data.get('penalty_points', 0)} 分")
                return hint_data
            elif response.status_code == 500:
                error_detail = response.json().get('detail', '未知错误')
                logger.error(f"获取提示失败: {error_detail}")
                return None
            else:
                logger.error(f"获取提示失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"获取提示异常: {str(e)}")
            return None
    
    def submit_answer(self, challenge_code: str, answer: str) -> Optional[Dict]:
        """提交答案"""
        try:
            url = f"{self.base_url}/api/v1/answer"
            data = {
                "challenge_code": challenge_code,
                "answer": answer
            }
            
            response = requests.post(url, headers=self.headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('correct', False):
                    points = result.get('earned_points', 0)
                    was_solved = result.get('is_solved', False)
                    if was_solved:
                        logger.info(f"题目 {challenge_code} 答案正确（重复提交），获得 {points} 分")
                    else:
                        logger.info(f"题目 {challenge_code} 答案正确！获得 {points} 分")
                        self.solved_challenges.add(challenge_code)
                else:
                    logger.warning(f"题目 {challenge_code} 答案错误")
                return result
            elif response.status_code == 500:
                error_detail = response.json().get('detail', '未知错误')
                logger.error(f"提交答案失败: {error_detail}")
                return None
            else:
                logger.error(f"提交答案失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"提交答案异常: {str(e)}")
            return None
    
    def run_contest(self):
        """运行比赛主循环（并发派发与进程管理版）"""
        logger.info("开始AI Agent自动攻防挑战赛（并发派发）")

    
        while self.running:
            try:
                # 1) 获取赛题列表（保持原实现不变）
                challenges = self.get_challenges()
                all_count = len(challenges)
                if not challenges:
                    logger.warning("无法获取题目列表，等待后重试")
                    time.sleep(10)
                    continue
    
                # 2) 过滤未解决赛题并随机打乱顺序
                unsolved = [c for c in challenges if not c.get("solved", False)]
                random.shuffle(unsolved)
                for c in challenges:
                    if c.get("solved") and c.get("challenge_code") not in self.dispatched_codes:
                        self.dispatched_codes.add(c.get("challenge_code"))
                if not unsolved and not self.active_jobs:
                    logger.info("所有题目已解决或无待处理任务，等待新题目...")
                    time.sleep(30)
                    continue
    
                # 3) 调度：同时派发最多两道赛题
                for c in unsolved:
                    if len(self.active_jobs) >= self.max_concurrency:
                        break
                    code = c.get("challenge_code")
                    if not code or code in self.active_jobs or code in self.dispatched_codes:
                            continue

                    # 3.1 记录现有Agent集合
                    before_ids = {a.get("id") for a in self.list_agents() if a.get("id")}
    
                    # 3.2 启动子进程（随机8字符名）
                    rand_name = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
                    proc = self.start_agent_process(rand_name, code)
                    logger.info(f"已启动Agent进程，赛题: {code}，Name: {rand_name}，PID: {proc.pid}")
    
                    # 3.3 等待新Agent注册
                    agent_id = self.wait_for_agent_registration(before_ids, timeout=30)
                    if not agent_id:
                        logger.error(f"Agent未在30秒内注册：{code}，终止进程")
                        self.safe_terminate(proc)
                        continue

                    # 运行次数 +1
                    count = self.run_counts.get(code, 0)
                    self.run_counts[code] = count
    
    
                    # 计算目标URL
                    target = self.compute_target_url(c)

                    target_info = c.get("target_info", {})
    
                    # 第五次运行获取hint，并加入到描述中
                    description = f"比赛题目: {code}\n题目信息：{target_info}"
           
                    if count >= 5 and code not in self.hint_fetched:
                        hint = self.get_hint(code)
                        if hint and hint.get("hint_content"):
                            description = f"{description}\n[HINT] {hint.get('hint_content')}"
                            self.hint_fetched.add(code)
    
                    # 3.4 创建任务并派发到该Agent
                    task = self.create_task(agent_id, target, description=description)
                    if not task:
                        logger.error(f"任务创建失败：{code} -> {target}，终止进程")
                        self.safe_terminate(proc)
                        continue
    
                    # 3.5 记录活跃作业
                    self.active_jobs[code] = {"proc": proc, "agent_id": agent_id, "start_ts": time.time()}
                    self.dispatched_codes.add(code)
                    logger.info(f"已派发赛题 {code} 到 Agent {agent_id}，目标 {target}（第{count}次运行）")
    
                # 4) 监控：解出则终止；超时10分钟也终止
                now = time.time()
                for code in list(self.active_jobs.keys()):
                    job = self.active_jobs.get(code)
                    if not job:
                        continue
                    # 查本轮状态
                    ch = next((x for x in challenges if x.get("challenge_code") == code), None)
                    if ch and ch.get("solved", False):
                        logger.info(f"赛题 {code} 已解出，终止对应Agent进程")
                        self.safe_terminate(job["proc"])
                        self.active_jobs.pop(code, None)
                        continue
                    # 检查超时
                    if now - job["start_ts"] > self.max_runtime_seconds:
                        logger.warning(f"赛题 {code} 超时，终止对应Agent进程")
                        self.safe_terminate(job["proc"])
                        self.active_jobs.pop(code, None)
    
                # 5) 若本轮8题已全部派发且当前无活跃作业，开始下一轮（仅未解出）
                round_total = len(challenges)

                if round_total >= all_count and len(self.dispatched_codes) >= all_count and not self.active_jobs:
                    logger.info("本轮8道题已全部派发，开始下一轮针对未解出的赛题")
                    self.dispatched_codes.clear()

                time.sleep(3)
    
    
            except KeyboardInterrupt:
                logger.info("收到中断信号，停止比赛")
                self.running = False
                break
            except Exception as e:
                logger.error(f"比赛主循环异常: {str(e)}")
                logger.error(traceback.format_exc())
                time.sleep(10)
    
    def stop(self):
        """停止比赛"""
        self.running = False

    def list_agents(self) -> List[Dict]:
        """获取本地后端所有Agent列表"""
        try:
            resp = requests.get(f"{self.server_url}/api/agents", timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", []) if isinstance(data, dict) else []
            return []
        except Exception:
            return []

    def start_agent_process(self, name: str, challenge_code: str) -> subprocess.Popen:
        """启动 flaghunter.py 子进程"""
        cmd = [
            "python3",  # 按你的要求使用 python3
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "flaghunter.py"),
            "--name", name,
            "--challengecode", challenge_code,
            "--apitoken", self.api_token,
            "--mode", self.mode,
        ]
        return subprocess.Popen(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))

    def wait_for_agent_registration(self, previous_ids, timeout= 30) :
        """等待新Agent注册（通过ID集合差异检测新注册）"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            agents = self.list_agents()
            current_ids = {a.get("id") for a in agents if a.get("id")}
            new_ids = list(current_ids - previous_ids)
            if new_ids:
                # 选第一个新ID（通常只有一个）
                return new_ids[0]
            time.sleep(1)
        return None

    def create_task(self, agent_id: str, target: str, description) -> Optional[Dict]:
        """向本地后端为指定Agent创建任务"""
        try:
            payload = {"target": target, "description": description, "agent_id": agent_id}
            resp = requests.post(f"{self.server_url}/api/tasks", json=payload, timeout=10.0)
            if resp.status_code in (200, 201):
                result = resp.json()
                if isinstance(result, dict) and result.get("success"):
                    return result.get("data")
            return None
        except Exception:
            return None

    def compute_target_url(self, challenge: Dict) -> str:
        """根据赛题target_info生成目标URL"""
        target_info = challenge.get("target_info", {}) or {}
        ip = target_info.get("ip", "127.0.0.1")
        ports = target_info.get("port", []) or []
        port = 80 if 80 in ports else (ports[0] if ports else 80)
        return f"http://{ip}:{port}"

    def safe_terminate(self, proc: subprocess.Popen):
        """安全终止子进程"""
        try:
            if proc.poll() is None:
                proc.terminate()  # 发送SIGTERM，flaghunter会清理并注销Agent
                try:
                    proc.wait(timeout=10)
                except Exception:
                    proc.kill()
        except Exception:
            pass


def main():
    """主函数"""
    # 从环境变量或配置文件获取API_TOKEN
    api_token = config.CONTEST_API_TOKEN
    if not api_token:
        logger.error("请设置环境变量 CONTEST_API_TOKEN")
        sys.exit(1)
    
    # 新增：支持从命令行设置模式（默认 deepseek）
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="deepseek", help="LLM模式（默认 deepseek）")
    args, _ = parser.parse_known_args()
    
    # 创建比赛工具实例（传入 mode）
    contest_hunter = ContestHunter(api_token, mode=args.mode)
    
    # 注册信号处理器
    def signal_handler(signum, frame):
        logger.info("接收到退出信号，正在停止比赛...")
        contest_hunter.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 运行比赛
        contest_hunter.run_contest()
    except Exception as e:
        logger.error(f"比赛运行异常: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        logger.info("比赛结束")


if __name__ == '__main__':
    main()