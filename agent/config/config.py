import os
import sqlite3

from utils.logger import logger
import uuid
import os
import random

API_KEYS = []

DEEPSEEK_API_URL = "https://api.deepseek.com"
DEEPSEEK_API_KEY = ""
DEEPSEEK_API_MODEL_ACTION = "deepseek-chat"

TENCENT_API_URL = "https://api.lkeap.cloud.tencent.com/v1"
TENCENT_API_KEY = ""
TENCENT_API_MODEL_ACTION = "deepseek-v3.1-terminus"
TENCENT_API_RANDOM_KEY = random.choice(API_KEYS)


SILCON_API_URL = "https://api.siliconflow.cn/v1"
SILCON_API_KEY = ""
SILCON_API_MODEL_ACTION = "Pro/deepseek-ai/DeepSeek-V3.1-Terminus"

# API配置
API_URL = "https://api.deepseek.com"
API_KEY = ""
API_MODEL_ACTION = "deepseek-chat"

CONTEST_API_TOKEN = ""

GLM_URL = "https://open.bigmodel.cn/api/paas/v4"
GLM_API_KEY = ""
GLM_MODEL = "glm-4-long"

NAME = "ctfSolver"
CHALLENGE_CODE = ""

# Server配置
SERVER_URL = "http://39.98.204.142:5000"  # 后端服务器地址
AGENT_VERSION = "1.0.0"  # Agent版本
HEARTBEAT_INTERVAL = 30  # 心跳间隔（秒）
AGENT_CAPABILITIES = ["web_scan", "vuln_detect", "flag_search", "page_explore"]  # Agent能力

# SQLite数据库配置
BASE_PATH = str(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_PATH, "chat.db")
INIT_SQL = os.path.join(BASE_PATH, "init.sql")
ADDON_README_PATH = os.path.join(BASE_PATH, "addons.txt")
TEMP_PATH = os.path.join(BASE_PATH, "temp/")

POC_PATH = os.path.join(BASE_PATH, "pocs/")

BASE_URL = "http://10.0.0.6:8000"

HUNTER = None

FORMS = {}

EXPLORE_URLS = []

# CTF任务配置
CTF_URL = ""
CTF_DESC = ""
TARGET = ""  # 添加TARGET配置
DESCRIPTION = ""  # 添加DESCRIPTION配置
TASK_PATH = os.path.join(os.path.dirname(BASE_PATH), "tasks")  # 任务存储路径

MAX_COUNT = 4
KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "key.txt")
ADDON_PATH = os.path.join(BASE_PATH, "addons/")
KNOWLEGDE_PATH = os.path.join(BASE_PATH, "knowledge/")
PAYLOAD_PATH = os.path.join(BASE_PATH, "payload/")

# Agent相关配置
AGENT_ID = None  # 将在注册时获得
AGENT_STATUS = "idle"  # Agent状态：idle, running, error, exploring, detecting

TASK_ID = ""
EXPLORED_PAGES = []
EXPLORED_PAGE_RESPONSES = []
NEED_FLAG = True
FLAG = ""
IGNORE_STATUS_LIST = [404, 405]
WRONG_STATUS_LIST = [405]

XRAY_PROXY = "127.0.0.1:7783"
XRAY_CMD = f"cd {BASE_PATH} && ./xray webscan --listen {XRAY_PROXY} --json-output #result_file#"
PYTHON_CMD = "python3"

messages = []


# 初始化数据库
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 读取SQL文件并按分号分割为单独的语句
    with open(INIT_SQL, "r") as sql_file:
        sql_statements = sql_file.read().split(';')

    # 执行每个非空SQL语句
    for statement in sql_statements:
        if statement.strip():
            cursor.execute(statement)

    conn.commit()
    conn.close()
    logger.info(f"数据库已初始化，路径：{DB_PATH}")


def flush_key():
    open(KEY_FILE, "w").close()


def write_key(key):
    with open(KEY_FILE, "a") as f:
        f.write(key + "\n")


def read_keys():
    if not os.path.exists(KEY_FILE):
        flush_key()
    return open(KEY_FILE, "r").read()


def get_addon(tool):
    return open(f"{ADDON_PATH}/{tool}.txt").read()


def get_knowledge(knowledge):
    knowledge_base_path = f"{KNOWLEGDE_PATH}/{knowledge}"

    knowledge_files = []
    # 遍历knowledge目录下的所有文件
    for filename in os.listdir(knowledge_base_path):
        file_path = os.path.join(knowledge_base_path, filename)
        if os.path.isfile(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
                lines = content.split('\n')
                first_line = lines[0] if lines else ''

                # 为每个文件生成唯一ID
                file_id = str(uuid.uuid4())
                knowledge_files.append({
                    "id": file_id,
                    "desc": first_line,
                    "all": content
                })
    return knowledge_files


def get_payload(payload_type):
    payload_file = f"{PAYLOAD_PATH}/{payload_type.lower()}.txt"
    if os.path.exists(payload_file):
        return open(payload_file, "r").read().split("\n")
    return []


