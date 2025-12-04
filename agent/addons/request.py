import base64
import binascii
import json
import re
import time
import uuid
import warnings
import importlib
import os
from hashlib import md5
from html.parser import HTMLParser
from urllib.parse import urlparse, parse_qs, urlencode
from urllib.request import urlopen, Request, HTTPHandler, HTTPSHandler, build_opener, ProxyHandler, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from http.cookiejar import CookieJar
import ssl
import traceback
from config import config
from utils import flagUtil

warnings.filterwarnings("ignore")


def remove_svg_from_content(content):
    """
    从HTML内容中移除所有SVG元素

    Args:
        content (str): HTML内容字符串

    Returns:
        str: 移除SVG后的HTML内容
    """
    # 使用正则表达式匹配SVG标签（包括嵌套的SVG）
    svg_pattern = r'<svg[^>]*>.*?</svg>'

    # 移除SVG元素，使用DOTALL让.匹配换行符，IGNORECASE忽略大小写
    cleaned_content = re.sub(svg_pattern, '', content, flags=re.DOTALL | re.IGNORECASE)

    # 移除可能留下的多余空行
    cleaned_content = re.sub(r'\n\s*\n', '\n', cleaned_content)

    return cleaned_content


def extract_forms(html):
    """从HTML中提取form元素和对应的URL"""

    class Parser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.forms = []
            self.current_form = []
            self.depth = 0

        def handle_starttag(self, tag, attrs):
            if tag == 'form' and self.depth == 0:
                self.depth = 1
                attrs_str = ' '.join(f'{k}="{v}"' for k, v in attrs)
                self.current_form.append(f'<form {attrs_str}>')
                self.url = dict(attrs).get('action', '')
            elif self.depth > 0:
                self.depth += 1
                attrs_str = ' '.join(f'{k}="{v}"' for k, v in attrs)
                self.current_form.append(f'<{tag} {attrs_str}>')

        def handle_endtag(self, tag):
            if self.depth > 0:
                if tag == 'form' and self.depth == 1:
                    self.current_form.append('</form>')
                    self.forms.append({
                        'form': ''.join(self.current_form),
                        'url': self.url
                    })
                    self.current_form = []
                    self.depth = 0
                else:
                    self.depth -= 1
                    self.current_form.append(f'</{tag}>')

        def handle_data(self, data):
            if self.depth > 0:
                self.current_form.append(data)

    parser = Parser()
    parser.feed(html)
    return parser.forms


def add_page(new_page, need_save=False):
    from utils.agent_manager import agent_manager
    from agents.saver import save_page
    request = new_page['request']
    response = new_page['response']
    md5_request = md5((str(request) + config.TASK_ID).encode()).hexdigest()
    md5_response = md5((request['method']+str(request['params'])+str(response['content']) + config.TASK_ID).encode()).hexdigest()
    if new_page['response'] and md5_response not in config.EXPLORED_PAGE_RESPONSES and new_page['response'][
        'status'] != 404:
        config.EXPLORED_PAGE_RESPONSES.append(md5_response)
        if not need_save:
            save_result = save_page(new_page)
            if config.NEED_FLAG and save_result['flag']:
                if "/admin../flag.txt" in response['url']:
                    time.sleep(120)
                flagUtil.set_flag(save_result['flag'])
        else:
            save_result = {
                'name': str(md5_request),
                'description': '',
                'key': '',
                'flag': ''
            }
        new_page['key'] = save_result.get("key", "")
        new_page['description'] = save_result.get("description", "")
        new_page['name'] = save_result['name']
        new_page['id'] = md5_request

        form_datas = extract_forms(response['content'])
        for form_data in form_datas:
            config.FORMS[form_data['url']] = form_data
            config.EXPLORE_URLS.append(response['url'])

        if need_save and config.HUNTER:
            config.HUNTER.explorer_pages.append(new_page)
            page_data = {
                "name": new_page['name'],
                "request": json.dumps(new_page.get('request', {})),
                "response": json.dumps(new_page.get('response', {})),
                "description": new_page.get('description', ''),
                "key": new_page.get('key', '')
            }
            created_page = agent_manager.create_page(agent_manager.current_task_id, page_data)

            # if new_page["key"]:
            #     with open(config.HUNTER.key_simple_file, "a+") as f:
            #         f.write(str(['name']) + f" {new_page['response']['url']} 发现线索：" + str(new_page['key']) + "\n")
            #     with open(config.HUNTER.key_file, "a+") as f:
            #         f.write(str(new_page['name']) + f" 请求：{new_page['request']} 发现线索：" + str(new_page['key']) + "\n")



        return new_page
    else:
        return None


