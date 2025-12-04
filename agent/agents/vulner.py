# 漏洞利用智能体

from re import S
from config import config
from utils import chatbot
import xmltodict
import re
from addons import request

prompt_template = """
你是一个漏洞利用专家，我会给你一个页面请求和漏洞载荷，格式如下：
<request>页面请求，json格式</request>
<vuln>漏洞类型</vuln>
<desc>漏洞描述，自然语言，详细描述了漏洞需要用到的载荷<desc>

你需要调用请求工具来完成漏洞利用，调用方式如下：
<request>
{request_desc}
</request>
当漏洞利用完成后，如下总结：
<summary>
对当前漏洞利用情况与结果的总结
</summary>
"""

message_template = """
当前漏洞如下：
<request>{request}</request>
<vuln>{vuln}</vuln>
<desc>{desc}</desc>

你需要完成的漏洞利用：
{message}

请你进行漏洞利用
"""

def exploit_vuln(request, vuln, desc, message):
    prompt = prompt_template.format(request_desc=config.get_addon("request"))
    session_id = chatbot.add_message(message=message_template.format(request=request, vuln=vuln, desc=desc, message=message))
    response = chatbot.chat(prompt=prompt, session_id=session_id)
    while True:
        request_xml = re.search(r"(<request>.*?</request>)", response, re.DOTALL)
        summary_xml = re.search(r"(<summary>.*?</summary>)", response, re.DOTALL)
        if request_xml:
            request_json = xmltodict.parse(request_xml.group(1))["request"]
            result = request.run(request_json)
            message = f"请求响应：{result}"
            chatbot.add_message(message=message, session_id=session_id)
        elif summary_xml:
            summary = xmltodict.parse(summary_xml.group(1))["summary"]
            return summary
