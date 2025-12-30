FROM python:3.9-slim

WORKDIR /app

# 复制依赖并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制当前目录下所有文件
COPY . .

# 暴露 Flask 默认端口
EXPOSE 5000

# 运行程序 (假设你的文件名叫 app.py)
CMD ["python", "app.py"]