def process_addon_templates(text) -> str:
    """
    处理{{addon()}}模板替换
    通过反射机制动态引入addons目录下的模块并调用其run函数
    
    Args:
        text: 包含模板的字符串
        
    Returns:
        str: 替换后的字符串
    """
    if not isinstance(text, str):
        return text
    
    # 匹配{{addon_name(param)}}模式
    pattern = r'\{\{(\w+)\((.*?)\)\}\}'
    
    def replace_addon(match):
        addon_name = match.group(1)
        param = match.group(2).strip()
        
        # 移除参数两端的引号（如果有）
        if param.startswith('"') and param.endswith('"'):
            param = param[1:-1]
        elif param.startswith("'") and param.endswith("'"):
            param = param[1:-1]
        elif param.startswith("base64|"):
            param = base64.b64decode(param[7:].encode()).decode()

        try:
            # 动态导入addon模块
            module_path = f"addons.{addon_name}"
            addon_module = importlib.import_module(module_path)
            
            # 调用模块的run函数
            if hasattr(addon_module, 'run'):
                result = addon_module.run(param)
                return str(result) if result is not None else ""
            else:
                print(f"Warning: addon '{addon_name}' does not have a 'run' function")
                return match.group(0)  # 返回原始模板
                
        except ImportError:
            print(f"Warning: addon '{addon_name}' not found")
            return match.group(0)  # 返回原始模板
        except Exception as e:
            print(f"Error processing addon '{addon_name}': {str(e)}")
            return match.group(0)  # 返回原始模板
    
    return re.sub(pattern, replace_addon, text)

class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # 禁止重定向

