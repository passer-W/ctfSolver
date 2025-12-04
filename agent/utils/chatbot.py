import sqlite3
from turtle import st
from typing import List, Dict
import uuid
from config import config
from utils.logger import logger
from utils.sql_helper import SQLiteHelper
import openai
from config import config


import re
import requests
import json
import time

def interact_with_server(action_type: str,process_id=None, data: dict = None):
    """
    与服务器进行交互
    :param action_type: 交互类型 ('process_check', 'history_update', 'heartbeat')
    :param data: 发送的数据
    :return: 服务器响应
    """
    try:
        if action_type == "process_check":
            # 检查进程状态，不存在则创建
            response = requests.get(f"{config.SERVER_URL}/api/process/{process_id}/status", timeout=5)
            if response.status_code == 404:
                # 进程不存在，创建新进程
                create_resp = requests.post(
                    f"{config.SERVER_URL}/api/process/{process_id}",
                    json={"addition": None},
                    headers={'Content-Type': 'application/json'},
                    timeout=5
                )
                if create_resp.status_code == 201:
                    # 创建成功，重新获取状态
                    response = requests.get(f"{config.SERVER_URL}/api/process/{process_id}/status", timeout=5)
                else:
                    logger.warn(f"创建进程失败: {create_resp.status_code}")
                    return None
            if response.status_code == 200:
                return response.json()['data']
        
        elif action_type == "history_update":
            # 更新历史记录
            response = requests.post(f"{config.SERVER_URL}/api/process/{process_id}/message",
                                   json={"metadata": data},
                                   headers={'Content-Type': 'application/json'},
                                   timeout=5)
            if response.status_code == 201:
                return response.json()

                
    except requests.exceptions.RequestException as e:
        logger.warn(f"服务器交互失败: {e}")
        return None
    except Exception as e:
        logger.warn(f"服务器交互异常: {e}")
        return None

def check_process_status(process_id):
    """
    检查进程状态，如果是暂停状态则等待
    :return: True if should continue, False if should pause
    """
    if not config.AGENT_ID:
        return True  # 如果没有注册，继续执行
        
    process_status = interact_with_server("process_check", process_id)
    if process_status and process_status.get("status") == "pause":
        logger.info("检测到进程暂停状态，等待恢复...")
        while True:
            time.sleep(5)  # 每5秒检查一次
            process_status = interact_with_server("process_check", process_id)
            if not process_status or process_status.get("status") != "pause":
                logger.info("进程状态恢复，继续执行")
                break
    return True

def generate_sessionid(session_id=""):
    """
    生成或处理会话ID
    :param session_id: 可选的会话ID
    :return: 新的会话ID
    """
    new_session_id = str(uuid.uuid4())
    
    if session_id:
        # 如果提供了session_id，将其作为父会话ID插入
        SQLiteHelper.insert_record("sessions", {
            "session_id": new_session_id,
            "parent_id": session_id
        })
    else:
        # 如果没有提供session_id，只插入新的会话ID
        SQLiteHelper.insert_record("sessions", {
            "session_id": new_session_id,
            "parent_id": None
        })
    
    return new_session_id


def add_message(message: str, session_id:str="", status: str="default"):
    if not session_id:
        session_id = generate_sessionid("")

    check_process_status(session_id)
    SQLiteHelper.insert_record("messages", {
        "session_id": session_id,
        "role": "user",
        "content": message,
        "status": status
    })
    
    # 与服务器交互 - 更新历史记录
    history_data = {
        "agent_id": config.AGENT_ID,
        "session_id": session_id,
        "content": message,
        "timestamp": int(time.time()),
        "type": "user"
    }
    interact_with_server("history_update", session_id, history_data)
    
    return session_id



def chat(prompt: str, session_id: str, status: str="default", _type="action", type="normal", limit=10000) -> str:
    """
    与AI进行对话，并保存对话历史
    :param prompt: 用户输入的提示词
    :param session_id: 会话ID
    :return: AI的回复
    """
    
    # 连接数据库
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    session_ids = [session_id]

    # 获取所有相关的session_id，从父到子排序

    try:
        messages: List[Dict[str, str]] = []
        for s in session_ids:
        # 获取历史消息
            if s != session_id:
                result = SQLiteHelper.execute_query('''
                     SELECT role, content 
                     FROM messages 
                     WHERE session_id = ? and status = 'default' 
                     ORDER BY created_at ASC
                 ''', (s,))
            else:
                result = SQLiteHelper.execute_query('''
                    SELECT role, content 
                    FROM messages 
                    WHERE session_id = ? 
                    ORDER BY created_at ASC
                ''', (s,))
            
            # 构建消息历史
            for role, content in result:

                if len(content) < limit:
                    messages.append({
                        "role": role,
                        "content": content
                    })
                else:
                    messages.append({
                        "role": role,
                        "content": content[:limit] + "...(内容过长，无法全部输出)" if type == "normal" else content
                    })
        
        # 调用OpenAI API获取回复
        client = openai.OpenAI(
            api_key=config.API_KEY if type == "normal" else config.GLM_API_KEY,
            base_url=config.API_URL if type == "normal" else config.GLM_URL
        )
        chat_count = 0
        while True:
            if chat_count > 20:
                ai_response = ""
                token_count = 0
                break
            try:
            
                response = client.chat.completions.create(
                    model=config.API_MODEL_ACTION if type == "normal" else config.GLM_MODEL,
                    messages=[
                        {"role": "system", "content": prompt}
                    ] + messages
                )
                ai_response = response.choices[0].message.content
                token_count = response.usage.total_tokens


                break
            except Exception as e:
                print(e)
                time.sleep(10)
                chat_count += 1

        # 获取AI回复
        # 获取本次对话的token数量
        logger.info(f"本次对话使用token数: {token_count}")

        logger.info(ai_response)

        cursor.execute('''
            INSERT INTO messages (session_id, role, content, status) 
            VALUES (?, ?, ?, ?)
        ''', (session_id, "assistant", ai_response, status))

        conn.commit()

        # 与服务器交互 - 更新历史记录
        history_data = {
            "session_id": session_id,
            "content": ai_response,
            "timestamp": int(time.time()),
            "token_count": token_count,
            "type": _type
        }

        interact_with_server("history_update", session_id, history_data)
        

        return ai_response
        
    except Exception as e:
        logger.warn(e)
        raise e
        return str(e)
        
    finally:
        conn.close()

def update_message_status(message: str, session_id: str) -> str:
    """
    更新消息状态为临时状态
    :param message: 消息内容
    :param session_id: 会话ID
    :return: 会话ID
    """
    # 使用SQLiteHelper执行更新操作并确保提交事务
    conn = sqlite3.connect(config.DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE messages 
            SET status = 'temp' 
            WHERE session_id = ? AND content = ?
        ''', (session_id, message))
        conn.commit()
    finally:
        conn.close()
    return session_id
