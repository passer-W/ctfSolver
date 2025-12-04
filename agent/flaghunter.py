import asyncio
import json
import os
import subprocess
import traceback
import uuid
import requests
import xml.etree.ElementTree as ET
import signal
import sys
import time

from addons import request
from agents.explorer import explore_page
from agents.poc import Scanner, Flagger
from agents.scanner import vuln_scan
from config import config
from utils import page_helper, flagUtil
from utils.logger import logger
from utils.agent_manager import agent_manager


config.init_db()
config.flush_key()

class FlagHunter():
    def __init__(self, url, description):
        self.url = url
        self.description = description
        config.CTF_URL = self.url
        config.CTF_DESC = f"目标URL：{self.url}\n目标描述：{self.description}"
        self.tasks = {}  # 所有action
        self.current_tasks = []  # 当前深度的action
        self.depth = 0
        self.task_id = str(uuid.uuid4())
        config.TASK_ID = self.task_id
        self.task_path = str(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"tasks/{self.task_id}"))
        self.task_page_path = f"{self.task_path}/pages/"
        if not os.path.exists(self.task_page_path):
            os.makedirs(self.task_page_path)
        self.key_file = f"{self.task_path}/key.txt"
        self.key_simple_file = f"{self.task_path}/key-simple.txt"
        self.vuln_file = f"{self.task_path}/vuln.txt"
        self.xray_result_file = f"{self.task_path}/result.json"

        self.explorer_pages = []
        self.detect_pages = []
        self.vuln_pages = []
        if not os.path.exists(self.key_file):
            open(self.key_file, "w").close()
        if not os.path.exists(self.key_simple_file):
            open(self.key_simple_file, "w").close()
        if not os.path.exists(self.vuln_file):
            with open(self.vuln_file, "w") as f:
                f.write('')

    async def explorer_page(self):
        try:
            # 发送开始探索页面的消息（running状态）
            explore_message = None


            pages = [{'name':'初始页面'}]
            discovered_pages = []  # 用于收集发现的页面

            while pages:
                new_pages = []

                # if self.vuln_pages and self.explorer_pages == self.detect_pages:
                #     # 根据漏洞重新探索
                #     logger.info("发现漏洞，重新进行页面探索")
                #     if agent_manager.current_task_id:
                #         agent_manager.send_pure_message_with_status(
                #             agent_manager.current_task_id,
                #             "🔄 发现漏洞，重新进行页面探索",
                #             "finish"
                #         )
                #     for i in range(len(self.vuln_pages)):
                #         self.vuln_pages[i]['vuln'] = True
                #     pages.extend(self.vuln_pages)
                #     self.vuln_pages = []

                for pp in pages:
                    explore_message = agent_manager.send_pure_message_with_status(
                        agent_manager.current_task_id,
                        f"🔍 开始探索页面: {pp['name']}",
                        "running"
                    )
                    session_id = explore_message['id']
                    try:
                        step_pages = explore_page(pp, key=open(self.key_file, "r").read(), vuln=open(self.vuln_file, "r").read(), session_id=session_id)
                    except Exception as e:
                        traceback.print_exc()
                        break
                    for p in step_pages:
                        logger.info(f"探索到新页面：{p['name']} {p['response']['url']} ，线索：{p['key']}")
                        if p["key"]:
                            with open(self.key_simple_file, "a+") as f:
                                f.write(str(p['name']) + f" {p['response']['url']} 发现线索：" + str(p['key']) + "\n")
                            with open(self.key_file, "a+") as f:
                                f.write(str(p['name']) + f" 请求：{p['request']} 发现线索：" + str(p['key']) + "\n")
                        page_path = f"{self.task_page_path}/{p['name']}.json"
                        p['path'] = page_path
                        if os.path.exists(page_path):
                            page_path = f"{self.task_page_path}/{p['name']}-{uuid.uuid4()}.json"
                        with open(page_path, "w") as pf:
                            pf.write(json.dumps(p))
                        if "path" in pp:
                            if not page_helper.get_parent_page(p['id']):
                                page_helper.insert_page_parent(pp['path'], p['id'])

                        # 向服务器报告发现的页面
                        if agent_manager.current_task_id:
                            page_data = {
                                "name": p['name'],
                                "request": json.dumps(p.get('request', {})),
                                "response": json.dumps(p.get('response', {})),
                                "description": p.get('description', ''),
                                "key": p.get('key', '')
                            }
                            # 直接调用同步方法，不使用await
                            created_page = agent_manager.create_page(agent_manager.current_task_id, page_data)

                            # 收集页面信息用于发送页面消息
                            page_info = {
                                "page_id": created_page.get('id', str(uuid.uuid4())) if created_page else str(uuid.uuid4()),
                                "url": p['response'].get('url', ''),
                                "status": p['response'].get('status', 200),
                                "responseTime": p['response'].get('response_time', 0),
                                "pageType": p.get('name', ''),
                                "description": p.get('description', '') or p.get('key', '')
                            }
                            discovered_pages.append(page_info)
                    agent_manager.update_pure_message_status(
                        explore_message.get('id'),
                        "finish",
                        f"✅ {pp['name']} 页面探索完成，共发现 {len(step_pages)} 个新页面"
                    )
                    new_pages.extend(step_pages)
                    self.explorer_pages.extend(step_pages)
                    # 更新全局页面列表供心跳使用
                    config.EXPLORED_PAGES = [p['id'] for p in self.explorer_pages]

                # 如果发现了新页面，发送页面消息
                if discovered_pages and agent_manager.current_task_id:
                    agent_manager.send_page_message(
                        agent_manager.current_task_id,
                        discovered_pages,
                        f"📄 发现 {len(discovered_pages)} 个新页面"
                    )
                    discovered_pages = []  # 清空已发送的页面

                pages = new_pages

                await asyncio.sleep(1)


                for p in self.explorer_pages:
                    if not p['id'] in config.EXPLORED_PAGES:
                        pages.append(p)





                if config.FLAG:
                    break
        except Exception as e:
            traceback.print_exc()
            raise e


    def poc_scan(self, page):
        scanner = Scanner()
        poc_results = scanner.poc_scan(page, key=open(self.key_simple_file, "r").read(), task_id=self.task_id)

        # 如果POC扫描发现漏洞，记录结果
        if poc_results:
            for poc_result in poc_results.values():
                if poc_result.get('vulnerable'):
                    logger.info(f"POC扫描发现漏洞: {poc_result.get('vuln_name', 'Unknown')}")
                    with open(self.vuln_file, "a+") as f:
                        f.write(
                            f"{page['name']} POC检测出漏洞：{poc_result.get('vuln_name', 'Unknown')} - {poc_result.get('description', '')}\n")
                    if config.NEED_FLAG:
                        poc_message = agent_manager.send_pure_message_with_status(
                            agent_manager.current_task_id,
                            f"🔍 开始深入利用漏洞: {poc_result['vuln_name']}",
                            "running"
                        )

                        try:
                            # 创建Flagger实例并调用hunt_flag方法
                            flagger = Flagger()
                            hunt_result = flagger.hunt_flag(
                                poc_result['poc_file'],
                                poc_result['request'],
                                poc_result['response'],
                                poc_message['id']
                            )

                            # 处理hunt_flag的返回结果
                            if hunt_result:
                                summary = hunt_result
                                vuln_status = summary.get('vuln', 'False')
                                find_flag = summary.get('findFlag', 'False')
                                desc = summary.get('desc', '')
                                flag_content = summary.get('flag', '')

                                # 构建结果消息
                                if find_flag == 'True' and flag_content:
                                    # 发现了flag
                                    result_message = f"🎉 利用{poc_result['vuln_name']}漏洞成功获取flag: {flag_content}"

                                    # 更新消息状态为成功
                                    agent_manager.update_pure_message_status(
                                        poc_message['id'],
                                        "finish",
                                        result_message
                                    )
                                    flagUtil.set_flag(flag_content)


                                elif vuln_status == 'True':
                                    # 确认存在漏洞但未找到flag
                                    result_message = f"✅ 确认漏洞存在，但未发现flag\n\n漏洞利用详情:\n{desc}"

                                    # 更新消息状态
                                    agent_manager.update_pure_message_status(
                                        poc_message['id'],
                                        "finish",
                                        result_message
                                    )
                                else:
                                    # 漏洞利用失败
                                    result_message = f"❌ 漏洞利用失败\n\n详情:\n{desc}"

                                    # 更新消息状态
                                    agent_manager.update_pure_message_status(
                                        poc_message['id'],
                                        "finish",
                                        result_message
                                    )
                            else:
                                # 没有返回有效结果
                                agent_manager.update_pure_message_status(
                                    poc_message['id'],
                                    "finish",
                                    f"❌ 漏洞利用过程异常，未获取到有效结果"
                                )

                        except Exception as e:
                            traceback.print_exc()
                            logger.error(f"漏洞利用过程中出错: {str(e)}")
                            # 更新消息状态为失败
                            agent_manager.update_pure_message_status(
                                poc_message['id'],
                                "finish",
                                f"❌ 漏洞利用过程中发生错误: {str(e)}"
                            )
                            return 0
        return len(poc_results)

    def llm_scan(self, page):
        results = vuln_scan(page, key=open(self.key_file, "r").read(), simple_key=open(self.key_simple_file, "r").read(), explorer_pages=self.explorer_pages,
                            task_id=self.task_id)
        if results:
            print(results)
            self.vuln_pages.append(page)
            with open(self.vuln_file, "a+") as f:
                vuln_info = '\n'.join([str(i) for i in results])
                f.write(f"{page['name']}检测出漏洞：\n{vuln_info}\n")

            # 向服务器报告发现的漏洞
            if agent_manager.current_task_id:
                vulnerabilities = []
                for result in results:
                    if result['vuln'] == 'True':
                        vuln_data = {
                            "vuln_type": result.get('vuln_type', 'Unknown'),
                            "description": result.get('desc', ''),
                            "request": json.dumps(page.get('request', {})),
                            "response": json.dumps(page.get('response', {}))
                        }
                        # 直接调用同步方法，不使用asyncio.create_task
                        created_vuln = agent_manager.create_vulnerability(agent_manager.current_task_id, vuln_data)

                        # 收集漏洞信息用于发送漏洞消息
                        if created_vuln:
                            vuln_info = {
                                "id": created_vuln.get('id'),
                                "type": result.get('vuln_type', 'Unknown'),
                                "vuln_type": result.get('vuln_type', 'Unknown'),
                                "url": page['response'].get('url', ''),
                                "description": result.get('desc', ''),
                                "discovered_at": created_vuln.get('discovered_at')
                            }
                            vulnerabilities.append(vuln_info)

                # 发送漏洞发现消息
                if vulnerabilities:
                    agent_manager.send_vulnerability_message(
                        agent_manager.current_task_id,
                        vulnerabilities,
                        f"🚨 在页面 {page['name']} 发现 {len(vulnerabilities)} 个漏洞"
                    )

                    return len(vulnerabilities)

                else:
                    agent_manager.send_pure_message_with_status(
                        agent_manager.current_task_id,
                        f"✅ 在页面 {page['name']} 未发现漏洞",
                        "finish"
                    )
                    return 0


        return 0

    async def detect_page(self):
        # 发送开始漏洞检测的消息（running状态）
        detect_message = None



        while True:
            for p in self.explorer_pages:
                vuln_count = 0
                if not p in self.detect_pages:
                    if agent_manager.current_task_id:
                        detect_message = agent_manager.send_pure_message_with_status(
                            agent_manager.current_task_id,
                            f"🔍 开始对 {p['name']} 页面进行漏洞检测",
                            "running"
                        )
                    logger.info(f"检测页面：{p['name']}")
                    if p['response']['status'] not in config.IGNORE_STATUS_LIST:
                        vuln_count = 0
                        vuln_count += self.poc_scan(p)
                        if not config.FLAG or not config.NEED_FLAG:
                            vuln_count += self.llm_scan(p)
                        if vuln_count:
                            self.new_vuln = True
                    self.detect_pages.append(p)
                # 漏洞检测完成，更新消息状态为finish
                if detect_message and agent_manager.current_task_id:
                    agent_manager.update_pure_message_status(
                        detect_message.get('id'),
                        "finish",
                        f"✅ {p['name']}页面漏洞检测完成，发现{vuln_count}个漏洞"
                    )
                if config.FLAG:
                    flagUtil.submit_flag()
            await asyncio.sleep(1)



    def hunt(self):
        logger.info(f"开始ctf夺旗任务，id：{self.task_id}")
        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # 发送任务开始消息（running状态）
        start_message = None
        if agent_manager.current_task_id:
            start_message = agent_manager.send_pure_message_with_status(
                agent_manager.current_task_id,
                f"🚀 CTF夺旗任务开始\n目标: {self.url}\n描述: {self.description}",
                "finish"
            )

        try:
            # 创建任务
            tasks = [
                # loop.create_task(self.check_xray_result()),
                loop.create_task(self.explorer_page()),
                loop.create_task(self.detect_page()),
            ]

            # 运行任务直到完成
            loop.run_until_complete(asyncio.gather(*tasks))

        except Exception as e:
            pass

        finally:
            # 清理事件循环
            loop.close()
            asyncio.set_event_loop(None)

            agent_manager.update_task_status(agent_manager.current_task_id, status="finished", flag=config.FLAG)

            # 任务完成，更新开始消息状态为finish
            if start_message and agent_manager.current_task_id:
                agent_manager.update_pure_message_status(
                    start_message.get('id'),
                    "finish",
                    f"✅ CTF夺旗任务完成\n目标: {self.url}\n发现页面: {len(self.explorer_pages)}个\n发现漏洞: {len(self.vuln_pages)}个"
                )

            for m in config.messages:
                agent_manager.update_pure_message_status(
                    m,
                    "finish",
                    f"✅ CTF夺旗任务已完成"
                )
                

            # 发送任务完成总结
            if agent_manager.current_task_id:
                summary_data = {
                    "vuln": len(self.vuln_pages) > 0,
                    "desc": f"扫描完成。发现 {len(self.explorer_pages)} 个页面，{len(self.vuln_pages)} 个漏洞页面。",
                    "findFlag": bool(config.FLAG),
                    "flag": config.FLAG or "",
                    "needDeep": len(self.vuln_pages) > 0 and not config.FLAG
                }

                agent_manager.send_summary_message(
                    agent_manager.current_task_id,
                    summary_data,
                    "📊 CTF夺旗任务完成"
                )




