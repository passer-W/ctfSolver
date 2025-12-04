import requests
from urllib.parse import quote

def run(params):
    """
    进行Fuzz测试的主函数
    params: 字典类型，包含以下键值:
        - url: 请求URL(包含{fuzz}占位符)
        - method: 请求方法(GET/POST等)
        - header: 请求头(字典类型)
        - proxy: 代理设置
        - payload: payload字符串，格式: xx,xx,xx 或 xx-xx(数字范围)
        - param: POST参数(字典类型，值可包含{fuzz}占位符)
    """
    try:
        results = []
        payloads = []
        
        # 处理payload来源
        if isinstance(params.get('payload'), str):
            # 处理逗号分隔的payload
            if ',' in params['payload']:
                payloads = [p.strip() for p in params['payload'].split(',')]
            # 处理范围类型的payload
            elif '-' in params['payload']:
                start, end = params['payload'].split('-')
                try:
                    start_num = int(start.strip())
                    end_num = int(end.strip())
                    payloads = [str(i) for i in range(start_num, end_num + 1)]
                except ValueError:
                    payloads = [params['payload']]
            else:
                payloads = [params['payload']]
        
        # 设置代理
        proxies = None
        if 'proxy' in params and params['proxy']:
            proxies = {
                'http': params['proxy'],
                'https': params['proxy']
            }
        
        # 设置请求头
        headers = params.get('header', {})
        
        # 获取POST参数
        post_data = params.get('param', {})

        if not post_data:
            post_data = {}

        if not headers:
            headers = {}
        
        # 判断fuzz位置
        url_has_fuzz = '{fuzz}' in params['url']
        param_has_fuzz = any(isinstance(v, str) and '{fuzz}' in v for v in post_data.values())
        header_has_fuzz = any(isinstance(v, str) and '{fuzz}' in v for v in headers.values())
        
        # 对每个payload进行测试
        for payload in payloads:
            try:
                encoded_payload = quote(payload)
                
                # 处理URL中的fuzz
                current_url = params['url']
                if url_has_fuzz:
                    current_url = current_url.replace('{fuzz}', encoded_payload)
                
                # 处理POST参数中的fuzz
                current_data = {}
                if param_has_fuzz:
                    for key, value in post_data.items():
                        if isinstance(value, str):
                            current_data[key] = value.replace('{fuzz}', encoded_payload)
                        else:
                            current_data[key] = value
                else:
                    current_data = post_data

                # 处理header中的fuzz
                current_headers = {}
                if header_has_fuzz:
                    for key, value in headers.items():
                        if isinstance(value, str):
                            current_headers[key] = value.replace('{fuzz}', encoded_payload)
                        else:
                            current_headers[key] = value
                else:
                    current_headers = headers
                
                # 发送请求
                response = requests.request(
                    method=params.get('method', 'GET'),
                    url=current_url,
                    headers=current_headers,
                    data=current_data if current_data else None,
                    proxies=proxies,
                    verify=False,
                    timeout=10
                )
                
                # 记录结果
                results.append({
                    '发送payload': payload,
                    'url': current_url,
                    '发送参数': current_data,
                    '发送头': current_headers,
                    '页面响应': response.status_code,
                    '页面返回头': dict(response.headers),
                    '页面响应内容': response.text,
                })
                
            except Exception as e:
                results.append({
                    'payload': payload,
                    'url': current_url if 'current_url' in locals() else None,
                    'data': current_data if 'current_data' in locals() else None,
                    'headers': current_headers if 'current_headers' in locals() else None,
                    'error': str(e)
                })
                
        return results
        
    except Exception as e:
        return {
            'error': str(e)
        }
