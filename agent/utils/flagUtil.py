from utils.agent_manager import agent_manager
from utils.logger import logger
from config import config
import requests
import time


class FlagSubmissionException(Exception):
    """Flag提交完成异常，用于中止当前任务而不终止整个程序"""
    pass


def set_flag(test_flag):

    if not config.CHALLENGE_CODE:
        black_list = ['SQLi_']
    else:
        black_list = []
    if len(test_flag) < 10:
        return
    for b in black_list:
        if b in test_flag:
            return

    success_flag = ""
    test_flags = [test_flag, test_flag.replace("flag", "FLAG")] if config.CHALLENGE_CODE and "flag" in test_flag else [test_flag]
    for flag in test_flags:
        # 如果提供了 CHALLENGE_CODE，则调用 /api/v1/answer 接口提交答案
        if config.CHALLENGE_CODE:
            url = f"{config.BASE_URL}/api/v1/answer"
            headers = {
                "accept": "application/json",
                "Authorization": f"Bearer {config.CONTEST_API_TOKEN}",
                "Content-Type": "application/json"
            }
            payload = {
                "challenge_code": config.CHALLENGE_CODE,
                "answer": flag
            }
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("correct"):
                        success_flag = flag
                        logger.info(f"Flag 提交正确，获得积分: {data.get('earned_points', 0)}")
                        if data.get("is_solved"):
                            logger.info("该题目已解决，重复提交")
                    else:
                        logger.warning(f"Flag 提交错误，未获得积分")
                elif resp.status_code == 429:
                    logger.warning(f"提交过于频繁，触发限流，等待后重试: {resp.text}")
                    time.sleep(2)
                    resp = requests.post(url, json=payload, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("correct"):
                            success_flag = flag
                            logger.info(f"Flag 提交正确，获得积分: {data.get('earned_points', 0)}")
                            if data.get("is_solved"):
                                logger.info("该题目已解决，重复提交")
                        else:
                            logger.warning(f"Flag 提交错误，未获得积分")
                            return
                    else:
                        logger.warning(f"重试后提交答案接口仍返回异常: {resp.status_code} {resp.text}")
                else:
                    logger.warning(f"提交答案接口返回异常: {resp.status_code} {resp.text}")
            except Exception as e:
                logger.error(f"调用提交答案接口失败: {str(e)}")
        else:
            success_flag = flag
    if success_flag:
        config.FLAG = success_flag




def submit_flag():
    """提交发现的flag"""
    logger.info(f"发现flag: {config.FLAG}")



    # 如果提供了agent_manager和task_id，则提交到后端
    try:
        result = agent_manager.create_flag(agent_manager.current_task_id, config.FLAG)
        if result:
            logger.info("Flag已成功提交到后端")
        else:
            logger.warning("Flag提交到后端失败")
        
        if config.CHALLENGE_CODE:
            url = f"{config.BASE_URL}/api/v1/answer"
            headers = {
                "accept": "application/json",
                "Authorization": f"Bearer {config.CONTEST_API_TOKEN}",
                "Content-Type": "application/json"
            }
            payload = {
                "challenge_code": config.CHALLENGE_CODE,
                "answer": config.FLAG
            }
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("correct"):
                        logger.info(f"Flag 提交正确，获得积分: {data.get('earned_points', 0)}")
                        if data.get("is_solved"):
                            logger.info("该题目已解决，重复提交")
                    else:
                        logger.warning(f"Flag 提交错误，未获得积分")
                        return
                elif resp.status_code == 429:
                    logger.warning(f"提交过于频繁，触发限流，等待后重试: {resp.text}")
                    # 简单等待1秒后重试一次
                    time.sleep(1)
                    try:
                        resp = requests.post(url, json=payload, headers=headers, timeout=10)
                        if resp.status_code == 200:
                            data = resp.json()
                            if data.get("correct"):
                                logger.info(f"Flag 提交正确，获得积分: {data.get('earned_points', 0)}")
                                if data.get("is_solved"):
                                    logger.info("该题目已解决，重复提交")
                            else:
                                logger.warning(f"Flag 提交错误，未获得积分")
                                return
                        else:
                            logger.warning(f"重试后提交答案接口仍返回异常: {resp.status_code} {resp.text}")
                    except Exception as e:
                        logger.error(f"重试调用提交答案接口失败: {str(e)}")
                else:
                    logger.warning(f"提交答案接口返回异常: {resp.status_code} {resp.text}")
            except Exception as e:
                logger.error(f"调用提交答案接口失败: {str(e)}")

    except Exception as e:
        logger.error(f"提交Flag时发生异常: {str(e)}")
    
    # 抛出异常来中止当前任务，而不是退出整个程序
    raise FlagSubmissionException("Flag已提交，中止当前任务")
