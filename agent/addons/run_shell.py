import os
import subprocess
import uuid
from config.config import TEMP_PATH

def run(params):
    """
    执行shell命令并返回结果
    :param params: 包含command字段的字典
    :return: 执行结果字符串
    """
    try:
        # 确保临时目录存在
        if not os.path.exists(TEMP_PATH):
            os.makedirs(TEMP_PATH)
            
        # 创建临时shell脚本文件
        temp_file = os.path.join(TEMP_PATH, f"{uuid.uuid4()}.sh")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(params["command"])
            
        # 设置文件权限为可执行
        os.chmod(temp_file, 0o755)
            
        # 执行shell脚本并获取输出
        result = subprocess.run(
            ["bash", temp_file],
            capture_output=True,
            text=True,
            timeout=5  # 设置超时时间为5秒
        )
        
        # 删除临时文件
        os.remove(temp_file)
        
        # 返回执行结果
        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error: {result.stderr}"
            
    except subprocess.TimeoutExpired:
        return "Error: 执行超时"
    except Exception as e:
        return f"Error: {str(e)}"
