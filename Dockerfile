# Dockerfile
FROM python:3.13-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    curl \
    zip \
    unzip \
    wget \
    gnupg \
    ca-certificates \
    # weasyprint 依赖
    libgirepository1.0-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# 安装 Chromium 浏览器和 ChromeDriver（支持 ARM64）
RUN apt-get update \
    && apt-get install -y chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . .

# 创建虚拟环境（模拟 run.sh 的环境）
RUN python -m venv venv

# 激活虚拟环境并安装依赖
RUN . venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

# 设置环境变量（按 run.sh 的配置）
ENV PYTHONPATH=/app
ENV VIRTUAL_ENV=/app/venv
ENV PATH="/app/venv/bin:$PATH"

# 设置 Gemini API Key 环境变量（可在运行时覆盖）
ENV GEMINI_API_KEY=""

# 创建必要的目录
RUN mkdir -p /app/output /app/data /app/logs

# 创建启动脚本（模拟 run.sh 的功能）
RUN echo '#!/bin/bash\n\
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)\n\
source "$SCRIPT_DIR/venv/bin/activate"\n\
export PYTHONPATH="$SCRIPT_DIR"\n\
echo "🚀 启动投资分析系统..."\n\
echo "📁 工作目录: $SCRIPT_DIR"\n\
echo "📦 PYTHONPATH: $PYTHONPATH"\n\
echo "📂 输出目录: /app/output"\n\
echo "=" * 50\n\
python main.py' > /app/start.sh && chmod +x /app/start.sh

# 设置入口点
ENTRYPOINT ["/app/start.sh"] 