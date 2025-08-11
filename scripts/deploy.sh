#!/bin/bash

# 投资分析系统自动部署脚本
# 使用方式: ./scripts/deploy.sh [commit_message]

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# 检查依赖
check_dependencies() {
    print_info "检查依赖..."
    
    if ! command -v git &> /dev/null; then
        print_error "Git 未安装"
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装"
        exit 1
    fi
    
    print_success "依赖检查通过"
}

# 本地测试
local_test() {
    print_info "开始本地测试..."
    
    # 构建镜像
    print_info "构建 Docker 镜像..."
    docker build -t investment-analysis:local-test .
    
    # 运行 CI 自检
    print_info "运行 CI 自检..."
    if [ -f "scripts/ci_check.sh" ]; then
        chmod +x scripts/ci_check.sh
        scripts/ci_check.sh investment-analysis:local-test
    else
        print_error "找不到 CI 自检脚本: scripts/ci_check.sh"
        exit 1
    fi
    
    print_success "本地测试通过"
}

# Git 操作
git_operations() {
    local commit_msg="${1:-自动部署: $(date +'%Y-%m-%d %H:%M:%S')}"
    
    print_info "执行 Git 操作..."
    
    # 检查是否有未提交的更改
    if ! git diff-index --quiet HEAD --; then
        print_info "检测到未提交的更改，正在提交..."
        git add .
        git commit -m "$commit_msg"
        print_success "代码已提交"
    else
        print_info "没有新的更改需要提交"
    fi
    
    # 推送到远程仓库
    print_info "推送到 GitHub..."
    git push origin main
    print_success "代码已推送到 GitHub"
}

# 显示部署结果
show_deployment_info() {
    local repo_url=$(git config --get remote.origin.url)
    local repo_name=$(basename -s .git "$repo_url")
    local username=$(echo "$repo_url" | sed -n 's/.*github.com[:/]\([^/]*\)\/.*/\1/p')
    
    print_success "部署启动成功！"
    echo
    print_info "GitHub Actions 工作流已触发"
    echo "🔗 查看构建状态: https://github.com/$username/$repo_name/actions"
    echo
    print_info "部署完成后，镜像将发布到:"
    echo "📦 ghcr.io/$username/investment-analysis:latest"
    echo
    print_info "使用部署的镜像:"
    echo "docker pull ghcr.io/$username/investment-analysis:latest"
    echo "docker run -it --name investment-analysis-container \\"
    echo "  -v \$(pwd)/output:/app/output \\"
    echo "  -v \$(pwd)/data:/app/data \\"
    echo "  -e GEMINI_API_KEY=your_api_key \\"
    echo "  ghcr.io/$username/investment-analysis:latest"
}

# 主函数
main() {
    echo "🚀 投资分析系统自动部署"
    echo "================================"
    
    # 获取提交信息
    local commit_message="$1"
    if [ -z "$commit_message" ]; then
        echo "请输入提交信息 (回车使用默认信息):"
        read -r user_input
        if [ -n "$user_input" ]; then
            commit_message="$user_input"
        fi
    fi
    
    # 执行部署流程
    check_dependencies
    local_test
    git_operations "$commit_message"
    show_deployment_info
    
    print_success "自动部署脚本执行完成！"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 