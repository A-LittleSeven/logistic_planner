# 使用官方 Python 3.12 官方精简镜像作为基础镜像
FROM python:3.12-slim

# 设置 Python 环境变量：禁止生成 .pyc 缓存文件，开启无缓冲标准输出（便于实时查看 docker logs）
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 工作目录
WORKDIR /app

# 安装必要的系统运行时依赖
# - libgomp1: Google OR-Tools 和 Scipy/Numpy 底层 OpenMP 并行计算依赖
# - curl: 用于 Docker 容器健康检查 (HEALTHCHECK)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 利用 Docker 层缓存：先单独复制 requirements.txt 并安装依赖
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# 复制后端业务源码
COPY . .

# 创建数据持久化目录 (SQLite 数据库挂载点)
RUN mkdir -p /app/data

# 默认指定 SQLite 数据库存储在持久化卷路径中
ENV DATABASE_PATH=/app/data/logistic.db

# 暴露 FastAPI 服务端口
EXPOSE 8000

# 容器健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动 Uvicorn 服务（生产环境监听 0.0.0.0，关闭自动热重载以节约资源）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
