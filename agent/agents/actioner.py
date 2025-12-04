import json
import os
import traceback

import xmltodict

from addons import distinguish
from agents.executor import execute_tool
from utils import page_helper, flagUtil
from config import config
from utils.agent_manager import agent_manager
from utils.chatbot import add_message, chat
import re

from utils.logger import logger
from agents import vulner

prompt_template = """
你是一个ctf解题专家，你需要根据目标检测思路和当前页面来决定调用的工具请求。
你必须遵循对应漏洞测试规范进行按步骤测试，发现漏洞就进行总结，如果发现存在某些限制或过滤，也立刻停止利用并总结，后续会提供给你绕过方式。
如果提供了测试工具，必须先使用工具进行验证，然后再进行深入测试。

CTF描述：
{ctf_desc}

原始页面信息如下：
请求：
{request}

响应：
{response}

当前关键信息：
{key}

你需要检测的漏洞为：
{vuln}
对于该漏洞的检测方法和调用工具代码时需要注意的规范如下：
{prompt_detect}

你需要根据漏洞规范中的要求构造xml数据，除此之外，如果你想进行手动漏洞探测或网页请求，请直接进行request工具调用，调用格式如下：
<request>
    {request_desc}
</request>
由于部分情况网页上下文过长，你需要对比发送载荷响应与正常响应的关键不同，可以使用如下方式：
<distinguish>
    <request1>
        <value>...</value>
    </request1>
    <request2>
        <value>...</value>
    </request2>
</distinguish>
其中request_xml_1为正常请求，request_xml_2为发送载荷后的请求，格式和request工具请求格式一致
对比结果会返回载荷请求中与正常请求不同的地方

执行命令或发送rce载荷请求必须使用distinguish工具对比不传入cmd的请求获取最终结果，不可以在执行命令时使用request工具。

如果你发现了某个漏洞并且利用该漏洞成功访问到了新的页面，如使用爆破、sql注入等绕过了登录限制，访问到了系统后台，你需要在总结前再次利用request工具触发漏洞访问新页面，并且需要将needExplore设置为True。

如果检测流程已经完成，返回如下格式，注意desc采用<!CDATA包裹：
<summary>
    <vuln>True/False（是否存在漏洞）</vuln>
    <desc><![CDATA[根据之前结果进行本次漏洞检测总结，需要写出详细漏洞参数、漏洞类型、漏洞载荷，漏洞载荷使用【】包装，尽可能详细描述，把所有路径、成功的载荷信息都说明清楚，如果用到其他漏洞，需要写明用到的漏洞的id；如利用id为xxx的漏洞上传文件后进行xxx]]></desc>
    <needDeep>True/False（是否需要深入探索，比如存在某些限制，需要一些高级策略支持）</needDeep>
</summary>


请注意：
1. 如果没有特殊说明，你一次只能进行一种工具调用，即一次回答中只能包含一个完整的xml
2. 总结时不需要给出进一步利用建议
3. 回答时需要先给出当前步骤的推理步骤，再给出需要调用的xml数据
4. 发现漏洞就进行总结，如果发现存在某些限制或过滤，也立刻停止利用并总结，后续会提供给你绕过方式
5. 不允许修改用户名为demo的用户的用户名和密码
"""


# 你可以利用漏洞库中的已知漏洞，首先必须查看漏洞的详细信息，查看方式如下：
# <info>
#     <id>漏洞id</id>
# </info>
#
# 漏洞库简介如下(id:描述)，如果你想利用漏洞，必须首先使用info查看详细信息，然后进行利用：
# {vuln_db_desc}

message_template = """
你需要实现的漏洞检测思路如下：
{desc}
"""

tool_message_template = """
工具执行结果如下：
{tool_result}
"""

page_message_template = """
页面{page_id}详细信息如下：
请求：
{page_request}


"""


need_flag_text = """
你现在需要继续利用发现的漏洞，并且尝试获取系统中隐藏的flag，如果之前的步骤里没有获取到flag信息，则需要进行后利用需要首先查看后利用知识库获取规范的后利用步骤，查看知识库方式如下：
<knowledge>
    <id>知识库id</id>
</knowledge>

后利用知识库id和简单介绍如下：
{knowledge}

你也可以继续访问系统中的其他页面进行漏洞的组合利用，你访问页面的方式如下：
<page>
    <id>页面id</id>
</page>

当前已经获取到的页面id和简单介绍如下：
{pages}


注意：
* 如果已经获取到了可靠的flag值，直接总结即可，不需要继续后利用。
* 你可以从后利用知识库中选择当前漏洞对应的知识库，如果不存在对应的知识库则不需要查看，根据当前信息继续尝试利用，直至获取flag。
* flag为一串复杂的长字符串，通常包含{{，并且在页面上显示以flag开头，形式为：flag{{xxxxx}}，你需要通过读取文件或读取环境变量等方式获取最终的flag。

最终的总结如下：
<summary>
    <vuln>True/False（是否存在漏洞）</vuln>
    <findFlag>True/False（是否发现flag）</findFlag>
    <desc><![CDATA[根据之前结果进行本次漏洞检测总结，需要写出详细漏洞参数、漏洞类型、漏洞载荷，漏洞载荷使用【】包装，尽可能详细描述，把所有路径、成功的载荷信息都说明清楚，如果用到其他漏洞，需要写明用到的漏洞的id；如利用id为xxx的漏洞上传文件后进行xxx]]></desc>
    <flag>如果发现flag(一串复杂字符)，输出flag内容，否则置空</flag>
</summary>
""".strip()

