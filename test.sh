#!/bin/bash
# 在 Docker 容器中运行测试

echo "🧪 在 Docker 容器中运行测试..."

docker-compose run --rm code-agent pytest tests/ -v

echo ""
echo "✅ 测试完成！"
