import importlib

def execute_tool(tool_name, *args, **kwargs):
    """根据工具名称动态调用对应addon的run函数"""
    try:
        # 构建addon模块的导入路径
        addon_path = f"addons.{tool_name}"
        
        # 动态导入对应的addon模块
        module = importlib.import_module(addon_path)
        
        # 调用模块中的run函数
        if hasattr(module, 'run'):
            return module.run(*args, **kwargs)
        else:
            raise AttributeError(f"工具 {tool_name} 中未找到run()函数")
            
    except ImportError:
        raise ImportError(f"未找到工具 {tool_name} 对应的addon模块")
    except Exception as e:
        raise e
        raise Exception(f"执行工具 {tool_name} 时发生错误: {str(e)}")


