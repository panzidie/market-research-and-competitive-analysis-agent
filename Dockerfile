FROM python:3.11-slim

# 安全：非 root 用户运行
RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建数据目录
RUN mkdir -p data/raw data/processed data/reports data/vector_store

# 切换非 root 用户
USER app

ENTRYPOINT ["python", "agent.py"]
