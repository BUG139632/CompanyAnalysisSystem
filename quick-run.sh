#!/bin/bash

echo "🚀 快速启动投资分析系统"
echo "=" * 40

# 检查是否已构建镜像
if [[ "$(docker images -q investment-analysis 2> /dev/null)" == "" ]]; then
    echo "🔨 首次运行，正在构建 Docker 镜像..."
    docker build -t investment-analysis .
fi

# 创建目录
mkdir -p output data logs

echo "📁 目录结构:"
echo "   - 输出目录: $(pwd)/output"
echo "   - 数据目录: $(pwd)/data"
echo "   - 日志目录: $(pwd)/logs"

echo ""
echo "🎯 启动分析系统..."
echo "💡 输入公司名称后，结果将自动保存到 output/ 目录"
echo "💡 提示：如需使用 Gemini API，请设置环境变量 GEMINI_API_KEY"
echo "   例如：GEMINI_API_KEY=your_key_here ./quick-run.sh"
echo "=" * 40

# 运行容器
docker run -it \
    -v "$(pwd)/output:/app/output" \
    -v "$(pwd)/data:/app/data" \
    -v "$(pwd)/logs:/app/logs" \
    -v "$(pwd)/config:/app/config" \
    -e GEMINI_API_KEY="${GEMINI_API_KEY:-}" \
    investment-analysis

echo ""
echo "✅ 分析完成！"
echo "📁 查看结果文件: ls output/" 