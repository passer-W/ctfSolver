#!/usr/bin/env python3
"""
测试Agent与Chatbot交互的脚本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.chatbot import add_message, chat, generate_sessionid
from utils.logger import logger
from config import config

def test_simple_qa():
    """简单的问答测试"""
    print("\n" + "=" * 60)
    print("开始简单问答测试")
    print("=" * 60)

    session_id = generate_sessionid()

    # 简单的技术问题
    questions = [
        f"分析js文件: {open('test.js', 'r').read()}， 提取其中和后端交互的接口完整说明",
    ]

    for question in questions:
        print(f"\n问题: {question[:100]}")
        print("-" * 40)

        try:
            add_message(question, session_id)

            prompt = "你是一个网络安全专家，请简洁明了地回答用户的技术问题。"
            response = chat(prompt, session_id, type="normal")

            print("回答:")
            print(response)

        except Exception as e:
            print(f"错误: {e}")


if __name__ == '__main__':
    test_simple_qa()