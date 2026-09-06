#!/bin/bash
# 运行 Docker 容器

echo "🚀 启动 Code Agent 容器..."

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "❌ 错误：找不到 .env 文件"
    echo "请复制 .env.example 为 .env 并填入 API Key"
    exit 1
fi

# 使用 docker-compose 启动
docker-compose up -d

echo ""
echo "✅ 容器启动成功！"
echo ""
echo "查看日志："
echo "  docker-compose logs -f code-agent"
echo ""
echo "停止容器："
echo "  docker-compose down"

