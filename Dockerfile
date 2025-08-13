# Dockerfile
FROM python:3.11-slim-bookworm

# 工作目录
WORKDIR /app

# 安装系统依赖（最小化）
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl \
        ca-certificates \
        wget \
        unzip \
        # weasyprint 运行时所需的轻量库，如不使用 PDF 可删除 \
        libpango1.0-0 \
        libcairo2 \
        gobject-introspection \
        libgdk-pixbuf-2.0-0 \
        libffi-dev; \
    rm -rf /var/lib/apt/lists/*

# 可选：如需 Selenium，可取消下方注释安装 Chromium
# RUN apt-get update && apt-get install -y --no-install-recommends chromium && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . .

# 创建并激活虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r requirements.txt

# 运行配置
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV GEMINI_API_KEY=""

ENTRYPOINT ["python", "main.py"] 