#!/bin/bash
# 构建 Docker 镜像

echo "🐳 构建 Docker 镜像..."
docker build -t code-agent:latest .

echo ""
echo "✅ 构建完成！"
echo ""
echo "镜像信息："
docker images | grep code-agent