knowledge_base = config.get_knowledge("get_flag")



def execute_solution(solution, page, key, explorer_pages, vuln_db):
    try:
        # vuln_db = [{'id': '0dc52cfd-22e1-454a-9c33-e0962e6cae0b', 'task_id': '03a02a6a-b3f7-46a4-81a2-afc151cd4301', 'vuln_type': 'UPLOAD', 'desc': '存在文件上传漏洞。上传的 PHP 文件可以被访问，但没有被正确解析为 PHP 代码。请求 URL 为 http://172.20.10.13:55226/posts/upload-article.php，请求方法为 POST，请求参数包括 name 和 email，上传文件参数名为 articleFile，文件内容为 【】，文件名为 test.php，文件类型为 text/plain。上传后的文件可以通过 http://172.20.10.13:55226/posts/uploads/test.php 访问。', 'request_json': {'url': 'http://172.20.10.13:55226/posts/upload-article.php', 'method': 'POST', 'header': {'User-Agent': 'python-requests/2.32.3', 'Accept-Encoding': 'gzip, deflate, zstd', 'Accept': '*/*', 'Connection': 'keep-alive'}, 'param': {'name': 'John Doe', 'email': 'john.doe@example.com'}, 'files': {'articleFile': ('example_article.txt', 'This is a sample article for testing purposes.', 'text/plain')}}}]
        global knowledge_base
        vuln = solution['vuln']
        desc = solution['desc']

        vuln_db_desc = "\n".join([f"""{i['id']}: {i['desc']}""" for i in vuln_db])

        # if vuln != "CMD":
        #     return {}

        # 使用反射方法从vulns模块动态导入对应漏洞的检测prompt
        detect_message = agent_manager.send_pure_message_with_status(
            agent_manager.current_task_id,
            content=f"⚡ 开始执行 {page['name']} 页面的漏洞检测思路 [{vuln}] ({desc})",
            status="running"
        )

        solution_id = detect_message.get("id")

        session_id = solution_id
        try:
            vuln_module = __import__(f"agents.vulns.{vuln}", fromlist=["simple_detect", "prompt_detect", "need_detect"])
        except:
            vuln = "OTHER"
            vuln_module = __import__(f"agents.vulns.{vuln}", fromlist=["simple_detect", "prompt_detect", "need_detect"])
        need_detect = getattr(vuln_module, "need_detect")
        if not need_detect(page['request']):
            vuln = "OTHER"
            vuln_module = __import__(f"agents.vulns.{vuln}", fromlist=["simple_detect", "prompt_detect", "need_detect"])

            # if detect_message:
            #     status_text = f"✅ {page['name']} 页面漏洞检测思路 [{vuln}] 不满足前置条件，跳过检测"
            #
            #     agent_manager.update_pure_message_status(
            #         detect_message.get('id'),
            #         "finish",
            #         status_text
            #     )
            # return {}
            # vuln_module = __import__(f"agents.vulns.{vuln}", fromlist=["simple_detect", "prompt_detect", "need_detect"])
        simple_detect = getattr(vuln_module, "simple_detect")
        prompt_detect = getattr(vuln_module, "prompt_detect")
        prompt = prompt_template.format(ctf_desc=config.CTF_DESC, request=page['request'], response=page['response'], vuln=vuln, prompt_detect=prompt_detect, request_desc=config.get_addon("request_vuln"), vuln_db_desc=vuln_db_desc, key=key)
    except Exception as e:
        traceback.print_exc()
        return
    try:
        step_count = 0
        all_results = []
        # 导入chatbot模块以使用进程状态检查
        from utils.chatbot import check_process_status

        message = message_template.format(desc=desc, key=key)
        if not session_id:
            session_id = add_message(message)
        else:
            add_message(message, session_id)
        while True:

            step_count += 1
            if (step_count > 30 and vuln == 'OTHER') or config.FLAG:
                summary = {"vuln":"False", "findFlag":"False", "desc":"", "flag":""}
                break
            # 在每次循环开始前检查进程状态
            check_process_status(session_id)

            response = chat(prompt, session_id)
            detect_xmls = re.findall(r'(<detect>.*?</detect>)', response, re.DOTALL)
            tool_xmls = re.findall(r'(<tool>.*?</tool>)', response, re.DOTALL)
            request_xmls = re.findall(r'(<request>.*?</request>)', response, re.DOTALL)
            distinguish_xmls = re.findall(r'(<distinguish>.*?</distinguish>)', response, re.DOTALL)

            summary_xml = re.search(r'(<summary>.*?</summary>)', response, re.DOTALL)
            vuln_xml = re.search(r'(<info>.*?</info>)', response, re.DOTALL)
            exploit_xml = re.search(r'(<exploit>.*?</exploit>)', response, re.DOTALL)
            knowledge_xml = re.search(r'(<knowledge>.*?</knowledge>)', response, re.DOTALL)
            page_xml = re.search(r'(<page>.*?</page>)', response, re.DOTALL)

            if detect_xmls:
                for detect_xml in detect_xmls:
                    param = xmltodict.parse(detect_xml)['detect']
                    result = simple_detect(json.loads(json.dumps(page['request'])), page['response'], param)
                    if not result:
                        add_message(f"上一轮检测试未发现漏洞，请继续测试或进行总结", session_id)
                    else:
                        all_results.extend(result)
                        add_message(f"上一轮检测发现漏洞：{result}，请继续测试或进行总结", session_id)
            elif vuln_xml:
                vuln_id = xmltodict.parse(vuln_xml.group(1))['info']['id']
                # vuln_db为列表，需要根据id查找
                vuln_detail = next((i for i in vuln_db if i['id'] == vuln_id), None)
                add_message(f"漏洞详情如下：{vuln_detail}", session_id)
            elif exploit_xml:
                exploit_id = xmltodict.parse(exploit_xml.group(1))['exploit']['id']
                exploit_message = xmltodict.parse(exploit_xml.group(1))['exploit']['message']
                # vuln_db为列表，需要根据id查找
                exploit_detail = next((i for i in vuln_db if i['id'] == exploit_id), None)
                exploit_result = vulner.exploit_vuln(exploit_detail['request'], exploit_detail['vuln_type'], exploit_detail['desc'], exploit_message)
                add_message(f"漏洞利用结果如下：{exploit_result}", session_id)
            elif tool_xmls:
                for tool_xml in tool_xmls:
                    param = xmltodict.parse(tool_xml)['tool']
                    result = simple_detect(json.loads(json.dumps(page['request'])), page['response'], param)
                    if not type(result) == list:
                        result = [result]
                    add_message("工具调用结果如下：", session_id)
                    for r in result:
                         add_message(str(r), session_id)
                    if not result:
                        add_message("无有效调用结果", session_id)

            elif request_xmls:
                for request_xml in request_xmls:
                    try:
                        new_request = xmltodict.parse(request_xml)['request']['value']
                        new_request['history'] = False
                        result = execute_tool('request', new_request)
                        add_message("网络请求响应如下：" + str(result) + "，请继续探索或总结", session_id)
                    except Exception as e:
                        add_message(f"网络请求响应xml解析出错:{e}，请重新构造", session_id)

            elif distinguish_xmls:
                for distinguish_xml in distinguish_xmls:
                    distinguish_result = distinguish.run(xmltodict.parse(distinguish_xml)['distinguish']['request1']['value'], xmltodict.parse(distinguish_xml)['distinguish']['request2']['value'])
                    add_message("对比结果如下：" + str(distinguish_result) + "，请继续探索或总结", session_id)
            elif knowledge_xml:
                knowledge_id = xmltodict.parse(knowledge_xml.group(1))['knowledge']['id']
                knowledge = next((i for i in knowledge_base if i['id'] == knowledge_id), None)
                if knowledge:
                    add_message("知识库内容如下：" + knowledge['all'], session_id)
                else:
                    add_message("未找到有效知识库", session_id)

            elif page_xml:
                page_id = xmltodict.parse(page_xml.group(1))['page']['id']
                new_page = next((explorer_pages[i] for i in explorer_pages if i == page_id), None)
                if page:
                    add_message("页面详情如下：" + str(new_page), session_id)
                else:
                    add_message("未找到有效页面", session_id)


            elif summary_xml:
                summary = xmltodict.parse(summary_xml.group(1))['summary']

                if summary['vuln'] == 'True' and not all_results:
                    all_results = [f'存在{vuln}漏洞']
                summary['vuln_type'] = vuln
                summary['request'] = json.dumps(page['request'])
                if "flag" in summary and summary['flag']:
                    flagUtil.set_flag(summary['flag'])
                    break
                if (config.NEED_FLAG and summary['vuln'] == "True" and not "findFlag" in summary) or ("needDeep" in summary and summary['needDeep'] == 'True') or ( vuln =='OTHER' ):
                    add_message(need_flag_text.format(knowledge="\n".join([f"{i['id']}: {i['desc']}" for i in knowledge_base]), pages="\n".join([f"{i}: {explorer_pages[i]['name']} {explorer_pages[i]['key']}" for i in explorer_pages])), session_id)
                else:
                    break

            else:
                add_message("未识别到有效指令，请重新输入", session_id)

        # 执行完成，更新消息状态
        if detect_message:
            status_text = f"✅ {page['name']} 页面[{vuln}]漏洞检测思路执行完成"

            if all_results:
                status_text += "，存在漏洞"


            if summary and summary.get("findFlag", "False") == 'True':
                status_text += "，发现Flag！"

            agent_manager.update_pure_message_status(
                detect_message.get('id'),
                "finish",
                status_text
            )




        return {
            "result": all_results,
            "summary": summary,
            "request": page['request']
        }

    except Exception as e:
        traceback.print_exc()
        print(e)





