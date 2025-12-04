import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import md5

import urllib3.util
import xmltodict

from addons.request import add_page
from agents.executor import execute_tool
from utils.chatbot import add_message, chat
from config import config
from utils.logger import logger
from addons import request


prompt_js = """
你需要收集网页上所有相关的js文件，包括但不限于：
1. 页面上的所有js文件
2. 页面上的所有内联js代码
3. 页面上的所有引入的js文件
返回一个xml格式的js列表：
<js>
    <url>https://xx.xx.xx/xxx.js</url>
    <url>https://xx.xx.xx/xxx.js</url>
</js>
url由当前页面url和页面js路径拼接获取
"""

prompt_api = """
你需要提取页面中和后端交互的接口完整说明，包括但不限于：
1. 接口路径
2. 请求方法
3. 请求参数
4. 接口说明
"""


prompt_template = """
你是一个网页使用专家，你可以根据已有的信息和网站功能进行网页的浏览与探索，你需要在一个回答里把所有需要探索的网页都探索完成。
你需要集中于获取更多网页交互请求，即需要进行以下操作：
1. 你需要尽可能地使用当前已经获取到的关键信息，比如收集到的用户名和密码需要尽可能使用，不要自己直接构造，注意不要爆破参数，每个参数只需要测试最可能的值即可；
2. 你需要访问所有原页面的url和api接口，保证所有新页面都要访问到，关键信息中可能提示的参数也需要使用，当你构造POST请求参数时需要严格按照页面表单中的参数构造
3. {page_desc}
4. 使用xml格式返回响应
5. 如果没有当前页面则为初始请求，访问系统url即可
6. 不要访问登出功能，不要访问css和图像，不要通过猜测路径获取新页面，如果所有已知的路径均访问完成，返回"任务已完成"即可
7. 如果是修改用户信息（包括密码）请求，请将修改后的信息和原信息设置为一样，避免篡改信息
8. 对于工具请求的构造，value由多个xml子标签构成，如果xml子标签中的值出现特殊字符，使用<![CDATA[
你需要返回的调用网络请求工具格式如下：
<step>
    <tool>request</tool>
    {request_desc}
</step>
说明：
* tool：从工具库中获取到的工具执行结果
* value：工具需要传入的参数，根据工具说明中的参数模版给出

一个完整的响应如下：
1）关键信息中发现了xxx/xxx；
2）我现在看到的是一个登陆页面
3）我可以采用登陆请求策略来探索更多路径
4）对于登陆请求策略，该页面显示，登陆的api端点为/xxx，我需要对 http://xx.xx.xx/xxx发起请求
5）我已经收集到了信息：xxx，我需要使用该信息进一步探索
6）我将构造如下响应发送请求：
<step>
    xxx
</step>
<step>
    xxx
</step>
...

系统url：
{CTF_URL}
"""

message = """
当前获取的关键信息如下，你需要尽量利用其来构造请求：
{key}

当前探索到的漏洞如下：
{vuln}

当前页面url：
{url}
页面内容如下：
{response}
该页面上的js文件中存在的接口如下：
{js_info}

请你根据以上线索，探索新路径，必须将每一个暴露的url和接口都访问到
"""

message_api = """
js文件url：
{url}

以下是页面内容：
{response}

提取其中和后端交互的接口完整说明
"""



message_js = """

当前页面url：
{url}
页面内容如下：
{response}

请你根据以上页面内容，提取出所有相关的js列表
"""

form_message = """
以下是一些之前页面的表单代码，请你根据这些代码构造新的请求访问页面：
{forms}
""".strip()

black_ext = [".css", ".png", ".jpg", ".ico", ".webp", ".pickle", "bootstrap.bundle.min.js", ".svg", ".jpeg"]

back_path = ['logout', 'bootstrap.bundle']

