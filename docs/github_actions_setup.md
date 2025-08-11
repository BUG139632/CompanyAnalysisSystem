# GitHub Actions 自动部署设置指南

## 🚀 概述

本项目已配置了完整的 GitHub Actions 自动部署工作流，支持：

- ✅ 自动构建 Docker 镜像
- ✅ 运行自动化测试
- ✅ 代码质量检查
- ✅ 自动发布到 GitHub Container Registry
- ✅ 创建版本发布
- ✅ 生成部署摘要

## 📋 设置步骤

### 1. 创建 GitHub 仓库

```bash
# 初始化 Git 仓库
git init

# 添加所有文件
git add .

# 首次提交
git commit -m "Initial commit: 投资分析系统"

# 设置主分支
git branch -M main

# 添加远程仓库
git remote add origin https://github.com/yourusername/investment-analysis.git

# 推送到 GitHub
git push -u origin main
```

### 2. 启用 GitHub Actions

1. 在 GitHub 仓库页面，点击 **Actions** 标签
2. GitHub 会自动检测到 `.github/workflows/deploy.yml` 文件
3. 点击 **Enable Actions** 启用工作流

### 3. 配置权限

**重要：** 确保 GitHub Actions 有权限推送到 Container Registry：

1. 进入仓库 **Settings** → **Actions** → **General**
2. 在 **Workflow permissions** 部分，选择：
   - ✅ **Read and write permissions**
   - ✅ **Allow GitHub Actions to create and approve pull requests**

### 4. 测试自动部署

推送代码到 `main` 分支即可触发自动部署：

```bash
# 使用内置部署脚本
./scripts/deploy.sh "添加 GitHub Actions 自动部署"

# 或者手动推送
git add .
git commit -m "测试自动部署"
git push origin main
```

## 🔧 工作流说明

### 触发条件

- 推送到 `main` 或 `master` 分支
- 创建 Pull Request
- 手动触发（在 Actions 页面）

### 工作流程

1. **构建和测试** (`build-and-test`)
   - 检出代码
   - 设置 Python 3.13 环境
   - 登录到 GitHub Container Registry
   - 构建并推送测试镜像到注册表
   - 使用推送的镜像运行基本功能测试
   - 运行代码质量检查
   - 上传构建日志
   - 输出测试镜像的 digest 和标签

2. **部署镜像** (`deploy`)
   - 直接使用已测试通过的镜像
   - 将测试镜像重新标记为 `latest`
   - 推送 `latest` 镜像
   - 生成部署摘要
   - 仅在推送到 `main` 分支时执行

3. **创建发布** (`release`)
   - 自动生成版本标签
   - 创建 GitHub Release
   - 包含镜像使用说明
   - 仅在推送到 `main` 分支时执行

### 🚀 优化特性

- **避免重复构建**: 测试阶段构建一次，部署阶段直接使用
- **提高可靠性**: 部署的镜像就是通过测试的镜像
- **加快部署速度**: 部署阶段只需重新标记镜像，无需重新构建
- **完整的可追溯性**: 每个构建都有唯一的测试镜像标签

### 镜像标签策略

- `latest` - 最新的主分支部署版本（已通过所有测试）
- `test-{RUN_NUMBER}` - 构建和测试阶段的临时镜像
- `main-{SHA}` - 特定提交的版本
- `v{YYYY.MM.DD}-{SHA}` - 发布版本标签

**工作流程:**
1. 构建阶段: 创建 `test-{RUN_NUMBER}` 镜像并运行测试
2. 部署阶段: 将通过测试的镜像重新标记为 `latest`
3. 发布阶段: 创建带版本号的发布标签

## 📦 使用部署的镜像

### 拉取最新镜像

```bash
docker pull ghcr.io/yourusername/investment-analysis:latest
```

### 运行容器

```bash
# 设置 API Key
export GEMINI_API_KEY=your_gemini_api_key

# 运行容器
docker run -it --name investment-analysis-container \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/data:/app/data \
  -e GEMINI_API_KEY=$GEMINI_API_KEY \
  ghcr.io/yourusername/investment-analysis:latest
```

### 使用 Docker Compose

```yaml
# docker-compose.deploy.yml
version: '3.8'

services:
  investment-analysis:
    image: ghcr.io/yourusername/investment-analysis:latest
    container_name: investment-analysis-container
    volumes:
      - ./output:/app/output
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - PYTHONPATH=/app
      - PYTHONUNBUFFERED=1
      - GEMINI_API_KEY=${GEMINI_API_KEY:-}
    stdin_open: true
    tty: true
    restart: unless-stopped
```

```bash
# 使用部署的镜像
GEMINI_API_KEY=your_api_key docker-compose -f docker-compose.deploy.yml up
```

## 🛠️ 自定义配置

### 修改工作流

编辑 `.github/workflows/deploy.yml` 可以自定义：

- 触发条件
- 测试步骤
- 部署目标
- 镜像标签策略

### 本地部署脚本

使用 `scripts/deploy.sh` 脚本可以：

```bash
# 基本使用
./scripts/deploy.sh

# 指定提交信息
./scripts/deploy.sh "修复分析报告输出问题"

# 脚本会自动：
# 1. 检查依赖
# 2. 本地测试
# 3. 提交代码
# 4. 推送到 GitHub
# 5. 触发自动部署
```

## 📊 监控部署

### 查看构建状态

1. GitHub 仓库页面 → **Actions** 标签
2. 查看最新的工作流运行
3. 点击具体的运行查看详细日志

### 查看部署的镜像

1. GitHub 仓库页面 → **Packages** 标签
2. 查看 `investment-analysis` 包
3. 查看不同版本的镜像

### 查看发布版本

1. GitHub 仓库页面 → **Releases** 标签
2. 查看自动创建的发布版本
3. 下载特定版本或查看更新说明

## 🔍 故障排除

### 构建失败

1. 检查 Actions 页面的错误日志
2. 常见问题：
   - 依赖包版本冲突
   - Docker 构建超时
   - 权限不足

### 推送镜像失败

1. 确认 GitHub Actions 权限设置正确
2. 检查 `GITHUB_TOKEN` 是否有效
3. 验证仓库名称和用户名

### 本地测试失败

```bash
# 手动测试构建
docker build -t test .

# 检查依赖
docker run --rm test python -c "import pandas, numpy, requests"

# 查看详细错误
docker run --rm test python main.py --help
```

## 📝 最佳实践

1. **提交前本地测试**：使用 `./scripts/deploy.sh` 自动测试
2. **语义化提交信息**：便于追踪和回滚
3. **定期更新依赖**：保持安全性
4. **监控资源使用**：GitHub Actions 有使用限制
5. **备份重要数据**：output 目录数据需要手动备份

## 🎯 下一步

- [ ] 设置 GitHub Secrets 管理敏感信息
- [ ] 配置多环境部署（开发/测试/生产）
- [ ] 添加自动化测试覆盖率报告
- [ ] 集成代码质量检查工具
- [ ] 设置部署通知（邮件/Slack） 