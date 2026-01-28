#!/bin/bash
# 飞书插件后端一键部署脚本
# 使用方法: sudo bash deploy-backend.sh

set -e

echo "========================================="
echo "飞书签名插件 - 后端自动部署脚本"
echo "========================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 项目目录
PROJECT_DIR="/var/www/feishu/feishu-plugin"
BACKEND_DIR="$PROJECT_DIR/backend"

echo -e "${YELLOW}[1/8] 检查系统环境...${NC}"
# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用 sudo 运行此脚本${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 系统检查通过${NC}"

echo -e "${YELLOW}[2/8] 安装系统依赖...${NC}"
apt update
apt install -y python3 python3-pip python3-venv mysql-server redis-server

echo -e "${GREEN}✓ 系统依赖安装完成${NC}"

echo -e "${YELLOW}[3/8] 配置 MySQL 数据库...${NC}"
# 启动 MySQL
systemctl start mysql
systemctl enable mysql

# 设置 MySQL 密码并创建数据库
mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'feishu123';" || true
mysql -uroot -pfeishu123 -e "CREATE DATABASE IF NOT EXISTS feishu CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

echo -e "${GREEN}✓ MySQL 配置完成${NC}"

echo -e "${YELLOW}[4/8] 配置 Redis...${NC}"
systemctl start redis
systemctl enable redis

echo -e "${GREEN}✓ Redis 配置完成${NC}"

echo -e "${YELLOW}[5/8] 创建 Python 虚拟环境...${NC}"
cd $BACKEND_DIR

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

echo -e "${GREEN}✓ 虚拟环境创建完成${NC}"

echo -e "${YELLOW}[6/8] 安装 Python 依赖...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}✓ Python 依赖安装完成${NC}"

echo -e "${YELLOW}[7/8] 配置 systemd 服务...${NC}"

# 获取当前用户
CURRENT_USER=$(logname || echo "ubuntu")

# 创建 systemd 服务文件
cat > /etc/systemd/system/feishu-backend.service << EOF
[Unit]
Description=Feishu Plugin Backend
After=network.target mysql.service redis.service

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/.venv/bin"
Environment="IS_STORE_APP=true"
ExecStart=$BACKEND_DIR/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 重新加载 systemd
systemctl daemon-reload

echo -e "${GREEN}✓ systemd 服务配置完成${NC}"

echo -e "${YELLOW}[8/8] 启动后端服务...${NC}"
systemctl start feishu-backend
systemctl enable feishu-backend

# 等待服务启动
sleep 3

# 检查服务状态
if systemctl is-active --quiet feishu-backend; then
    echo -e "${GREEN}✓ 后端服务启动成功!${NC}"
    echo ""
    echo "========================================="
    echo -e "${GREEN}部署完成!${NC}"
    echo "========================================="
    echo ""
    echo "后端 API 地址: http://$(hostname -I | awk '{print $1}'):8000"
    echo "API 文档: http://$(hostname -I | awk '{print $1}'):8000/docs"
    echo ""
    echo "查看服务状态: sudo systemctl status feishu-backend"
    echo "查看日志: sudo journalctl -u feishu-backend -f"
    echo ""
else
    echo -e "${RED}✗ 后端服务启动失败!${NC}"
    echo "请查看日志: sudo journalctl -u feishu-backend -xe"
    exit 1
fi
