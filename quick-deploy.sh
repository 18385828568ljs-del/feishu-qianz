#!/bin/bash
# 飞书插件快速部署脚本 (简化版)
# 使用方法: sudo bash quick-deploy.sh

set -e

echo "========================================="
echo "飞书签名插件 - 快速部署脚本"
echo "========================================="

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 项目目录
PROJECT_DIR="/var/www/feishu/feishu-plugin"

echo -e "${YELLOW}步骤 1: 创建项目目录...${NC}"
mkdir -p $PROJECT_DIR/backend
mkdir -p $PROJECT_DIR/frontend/dist
mkdir -p $PROJECT_DIR/admin/dist

echo -e "${GREEN}✓ 目录创建完成${NC}"
echo ""
echo "========================================="
echo "接下来请手动操作:"
echo "========================================="
echo ""
echo "1. 使用 WinSCP 上传文件:"
echo "   - 本地 d:\\feishu1\\backend\\*.py → 服务器 $PROJECT_DIR/backend/"
echo "   - 本地 d:\\feishu1\\backend\\requirements.txt → 服务器 $PROJECT_DIR/backend/"
echo "   - 本地 d:\\feishu1\\backend\\.env → 服务器 $PROJECT_DIR/backend/"
echo ""
echo "2. 上传完成后,运行部署脚本:"
echo "   cd $PROJECT_DIR"
echo "   sudo bash deploy-backend.sh"
echo ""
echo "========================================="
