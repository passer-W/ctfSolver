from config import config
from utils import page_helper
from utils.chatbot import add_message, chat
from utils.logger import logger
import xmltodict
import re
import traceback

prompt = """
你是一个ctf题目解决者，你需要根据当前请求与响应包和历史获取的关键信息来生成漏洞检测的思路。

你需要一步步推理与得出最终的检测思路，推理步骤如下：
1）这是一个什么请求，传入了哪些信息，获取了哪些信息
2）当前请求的哪些功能点可能存在漏洞
3）对于xx漏洞的基础测试载荷为xx，xx，xx；。。。。
4）对于这些漏洞生成xml格式的最终检测思路：
<solutions>
    <solution>
        <vuln>漏洞类型，为字母缩写，支持：IDOR（越权）、SSTI、XSS、SQLI、UPLOAD（文件上传漏洞）、LFI（本地文件包含）、CMD（命令注入）、OTHER</vuln>
        <desc>利用方式的自然语言描述，不需要指明要检测的参数，也不可以描述载荷，概括性介绍利用方法即可</desc>
    </solution>
    ...
</solutions>

注意：
1. 请尽量发挥创意，发掘更多可能的solution，请仔细分析当前请求，尽量发现所有可能存在的漏洞点
2. 不要进行常规漏洞检测思路，如框架、备份文件漏洞等
3. OTHER类型漏洞可以提出多种检测思路，尽可能多地提出检测思路
4. 文件上传请求需要生成UPLOAD的solution
5. OTHER类型漏洞有：SSRF、XXE、代码注入、反序列化等，也可以针对api进行一些漏洞的利用
6. JWT令牌漏洞也属于IDOR漏洞
7. 对于Python系统，可以进行SSTI漏洞尝试
8. 对于不同页面或端点的同一漏洞检测思路分开给出

CTF题目描述：
{CTF_DESC}
"""

message_template = """
当前请求信息如下：
请求：
{request}

响应：
{response}

当前关键信息：
{key}
"""


def parse_solutions(response):
    solutions = []
    try:
        solution_list = list(re.findall(r"<solution>(.*?)</solution>", response, re.DOTALL))
        for i in range(len(solution_list)):
            try:

                vuln = re.findall('<vuln>(.*?)</vuln>', solution_list[i], re.DOTALL)[0]

                description = re.findall('<desc>(.*?)</desc>', solution_list[i], re.DOTALL)[0]

                if not "缓冲区" in description and not "溢出" in description:

                    solutions.append({
                        'vuln': vuln,
                        'desc': description,
                    })
            except:
                pass

    except Exception as e:
        traceback.print_exc()
        logger.warn(e)
        pass
    return solutions

def get_solutions(page, key, session_id):
    """
    漏洞扫描
    :param page: 页面信息
    :return: 漏洞检测思路
    """
    # 构建提示词
    # 调用OpenAI API获取回复
    add_message(message_template.format(key=key, request=page["request"], response=page["response"]), session_id=session_id)
    response = chat(prompt.format(CTF_DESC=config.CTF_DESC), session_id=session_id)
    logger.info(f"{page['name']} 获取漏洞检测思路：{response}")
    # 解析漏洞检测思路

    solutions = parse_solutions(response)
    return solutions
