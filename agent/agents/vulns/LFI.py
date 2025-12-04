import json
import urllib3.util
import concurrent.futures
from threading import Lock
from addons import request
from config import config

prompt_detect = """
你需要严格按照以下流程进行本地文件包含检测：

你可以进行如下工具调用，你需要首先使用DEFAULT扫描内置载荷：
<tool>
    <request><![CDATA[插入{LFI}标签后的request,json格式]]></request>
    <value><![CDATA[DEFAULT（设置为DEFAULT则扫描系统内置载荷）/xxx(可以提供自定义载荷，可以使用逗号分割)]]></value>
    <type>normal</type>
</tool>


LFI标签指的是在正常request请求中相应位置插入需要进行测试的标签，如：
{"url": "http://xx/page?file={LFI}", "method": "GET", "header": {"Content-Type": "application/json"}, "files": {}}

检测流程：
1. 首先使用通用检测工具进行LFI载荷测试
2. 分析通用载荷的执行结果，判断是否存在本地文件包含漏洞
3. 如果通用载荷测试失败，尝试以下策略：
   - 上传文件包含：如果系统存在上传功能，可以进行文件上传
4. 当进行后利用时，直接使用request构造请求即可

注意：
1. 一次只能进行一个步骤，即一次只能返回一个xml
2. LFI只能发生在请求中存在参数的情况，如果原始请求没有参数，立刻停止
3. 如果发现存在LFI但存在某些限制，可以在最终结论中表示存在漏洞，但需要进一步利用
4. 如果已经发现上传漏洞，尝试上传文件后包含
5. LFI漏洞的后利用也需要继续使用包含文件利用
6. 当认为已经发现漏洞时，直接总结即可
"""

lfi_payload = config.get_payload("lfi")

def generate_path_combinations(path):
    # 移除开头和结尾的斜杠
    path = path.strip('/')

    # 分割路径为各个部分
    parts = path.split('/')

    results = []

    # 从后往前逐级构建路径
    for i in range(len(parts)):
        # 当前层级的部分
        current = parts[-i - 1:]

        # 构建完整路径（带后缀）
        full_path = '/'.join(current)
        results.append(full_path)

        # 如果最后一部分有后缀，构建不带后缀的版本
        if '.' in current[-1]:
            no_ext = current[-1].split('.')[0]
            no_ext_path = '/'.join(current[:-1] + [no_ext]) if len(current) > 1 else no_ext
            results.append(no_ext_path)

    return results

def need_detect(request_json):
    return True

def simple_detect(request_json, response, param=None):
    if param.get("type", "normal") == 'normal':
        try:
            request_json = json.loads(param['request'])
        except json.JSONDecodeError:
            return "提供的 request 模板不是合法的 JSON 格式，请检查后重试"
        
        try:
            if param.get("value", "").lower() == "default":
                # 使用LFI载荷进行测试
                payload = lfi_payload
            else:
                payload = param.get("value").split(",")
                # if "." in param.get('value'):
                #     payload = [param.get("value"), ".".join((param.get("value").split(".")[:-1]))]

            # 存储测试结果
            results = {}
            result_info = []
            results_lock = Lock()
            
            def test_lfi_payload(test_payload):
                if config.FLAG:
                    return
                try:
                    # 构造新的请求
                    new_request = json.loads(param['request'].replace("{LFI}", str(test_payload)))
                    
                    # 发送请求并获取响应
                    new_response = request.run(new_request)
                    
                    # 简化响应内容，将测试值替换为{payload}
                    simplify_content = new_response['content'].replace(str(test_payload), "{payload}")
                    
                    # 线程安全地更新结果
                    with results_lock:
                        response_found = False
                        for existing_response, values in results.items():
                            if simplify_content == existing_response:
                                results[existing_response].append(str(test_payload))
                                response_found = True
                                break
                        
                        # 如果是新的响应，创建新条目
                        if not response_found:
                            results[simplify_content] = [str(test_payload)]
                except Exception as e:
                    print(f"LFI测试载荷 {test_payload} 出错: {str(e)}")
            
            # 使用10并发进行模糊测试
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                futures = [executor.submit(test_lfi_payload, test_payload) for test_payload in payload]
                concurrent.futures.wait(futures)
            
            # 格式化结果信息
            for k in results:
                result_info.append(f"载荷 【{','.join(results[k])}】: {k}\n")
            
            return result_info
            
        except Exception as e:
            return f"LFI测试过程中发生错误: {str(e)}"
    
    elif param.get("type") == 'url':
        try:
            request_json = json.loads(param['request'])
        except json.JSONDecodeError:
            return "提供的 request 模板不是合法的 JSON 格式，请检查后重试"
        
        try:
            # 获取要测试的URL或路径
            test_value = param.get('value', '')
            if not test_value:
                return "请提供需要测试的URL或文件路径"
            
            # 如果是URL，生成路径组合
            if test_value.startswith("http"):
                payload = generate_path_combinations(urllib3.util.parse_url(test_value).path)
            else:
                payload = [test_value]
            
            # 存储测试结果
            results = {}
            result_info = []
            results_lock = Lock()
            
            def test_url_payload(test_payload):
                if config.FLAG:
                    return
                try:
                    # 构造新的请求
                    new_request = json.loads(param['request'].replace("{LFI}", str(test_payload)))
                    
                    # 发送请求并获取响应
                    new_response = request.run(new_request)
                    
                    # 简化响应内容，将测试值替换为{payload}
                    simplify_content = new_response['content'].replace(str(test_payload), "{payload}")
                    
                    # 线程安全地更新结果
                    with results_lock:
                        response_found = False
                        for existing_response, values in results.items():
                            if simplify_content == existing_response:
                                results[existing_response].append(str(test_payload))
                                response_found = True
                                break
                        
                        # 如果是新的响应，创建新条目
                        if not response_found:
                            results[simplify_content] = [str(test_payload)]
                except Exception as e:
                    print(f"URL测试载荷 {test_payload} 出错: {str(e)}")
            
            # 使用10并发进行模糊测试
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                futures = [executor.submit(test_url_payload, test_payload) for test_payload in payload]
                concurrent.futures.wait(futures)
            
            # 格式化结果信息
            for k in results:
                result_info.append(f"载荷 【{','.join(results[k])}】: {k}\n")
            
            return result_info
            
        except Exception as e:
            return f"URL测试过程中发生错误: {str(e)}"
    
    else:
        return "不支持的测试类型"

