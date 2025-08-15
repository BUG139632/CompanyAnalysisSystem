# 使用官方Selenium Chrome镜像
FROM --platform=linux/amd64 selenium/standalone-chrome:latest

# 切换到root用户
USER root

# 安装Python和必要的依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        build-essential \
        git \
        fonts-noto-cjk \
        fonts-wqy-zenhei && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY . .

# 创建并激活虚拟环境
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r requirements.txt

# 创建WebDriver辅助脚本
RUN echo 'from selenium import webdriver\n\
from selenium.webdriver.chrome.options import Options\n\
\n\
def get_chrome_driver():\n\
    """获取配置好的Chrome WebDriver实例"""\n\
    options = Options()\n\
    options.add_argument("--headless")\n\
    options.add_argument("--no-sandbox")\n\
    options.add_argument("--disable-dev-shm-usage")\n\
    options.add_argument("--disable-gpu")\n\
    \n\
    driver = webdriver.Chrome(options=options)\n\
    return driver\n\
' > /app/webdriver_helper.py

# 环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV DISPLAY=:99

# 切换回非root用户运行
USER 1200:1201

ENTRYPOINT ["python3", "main.py"]