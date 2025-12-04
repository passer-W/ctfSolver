#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import sqlite3
import argparse
from typing import List

import tqdm

from config.config import DB_PATH

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_sessions(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    sql = """
    SELECT id, session_id, parent_id, created_at
    FROM sessions
    ORDER BY created_at ASC, id ASC
    """
    cur = conn.cursor()
    cur.execute(sql)
    return cur.fetchall()

def fetch_messages(conn: sqlite3.Connection, session_id: str) -> List[sqlite3.Row]:
    sql = """
    SELECT id, role, content, status, created_at
    FROM messages
    WHERE session_id = ? AND status = 'default'
    ORDER BY created_at ASC, id ASC
    """
    cur = conn.cursor()
    cur.execute(sql, (session_id,))
    return cur.fetchall()

def pair_messages(rows: List[sqlite3.Row]) -> List[dict]:
    """按顺序将消息配对：user -> assistant"""
    pairs = []
    pending_user = None
    for m in rows:
        role = (m["role"] or "").strip()
        content = m["content"] or ""
        if role == "user":
            pending_user = content
        elif role == "assistant":
            if pending_user is not None:
                pairs.append({"user": pending_user, "assistant": content})
                pending_user = None
            else:
                # 孤立的assistant，跳过
                continue
        else:
            # 其他角色（目前不会有system），跳过
            continue
    return pairs

def export_messages(output_path: str, system_text: str):
    conn = get_connection()
    try:
        sessions = fetch_sessions(conn)
        if not sessions:
            print(f"[INFO] sessions 表为空（DB: {DB_PATH}），不生成文件。")
            return

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            for s in tqdm.tqdm(sessions):
                sid = s["session_id"]
                rows = fetch_messages(conn, sid)
                pairs = pair_messages(rows)

                for p in pairs:
                    obj = {
                        "messages": [
                            {"role": "system", "content": system_text},
                            {"role": "user", "content": p["user"]},
                            {"role": "assistant", "content": p["assistant"]},
                        ]
                    }
                    f.write(json.dumps(obj, ensure_ascii=False) + "\n")

        print(f"[OK] 导出完成，共 {sum(len(pair_messages(fetch_messages(conn, s['session_id'])) ) for s in sessions)} 行，输出文件：{output_path}")
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="导出 chat.db 的 messages 对话为按对的 JSON Lines")
    default_output = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "messages.json"))
    parser.add_argument("--output", default=default_output, help="输出文件路径（默认项目根目录 messages.json）")
    parser.add_argument("--system", default="你是网络安全专家", help="插入的 system 角色内容（默认：你是消防系统专家）")
    args = parser.parse_args()

    export_messages(args.output, args.system)

if __name__ == "__main__":
    main()