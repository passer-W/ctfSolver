import json
import os

from utils.sql_helper import SQLiteHelper


def insert_page_parent(parent_path: str, page_id: str):
    """插入页面的父子关系到数据库"""
    SQLiteHelper.insert_record("pages", {
        "parent_path": parent_path,
        "id": page_id
    })

def get_parent_page(page_id: str) -> dict:
    """根据页面ID获取其父页面信息
    
    Args:
        page_id: 页面ID
        
    Returns:
        父页面信息的字典，如果没有找到返回None
    """
    sql = """
        SELECT parent_path
        FROM pages WHERE id = ?
    """
    result = SQLiteHelper.fetch_one(sql, (page_id,))
    if result:
        page = json.loads(open(result[0], "r").read())
        return page
    else:
        return {}


def get_pages_info(pages):
    pages_info = ""
    for p in pages:
        pages_info += f"""页面 {p['name']}，id：{p['id']}：\n页面描述：{p.get('description', '')}\n页面请求：{p.get('request')}\n"""
    return pages_info