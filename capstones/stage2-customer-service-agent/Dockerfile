# 阶段二 Capstone · 最小部署镜像
# 构建：docker build -t cs-agent .
# 运行：docker run -p 8000:8000 -e DEEPSEEK_API_KEY=sk-xxx cs-agent
#       ⚠️ key 在**运行时**用 -e 注入，绝不写进 Dockerfile / 镜像（否则 key 随镜像泄露）。

# slim 基础镜像：够跑 Python，体积远小于完整版
FROM python:3.12-slim

WORKDIR /app

# 先拷依赖清单再装 —— 利用 Docker 层缓存：代码改动不会让依赖层重装
COPY requirements-deploy.txt .
RUN pip install --no-cache-dir -r requirements-deploy.txt

# 再拷业务代码（放后面，改代码只重建这一层，依赖层命中缓存）
COPY tools.py agent.py reflect.py policy_rag.py app.py ./

# 生产加固：用非 root 用户跑，缩小被攻破后的影响面
RUN useradd -m appuser
USER appuser

EXPOSE 8000

# --host 0.0.0.0：容器里必须监听所有网卡，不能是 127.0.0.1（否则容器外连不进来）
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
