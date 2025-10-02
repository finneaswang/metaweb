#!/bin/bash

echo "======================================"
echo "MetaWeb 部署脚本"
echo "======================================"
echo ""

# 检查是否在正确的目录
if [ ! -f "docker-compose.prod.yml" ]; then
    echo "❌ 错误：请在项目根目录运行此脚本"
    exit 1
fi

# 拉取最新代码
echo "📥 拉取最新代码..."
git pull origin main

if [ $? -ne 0 ]; then
    echo "❌ Git pull 失败"
    exit 1
fi

# 检查环境变量文件
if [ ! -f ".env.production" ]; then
    echo "⚠️  未找到 .env.production 文件"
    echo "📝 请复制 .env.production.example 并配置："
    echo "   cp .env.production.example .env.production"
    echo "   然后编辑 .env.production 填入实际配置"
    exit 1
fi

# 停止旧容器
echo "🛑 停止旧容器..."
docker-compose -f docker-compose.prod.yml down

# 构建新镜像
echo "🔨 构建 Docker 镜像..."
docker-compose -f docker-compose.prod.yml build --no-cache

if [ $? -ne 0 ]; then
    echo "❌ Docker 构建失败"
    exit 1
fi

# 启动新容器
echo "🚀 启动容器..."
docker-compose -f docker-compose.prod.yml up -d

if [ $? -ne 0 ]; then
    echo "❌ 容器启动失败"
    exit 1
fi

# 检查容器状态
echo ""
echo "✅ 部署完成！"
echo ""
echo "📊 容器状态："
docker-compose -f docker-compose.prod.yml ps
echo ""
echo "📝 查看日志："
echo "   docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "🌐 访问地址："
echo "   http://服务器IP:3000"
echo ""
echo "======================================"