def main(name=None, challenge_code=None, api_token=None, mode=None):
    if name:
        config.NAME = name
    if challenge_code:
        config.CHALLENGE_CODE = challenge_code
    if api_token:
        config.API_TOKEN = api_token

    if mode:
        if mode == 'deepseek':
            config.API_URL = config.DEEPSEEK_API_URL
            config.API_KEY = config.DEEPSEEK_API_KEY
            config.API_MODEL_ACTION = config.DEEPSEEK_API_MODEL_ACTION
        elif mode == 'tencent':
            config.API_URL = config.TENCENT_API_URL
            config.API_KEY = config.TENCENT_API_KEY
            config.API_MODEL_ACTION = config.TENCENT_API_MODEL_ACTION
        elif mode == "silcon":
            config.API_URL = config.SILCON_API_URL
            config.API_KEY = config.SILCON_API_KEY
            config.API_MODEL_ACTION = config.SILCON_API_MODEL_ACTION
        else:
            config.API_URL = config.TENCENT_API_URL
            config.API_KEY = config.TENCENT_API_RANDOM_KEY
            config.API_MODEL_ACTION = config.TENCENT_API_MODEL_ACTION

    """主函数，处理agent注册和心跳"""
    logger.info("ctfSolver启动中...")

    # 注册信号处理器
    def signal_handler(signum, frame):
        logger.info("接收到退出信号，正在清理...")
        cleanup()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 启动Agent管理器
    logger.info("正在启动Agent管理器...")
    if agent_manager.start():
        logger.info("Agent管理器启动成功")

        try:
            # 等待任务完成
            logger.info("Agent已就绪，等待任务...")
            # 保持主循环运行
            while agent_manager.is_running:
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("收到中断信号")
        except Exception as e:
            logger.error(f"主循环异常: {str(e)}")
        finally:
            cleanup()
    else:
        logger.error("Agent管理器启动失败，程序退出")
        sys.exit(1)


def cleanup():
    """清理函数"""
    logger.info("正在清理资源...")
    agent_manager.stop()
    logger.info("清理完成")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", help="Agent name", default="ctfSolver")
    parser.add_argument("--challengecode", help="Challenge code", default="")
    parser.add_argument("--apitoken", help="Api Token", default="")
    parser.add_argument("--mode", help="Api Token", default="random")

    args = parser.parse_args()
    try:
        # 运行主函数
        main(name=args.name, challenge_code=args.challengecode, api_token=args.apitoken, mode=args.mode)
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序异常退出: {str(e)}")