def guess_path(url):
    logger.info("对初始url进行常见路径探测")
    path_payload = config.get_payload("path")
    root_url = urllib3.util.parse_url(url)
    root_url = f"{root_url.scheme}://{root_url.host}:{root_url.port}" if root_url.port else f"{root_url.scheme}://{root_url.host}"
    all_pages = []
    
    # 创建线程池进行并发请求
    def check_path(p):
        url = f"{root_url}{p}"
        request_json = {"method":"OPTIONS", "url": url}
        result = request.run(request_json)
        if result['status'] == 200 or result['status'] == 405:
            if len(result['content']) == 0 or result['status'] == 405:
                result = request.run({"method":"GET", "url": url})
                if result['status'] in [404, 403] or result['content'] == 0:
                    return
            logger.info(f"发现新路径：{url}")
            return result['history']
        return []

    # 使用concurrent.futures而不是asyncio来处理并发
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        # 提交所有任务到线程池
        for p in path_payload:
            future = executor.submit(check_path, p)
            futures.append(future)
            
        # 获取所有结果
        for future in futures:
            try:
                pages = future.result()
                all_pages.extend(pages)
            except Exception as e:
                logger.error(f"检查路径时发生错误: {str(e)}")
                continue
                
    return all_pages

def explore_all_js(page):
    """
    探索页面所有js文件
    :param page: 页面
    :return: 动作
    """
    results = {}
    
    # 直接从页面内容中提取JavaScript URL
    page_content = page.get("response", {}).get('content', '')
    page_url = page.get("response", {}).get('url', '')
    
    # 使用正则表达式提取JavaScript文件URL
    js_patterns = [
        r'<script[^>]+src=["\']([^"\']+)["\'][^>]*>',  # <script src="...">
        r'src=["\']([^"\']*\.js[^"\']*)["\']',         # src="...js..."
        r'["\']([^"\']*\.js(?:\?[^"\']*)?)["\']',      # "...js" or "...js?..."
    ]
    
    js_urls = set()
    for pattern in js_patterns:
        matches = re.findall(pattern, page_content, re.IGNORECASE)
        for match in matches:
            if match and not match.startswith('data:'):  # 排除data URL
                js_urls.add(match.strip())
    
    # 处理URL拼接，区分绝对路径和相对路径
    from urllib.parse import urljoin, urlparse
    
    final_js_urls = []
    parsed_page_url = urlparse(page_url)
    base_url = f"{parsed_page_url.scheme}://{parsed_page_url.netloc}"
    
    for js_url in js_urls:
        if js_url.startswith(('http://', 'https://')):
            # 绝对URL，直接使用
            final_js_urls.append(js_url)
        elif js_url.startswith('/'):
            # 以/开头的绝对路径，拼接到域名
            final_js_urls.append(base_url + js_url)
        else:
            # 相对路径，使用urljoin处理
            final_js_urls.append(urljoin(page_url, js_url))
    
    js_urls = final_js_urls
    
    def _fetch_single_js(u):
        """抓取单个 JS 并返回 (url, 接口信息)"""
        try:
            result = request.run({"method": "GET", "url": u.strip()})
            sid = add_message(message_api.format(url=u.strip(), response=result['content']), session_id=None)
            model_type = "large" if len(result.get("content", "")) > 100000 else "normal"
            response = chat(prompt_api, sid, type=model_type, limit=100000)
            return u, response
        except Exception as e:
            logger.error(f"请求JS文件 {u} 失败: {str(e)}")
            return u, ""

    # 多线程并发处理
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(_fetch_single_js, u) for u in js_urls]
        for fut in as_completed(futures):
            url, info = fut.result()
            if info:
                results[url] = info

        return results
            
    



