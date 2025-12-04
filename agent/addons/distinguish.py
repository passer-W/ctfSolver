from addons import request
import difflib

def run(request_json_1, request_json_2):
    
    # 分别发送两个请求
    response1 = request.run(request_json_1)
    response2 = request.run(request_json_2)
    
    # 获取两个响应的content内容
    content1 = response1.get('content', '')
    content2 = response2.get('content', '')
    
    # 使用difflib比较两个字符串
    differ = difflib.Differ()
    diff = list(differ.compare(content1.splitlines(True), content2.splitlines(True)))
    
    return {
        "add": ''.join([i for i in diff if i.startswith('+')]),
        "remove": ''.join([i for i in diff if i.startswith('-')]),
        "new_response": response2
    }