def run(params):
    """
    进行网络请求的主函数，自动记录重定向过程中的所有cookies
    params: 字典类型，包含以下键值:
        - url: 请求URL
        - method: 请求方法(GET/POST等)
        - header: 请求头(字典类型)
        - proxy: 代理设置
        - param: 请求参数(字典类型)
        - files: 文件上传参数(字典类型)
        - no_url_encode: 是否禁用URL编码(布尔类型，默认False)
    """
    try:
        # 设置代理
        proxy_handler = None

        # 设置请求头和参数
        headers = params.get('header', {})
        request_param_list = params.get('params', [])
        raw_data = params.get('raw', None)  # 新增raw参数支持
        need_explore = params.get("needExplore", "False") == "True"
        
        # 处理params参数格式
        if request_param_list and 'x-param' in request_param_list:
            request_param_list = request_param_list['x-param']
            if not type(request_param_list) == list:
                request_param_list = [request_param_list]
        
        method = params.get('method', 'GET').upper()
        files_config = params.get('files', {})

        need_history = params.get('history', True)

        if not headers:
            headers = {}

        request_params = {}

        # 处理参数列表
        if type(request_param_list) == list:
            if request_param_list:
                for p in request_param_list:
                    request_params[p['x-name']] = p['x-value']
        elif request_param_list:
            request_params = request_param_list

        # 检查是否禁用URL编码
        no_url_encode = params.get('no_url_encode', False)
        
        # 检查是否禁止重定向
        no_redirect = params.get('no_redirect', False)
        
        # 应用模板替换
        # 处理URL中的模板
        if 'url' in params:
            params['url'] = process_addon_templates(params['url'])
        
        # 处理headers中的模板
        if headers:
            for key, value in headers.items():
                headers[key] = process_addon_templates(str(value))
        
        # 处理request_params中的模板
        if request_params:
            for key, value in request_params.items():
                if isinstance(value, str):
                    request_params[key] = process_addon_templates(value)
                elif isinstance(value, list):
                    request_params[key] = [process_addon_templates(str(v)) for v in value]
        
        # 处理raw_data中的模板
        if raw_data and isinstance(raw_data, str):
            raw_data = process_addon_templates(raw_data)
        
        # 创建cookie jar和opener
        cookie_jar = CookieJar()
        
        # 创建SSL上下文，忽略证书验证
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # 创建HTTPS handler
        https_handler = HTTPSHandler(context=ssl_context)
        
        # 创建opener
        if proxy_handler:
            opener = build_opener(proxy_handler, https_handler)
        else:
            opener = build_opener(https_handler)

        # 处理GET请求URL中的重复参数
        url = params['url']
        if method == 'GET' and '?' in url:
            base_url, query_string = url.split('?', 1)
            url_params = parse_qs(query_string)
            
            # 移除URL中与request_params重复的参数
            filtered_params = {k: v[0] for k, v in url_params.items() if k not in request_params}
            
            # 重建URL
            if filtered_params:
                if no_url_encode:
                    # 禁用URL编码时，手动构建查询字符串
                    query_parts = []
                    for key, value in filtered_params.items():
                        query_parts.append(f"{key}={value}")
                    url = f"{base_url}?{'&'.join(query_parts)}"
                else:
                    # 使用标准URL编码
                    url = f"{base_url}?{urlencode(filtered_params)}"
            else:
                url = base_url

        # 保存原始URL用于no_url_encode模式

        # 构建最终的请求URL
        if method == 'GET' and request_params:
            if '?' in url:
                separator = '&'
            else:
                separator = '?'
            
            if no_url_encode:
                # 禁用URL编码时，手动构建查询字符串
                query_parts = []
                for key, value in request_params.items():
                    if isinstance(value, list):
                        for v in value:
                            query_parts.append(f"{key}={v}")
                    else:
                        query_parts.append(f"{key}={value}")
                url = url + separator + '&'.join(query_parts)
            else:
                # 使用标准URL编码
                url = url + separator + urlencode(request_params, doseq=True)

        # 处理请求体数据
        request_data = None
        content_type = None
        
        if raw_data:
            # 如果有raw数据，直接使用raw作为请求体
            if isinstance(raw_data, str):
                request_data = raw_data.encode('utf-8')
            else:
                request_data = raw_data

            if 'Content-Type' not in headers and 'content-type' not in headers:
                content_type = 'text/plain'

        elif files_config and files_config.get('item'):
            # 处理文件上传 - 构建multipart/form-data
            boundary = f"----WebKitFormBoundary{uuid.uuid4().hex[:16]}"
            content_type = f'multipart/form-data; boundary={boundary}'
            headers['Content-Type'] = content_type
            
            body_parts = []
            
            # 处理文件项
            if isinstance(files_config.get('item', []), list):
                file_items = files_config['item']
            else:
                file_items = [files_config['item']]

            for file_item in file_items:
                # 处理文件内容中的模板
                file_content = file_item['content']
                if isinstance(file_content, str):
                    file_content = process_addon_templates(file_content)
                
                if file_content.startswith("hex("):
                    try:
                        # 提取hex内容并解码
                        hex_content = re.findall(r'hex\((.*?)\)', file_content)[0]
                        file_content = binascii.a2b_hex(hex_content)
                    except:
                        file_content = b''
                elif isinstance(file_content, str):
                    try:
                        file_content = binascii.a2b_hex(file_content)
                    except:
                        file_content = file_content.encode('utf-8')
                
                # 处理文件名和其他字段中的模板
                filename = process_addon_templates(str(file_item.get("filename", "item")))
                name = process_addon_templates(str(file_item["name"]))
                file_content_type = process_addon_templates(str(file_item.get("content_type", "application/octet-stream")))
                
                # 构建文件部分
                file_part = f'--{boundary}\r\n'
                file_part += f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                file_part += f'Content-Type: {file_content_type}\r\n\r\n'
                body_parts.append(file_part.encode('utf-8'))
                body_parts.append(file_content)
                body_parts.append(b'\r\n')
            
            # 添加表单参数
            if request_params:
                for key, value in request_params.items():
                    if isinstance(value, list):
                        for v in value:
                            param_part = f'--{boundary}\r\n'
                            param_part += f'Content-Disposition: form-data; name="{key}"\r\n\r\n{v}\r\n'
                            body_parts.append(param_part.encode('utf-8'))
                    else:
                        param_part = f'--{boundary}\r\n'
                        param_part += f'Content-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'
                        body_parts.append(param_part.encode('utf-8'))
            
            # 结束边界
            body_parts.append(f'--{boundary}--\r\n'.encode('utf-8'))
            request_data = b''.join(body_parts)
            
        elif method in ['POST', 'PUT', 'PATCH'] and request_params:
            # 表单数据
            if no_url_encode:
                # 禁用URL编码时，手动构建表单数据
                form_parts = []
                for key, value in request_params.items():
                    if isinstance(value, list):
                        for v in value:
                            form_parts.append(f"{key}={v}")
                    else:
                        form_parts.append(f"{key}={value}")
                request_data = '&'.join(form_parts).encode('utf-8')
            else:
                # 使用标准URL编码
                request_data = urlencode(request_params, doseq=True).encode('utf-8')
            
            content_type = 'application/x-www-form-urlencoded'

        # 设置Content-Type
        if content_type:
            headers['Content-Type'] = content_type
        
        # 手动处理重定向链
        redirect_count = 0
        max_redirects = 20
        all_set_cookies = []  # 收集所有重定向过程中设置的cookies
        history = []  # 记录所有请求和响应的历史
        current_cookies = ""  # 当前的cookie字符串

        origin_request = {
            'url': url,
            'method': method,
            'header': dict(headers),
            'params': request_params,
            'files': files_config,
            "raw": raw_data
        }

        new_request = json.loads(json.dumps(origin_request))

        while redirect_count <= max_redirects:
            try:
                # 创建请求对象
                req = Request(url, data=request_data, headers=headers, method=method)

                # 添加cookies到请求头
                if current_cookies:
                    req.add_header('Cookie', current_cookies)
                headers['Cookie'] = current_cookies




                openera = build_opener(NoRedirectHandler)

                # 发送请求
                response = openera.open(req, timeout=60)
                
                # 读取响应
                response_content = response.read()
                response_text = response_content.decode('utf-8', errors='ignore')
                # 正确处理多个相同名称的头（如多个Set-Cookie）
                response_headers = {}
                for header_name, header_value in response.headers.items():
                    if header_name.lower() in response_headers:
                        # 如果头已存在，将值合并（用于Set-Cookie等可能重复的头）
                        if isinstance(response_headers[header_name.lower()], list):
                            response_headers[header_name.lower()].append(header_value)
                        else:
                            response_headers[header_name.lower()] = [response_headers[header_name.lower()], header_value]
                    else:
                        response_headers[header_name.lower()] = header_value
                response_url = response.url
                status_code = response.status
                
            except HTTPError as e:
                # HTTP错误也要处理响应
                response_content = e.read() if hasattr(e, 'read') else b''
                response_text = response_content.decode('utf-8', errors='ignore')
                # 正确处理多个相同名称的头（如多个Set-Cookie）
                response_headers = {}
                if hasattr(e, 'headers'):
                    for header_name, header_value in e.headers.items():
                        if header_name.lower() in response_headers:
                            # 如果头已存在，将值合并（用于Set-Cookie等可能重复的头）
                            if isinstance(response_headers[header_name.lower()], list):
                                response_headers[header_name.lower()].append(header_value)
                            else:
                                response_headers[header_name.lower()] = [response_headers[header_name.lower()], header_value]
                        else:
                            response_headers[header_name.lower()] = header_value
                response_url = e.url if hasattr(e, 'url') else url
                status_code = e.code
                response = e
                
            except URLError as e:
                return {
                    'content': "",
                    'error': f"URL Error: {str(e)}"
                }
            except Exception as e:
                return {
                    'content': "",
                    'error': f"Request Error: {str(e)}"
                }
            
            # 记录当前请求和响应
            request_params_copy = request_params.copy()

            # 如果URL包含查询参数
            if '?' in url:
                query_string = url.split('?')[1]
                # 将查询参数添加到params中
                for pair in query_string.split('&'):
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        request_params_copy[key] = value
            origin_request['params'] = request_params_copy

            history.append({
                'request': json.loads(json.dumps(new_request)),
                'response': {
                    'url': response_url,
                    'status': status_code,
                    'header': response_headers,
                    'content': remove_svg_from_content(response_text)
                }
            })

            # 处理Set-Cookie响应头
            set_cookie_headers = []
            for header_name, header_value in response_headers.items():
                if header_name.lower() == 'set-cookie':
                    # header_value可能是字符串或列表
                    if isinstance(header_value, list):
                        for cookie_value in header_value:
                            set_cookie_headers.append(cookie_value)
                            all_set_cookies.append(cookie_value)
                            
                            # 解析cookie并添加到当前cookies中
                            cookie_parts = cookie_value.split(';')[0]  # 只取cookie的名值对部分
                            if '=' in cookie_parts:
                                if current_cookies:
                                    current_cookies += "; " + cookie_parts
                                else:
                                    current_cookies = cookie_parts
                    else:
                        set_cookie_headers.append(header_value)
                        all_set_cookies.append(header_value)
                        
                        # 解析cookie并添加到当前cookies中
                        cookie_parts = header_value.split(';')[0]  # 只取cookie的名值对部分
                        if '=' in cookie_parts:
                            if current_cookies:
                                current_cookies += "; " + cookie_parts
                            else:
                                current_cookies = cookie_parts

            # 检查是否需要继续重定向
            is_redirect = status_code in [301, 302, 303, 307, 308]
            if is_redirect and redirect_count < max_redirects:
                redirect_url = response_headers.get('location')
                if not redirect_url:
                    break

                # 处理相对URL
                if redirect_url.startswith('/'):
                    parsed_url = urlparse(url)
                    redirect_url = f"{parsed_url.scheme}://{parsed_url.netloc}{redirect_url}"
                elif not redirect_url.startswith(('http://', 'https://')):
                    # 处理相对路径
                    parsed_url = urlparse(url)
                    base_path = '/'.join(parsed_url.path.split('/')[:-1])
                    redirect_url = f"{parsed_url.scheme}://{parsed_url.netloc}{base_path}/{redirect_url}"

                # 更新请求参数
                url = redirect_url
                method = 'GET'  # 重定向通常使用GET方法
                request_data = None  # 清除请求体数据
                # 注意这里是一个大更改
                new_request['method'] = method
                new_request['url'] = url
                new_request['header'] = headers
                new_request['params'] = {}
                
                # 更新headers，移除Content-Type和Content-Length
                if 'Content-Type' in headers:
                    del headers['Content-Type']
                if 'Content-Length' in headers:
                    del headers['Content-Length']

                redirect_count += 1
            else:
                break

        # 构建最终响应，合并所有重定向过程中设置的cookies
        final_headers = dict(response_headers)

        # 将所有重定向过程中设置的cookies合并到最终响应的Set-Cookie头中
        if all_set_cookies:
            final_headers['Set-Cookie'] = ', '.join(all_set_cookies)
        
        save_path = ""

        if 'needSave' in params and params['needSave'] == 'True':
            save_path = config.TEMP_PATH + "/" + uuid.uuid4().hex + "-" + params['saveName']
            with open(save_path, "wb") as f:
                f.write(response_content)

        if 'needReturn' in params and params['needReturn'] == 'False':
            need_return = False
        else:
            need_return = True

        if need_explore:
            for p in history:
                add_page(p, True)

        return {
            'savePath': save_path,
            'url': response_url,
            'status': status_code,
            'header': final_headers,
            'content': response_text if need_return else "",
            'history': history if need_history else None  # 添加请求响应历史记录
        }

    except Exception as e:
        traceback.print_exc()

        return {
            'content': "",
            'error': str(e)
        }