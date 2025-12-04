import re

import xmltodict

from agents.executor import execute_tool
from config import config
from utils import page_helper
from utils.chatbot import add_message, chat

from addons import request

prompt_template = """
你是一个漏洞挖掘大师，你可以根据历史使用的工具链和网页响应信息来构造精妙的参数绕过服务端的某些限制，漏洞类型不限于XSS、XXE、SSTI等，绕过的可能是服务端过滤、WAF或RASP等拦截器。
我会提供给你一次请求的请求包和响应包及可能的分析，你需要识别参数和漏洞类型并给出绕过方案，你可以调用网络请求来实现验证。
你必须遵循以下方式进行绕过：
    1）SSTI漏洞，如果对{{进行拦截，需要先不传入{{进行测试，比如如果原始载荷是{{a*b}}被拦截，可以先传入a*b，观察页面是否返回特定结果（与a*b相关，并不一定是直接返回，可能是出现a*b相关的数据，可以进一步分析确认），以确定后端的配置，先从1*1开始
    同时，一些常见的绕过策略有：{绕过：(self.__init__.__globals__.__builtins__.__import__('os').popen('ls').read())
注意：
1. 你需要按照以下格式进行推理生成绕过方案：
1）本次请求的请求包中xx参数可能存在xx漏洞，根据提示信息发现存在xx限制
2）xx限制可以通过xx、xx、xx方式绕过，我将依次尝试
3）我此次构造的参数载荷为xxx，我需要写一个python脚本来验证是否存在xx漏洞（不仅要获取响应，还需要有判断漏洞是否存在的判断语句，最后将所有结果打印）：
<tool>
    <name>run_python</name>
    <value>
        需要执行的python代码
    </value>
</tool>
4）请告诉我这次代码执行的结果
2. 你可以进行多轮绕过，请根据前几轮次的结果综合分析接下来选择的绕过策略
3. 当你认为绕过成功后，请进行总结，总结格式如下：
<summary>
    <type>简述绕过的方式</type>
    <payload>绕过的载荷</payload>
</summary>
4. 当你认为当前请求没有必要继续构造绕过，请返回如下总结：
<summary>
    <type>没有绕过的原因</type>
    <payload>尝试过但没有成功的载荷</payload>
</summary>
5. 必须严格遵守xml规范给出相关信息，特殊字符采用<!CDATA
6. 你必须遵循当前的漏洞检测思路进一步利用，跟当前利用的漏洞类型保持一致，比如之前利用的是sql注入漏洞，现在也应该继续探索sql注入漏洞的绕过方式，请勿改变测试的漏洞类型
7. 一次只能调用一种工具
8. 你需要仔细分析请求的响应结果，观察其与请求参数是否存在联系，以及与原始页面的差别
9. 如果出现报错，还需要详细分析报错的原因，最终生成可用的payload，报错的原因可能有参数类型不匹配，最常见的事数字型参数传入了字符型payload
10. 绕过的最终目的是达到代码执行或xss触发，比如ssti需要最终执行代码

你可以调用的工具格式如下：
工具名称：run_python
工具描述：当已封装工具无法满足请求时，自定义python脚本并执行返回结果
参数格式：
<value>
    Python代码
</value>
"""

message_template = """

当前的漏洞检测思路：
{solution}

当前漏洞利用方式如下：
{tool_chain}

对当前利用的说明和进一步利用的提示：
{desc}

原始页面信息如下：
请求：
{request}
响应：
{response}

请你构造绕过方式
"""

fail_message = """
请进行总结，总结格式如下：
<summary>
    <type>没有绕过的原因</type>
    <payload>尝试过但没有成功的载荷</payload>
</summary>
"""


def change_payload(tool_chain, desc, page, key, solution, depth=10):
    parent_page = page_helper.get_parent_page(page['id'])
    parent_request = ""
    parent_response = ""
    if parent_page:
        parent_request = parent_page['request']
        parent_response = parent_page['response']
    message = message_template.format(request=page["request"], response=page["response"], tool_chain=tool_chain, desc=desc, solution=solution)
    session_id = add_message(message)
    tool_list = open(config.ADDON_README_PATH, "r").read()
    response = chat(prompt_template, session_id)
    # print(response)
    count = 0

    while "<tool>" in response:
        if count > depth:
            add_message(fail_message, session_id)
            break
        action_xml = re.findall('(<tool>.*?</tool>)', response, re.DOTALL)[0]
        action = xmltodict.parse(action_xml)['tool']
        tool_name = action['name']
        tool_value = action['value']
        tool_result = execute_tool(tool_name, tool_value)
        # print(tool_result)

        add_message("python代码执行结果为：" + str(tool_result), session_id)
        response = chat(prompt_template, session_id)
        # print(response)
        count += 1

    if "<summary>" in response:
        summary_xml = re.findall('(<summary>.*?</summary>)', response, re.DOTALL)[0]
        summary = xmltodict.parse(summary_xml)['summary']
        return summary
    return None