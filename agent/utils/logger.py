import logging
from datetime import datetime



# 配置日志格式
def setup_logger():
    # 自定义日志格式
    log_format = '[%(levelname)s] %(asctime)s [%(name)s:%(filename)s:%(lineno)d] %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # 创建logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 设置格式器
    formatter = logging.Formatter(log_format, date_format)
    console_handler.setFormatter(formatter)
    
    # 添加处理器到logger
    logger.addHandler(console_handler)
    
    return logger

# 获取logger实例
logger = setup_logger()
