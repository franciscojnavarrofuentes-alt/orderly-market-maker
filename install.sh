#!/bin/bash
# ONE-COMMAND INSTALLER - Orderly Market Maker Bot
# Usage: curl -sSL https://raw.githubusercontent.com/franciscojnavarrofuentes-alt/orderly-market-maker/main/install.sh | bash

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

clear
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}   Orderly Market Maker - Auto Installer${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}✗ Please run as root (or use sudo)${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/8]${NC} Updating system..."
apt update -qq && apt upgrade -y -qq
echo -e "${GREEN}✓${NC} System updated"

echo -e "${YELLOW}[2/8]${NC} Installing dependencies..."
DEBIAN_FRONTEND=noninteractive apt install -y -qq python3 python3-pip python3-venv git screen htop curl ufw >/dev/null 2>&1
echo -e "${GREEN}✓${NC} Dependencies installed"

echo -e "${YELLOW}[3/8]${NC} Checking Python..."
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if [ "${PYTHON_VERSION//./}" -lt "310" ]; then
    echo -e "${RED}✗ Python 3.10+ required. Current: $PYTHON_VERSION${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Python $(python3 --version)"

echo -e "${YELLOW}[4/8]${NC} Cloning repository..."
cd /root
if [ -d "orderly-market-maker" ]; then
    cd orderly-market-maker
    git pull -q origin main
else
    git clone -q https://github.com/franciscojnavarrofuentes-alt/orderly-market-maker.git
    cd orderly-market-maker
fi
echo -e "${GREEN}✓${NC} Repository ready"

echo -e "${YELLOW}[5/8]${NC} Setting up Python environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo -e "${GREEN}✓${NC} Python packages installed"

echo -e "${YELLOW}[6/8]${NC} Configuring bot..."
if [ ! -f ".env" ]; then
    cp .env.example .env
fi
chmod 600 .env
echo -e "${GREEN}✓${NC} Configuration file ready"

echo -e "${YELLOW}[7/8]${NC} Setting up firewall..."
ufw --force enable >/dev/null 2>&1
ufw allow OpenSSH >/dev/null 2>&1
echo -e "${GREEN}✓${NC} Firewall configured"

echo -e "${YELLOW}[8/8]${NC} Creating systemd service..."
cat > /etc/systemd/system/mm-bot.service << 'EOFSERVICE'
[Unit]
Description=Orderly Market Maker Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/orderly-market-maker
Environment="PYTHONPATH=/root/orderly-market-maker/src"
ExecStart=/root/orderly-market-maker/.venv/bin/python -m mm.main
Restart=always
RestartSec=10
StandardOutput=append:/root/orderly-market-maker/mm_run.log
StandardError=append:/root/orderly-market-maker/mm_run.log

[Install]
WantedBy=multi-user.target
EOFSERVICE

systemctl daemon-reload
systemctl enable mm-bot >/dev/null 2>&1
echo -e "${GREEN}✓${NC} Systemd service created"

# Create management commands
cat > /usr/local/bin/mm << 'EOFMM'
#!/bin/bash
case "$1" in
    start)
        systemctl start mm-bot
        echo "✓ Bot started"
        ;;
    stop)
        systemctl stop mm-bot
        echo "✓ Bot stopped"
        ;;
    restart)
        systemctl restart mm-bot
        echo "✓ Bot restarted"
        ;;
    status)
        systemctl status mm-bot --no-pager | head -20
        echo ""
        echo "Recent logs:"
        tail -10 /root/orderly-market-maker/mm_run.log
        ;;
    logs)
        tail -f /root/orderly-market-maker/mm_run.log
        ;;
    config)
        nano /root/orderly-market-maker/.env
        ;;
    trades)
        grep "✓ TAKE PROFIT\|Position changed" /root/orderly-market-maker/mm_run.log | tail -20
        ;;
    update)
        cd /root/orderly-market-maker
        git pull origin main
        source .venv/bin/activate
        pip install -q -r requirements.txt
        systemctl restart mm-bot
        echo "✓ Bot updated and restarted"
        ;;
    *)
        echo "Orderly Market Maker Bot - Control"
        echo ""
        echo "Usage: mm <command>"
        echo ""
        echo "Commands:"
        echo "  start    - Start the bot"
        echo "  stop     - Stop the bot"
        echo "  restart  - Restart the bot"
        echo "  status   - Show bot status"
        echo "  logs     - View live logs"
        echo "  config   - Edit configuration"
        echo "  trades   - Show recent trades"
        echo "  update   - Update bot from GitHub"
        ;;
esac
EOFMM

chmod +x /usr/local/bin/mm

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Installation Complete!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT: Configure your credentials${NC}"
echo ""
echo "Run this command to edit config:"
echo -e "${BLUE}  mm config${NC}"
echo ""
echo "Required settings:"
echo "  • ORDERLY_ACCOUNT_ID"
echo "  • ORDERLY_KEY"
echo "  • ORDERLY_SECRET"
echo "  • DRY_RUN=true  (test first!)"
echo ""
echo -e "${YELLOW}📋 Quick Commands:${NC}"
echo -e "  ${BLUE}mm config${NC}   - Edit credentials"
echo -e "  ${BLUE}mm start${NC}    - Start the bot"
echo -e "  ${BLUE}mm status${NC}   - Check status"
echo -e "  ${BLUE}mm logs${NC}     - View live logs"
echo -e "  ${BLUE}mm stop${NC}     - Stop the bot"
echo ""
echo -e "${YELLOW}🧪 Testing (recommended):${NC}"
echo "  1. mm config  → Set credentials + DRY_RUN=true"
echo "  2. cd /root/orderly-market-maker"
echo "  3. source .venv/bin/activate"
echo "  4. PYTHONPATH=src python3 -m mm.main"
echo "  5. Press Ctrl+C if working correctly"
echo ""
echo -e "${YELLOW}🚀 Production:${NC}"
echo "  1. mm config  → Change DRY_RUN=false"
echo "  2. mm start   → Start bot"
echo "  3. mm logs    → Monitor"
echo ""
echo -e "${GREEN}Ready to trade! 🎯${NC}"
echo ""