def explore_page(page, key, vuln, session_id):
    """
    探索页面
    :param page: 页面
    :return: 动作
    """

    if not page.get("request"):
        add_message("访问提供的初始url", session_id)
    else:
        js_info = explore_all_js(page)
        js_info = "\n".join([f"js文件url：{url}\n该js中的接口说明：{info}" for url, info in js_info.items()])

        add_message(message.format(url=page.get("response", "")['url'], response=page.get("response", "")['content'], key=key, vuln=vuln, js_info=js_info), session_id=session_id)
    if 'vuln' in page:
        page_desc = "尽可能多的访问新网页或对api发送网络请求，当前页面存在漏洞，必须使用已经探测到的漏洞信息进行更多页面的发现，不可以更改载荷"
    else:
        page_desc = "尽可能多的访问新网页或对api发送网络请求，只能发送正常请求参数，不可以进行漏洞探测，不可以发送任何危险参数"

    prompt = prompt_template.format(CTF_URL=config.CTF_URL, page_desc=page_desc, request_desc=config.get_addon("request"))


    response = chat(prompt, session_id)
    # print(response)
    response_xml = re.findall("(<step>.*?</step>)", response, re.DOTALL)

    step_count = 0
    new_pages = []
    wrong_page = []

    flag = False

    if not page.get("request"):
        all_pages = guess_path(config.CTF_URL)
        for new_page in all_pages:
            flag = True
            new_page = add_page(new_page)
            if new_page:
                new_pages.append(new_page)
                new_page_info = f"url：{new_page['response']['url']} header：{new_page['response']['header']} response：{new_page['response']['content']} 关键线索：{new_page['key']}"
                add_message(f"爆破路径访问到页面：{new_page_info}", session_id)

    stop_flag = False

    while response_xml:
        if config.FLAG:
            break
        explore_pages = []
        for step_xml in response_xml:
            try:
                step = xmltodict.parse(step_xml)['step']
                tool_name = step['tool']
                value = step['value']
                # 提取URL路径部分（去除查询参数）来检查扩展名
                url_path = value['url'].split('?')[0].split('#')[0]
                if any(url_path.endswith(ext) for ext in black_ext) or any(p in url_path for p in back_path):
                    continue
                md5_request = md5((str(value)+config.TASK_ID).encode()).hexdigest()
                if md5_request not in config.EXPLORED_PAGES:
                    config.EXPLORED_PAGES.append(md5_request)
                    result = execute_tool(tool_name, value)
                    pages = result['history']
                    for new_page in pages:
                        new_page = add_page(new_page)
                        if new_page:
                            flag = True

                            new_page_info = f"url：{new_page['response']['url']} header：{new_page['response']['header']} response：{new_page['response']['content']} 关键线索：{new_page['key']}"
                            new_pages.append(new_page)
                            explore_pages.append(new_page_info)
                            if new_page['response']['status'] in config.WRONG_STATUS_LIST:
                                wrong_page_info = f"访问出错页面：{new_page['name']} 请求体：{new_page['request']} 响应码：{new_page['response']['status']}"
                                add_message(f"上一轮访问出错的页面：{wrong_page_info}", session_id)
                                wrong_page.append(wrong_page_info)

                            else:
                                add_message(f"上一轮访问成功的页面：{new_page_info}", session_id)



            except Exception as e:
                print(e)
                break
        if not flag:
            add_message("上一轮没有访问到有效页面", session_id)

        step_count += 1
        flag = False

        if stop_flag:
            break

        if step_count > 4:
            new_forms = []

            for form_url in config.FORMS:
                has_explored = any(form_url in explored for explored in config.EXPLORE_URLS)
                if not has_explored:
                    new_forms.append(config.FORMS[form_url])
            if new_forms:
                add_message(form_message.format(forms="\n".join([f['form'] for f in new_forms])), session_id)
            stop_flag = True
            config.FORMS = {}

        else:
            add_message("\n请你：1. 修正访问出错的页面，如果是405错误，必须修改为更合适的方法重新访问，比如POST需要换为GET，注意提交的参数不要改变"
                                + "2. 根据新的访问成功页面结合已有信息继续进行探索", session_id)


        try:
            response = chat(prompt, session_id)
            response_xml = re.findall("(<step>.*?</step>)", response, re.DOTALL)
        except Exception as e:
            print(e)
            break

    return new_pages

