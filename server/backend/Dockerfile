# 使用官方 Python 轻量镜像
FROM python:3.11-slim

# 避免生成 .pyc、开启无缓冲
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 工作目录
WORKDIR /app

# 先复制依赖清单并安装
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip install --no-cache-dir celery redis -i https://pypi.tuna.tsinghua.edu.cn/simple


# 复制项目代码
COPY . /app

# 暴露端口
EXPOSE 5000

# 运行 Flask 应用
CMD ["python", "app.py"]