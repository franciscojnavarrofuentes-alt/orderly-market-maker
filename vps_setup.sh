#!/bin/bash
# Automatic VPS Setup Script for Orderly Market Maker
# This script will install and configure everything needed

set -e  # Exit on any error

echo "=================================="
echo "Orderly Market Maker - VPS Setup"
echo "=================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root (use: sudo bash vps_setup.sh)"
    exit 1
fi

echo "Step 1: Updating system packages..."
apt update && apt upgrade -y
print_success "System updated"

echo ""
echo "Step 2: Installing required packages..."
apt install -y python3 python3-pip python3-venv git screen htop curl
print_success "Packages installed"

echo ""
echo "Step 3: Checking Python version..."
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
print_success "Python version: $(python3 --version)"

if [ "${PYTHON_VERSION//./}" -lt "310" ]; then
    print_error "Python 3.10+ required. Current version: $PYTHON_VERSION"
    exit 1
fi

echo ""
echo "Step 4: Cloning repository..."
if [ -d "/root/orderly-market-maker" ]; then
    print_warning "Repository already exists. Updating..."
    cd /root/orderly-market-maker
    git pull origin main
else
    cd /root
    git clone https://github.com/franciscojnavarrofuentes-alt/orderly-market-maker.git
    cd orderly-market-maker
fi
print_success "Repository ready"

echo ""
echo "Step 5: Setting up Python virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    print_success "Virtual environment created"
else
    print_warning "Virtual environment already exists"
fi

source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
print_success "Dependencies installed"

echo ""
echo "Step 6: Configuration setup..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    print_warning ".env file created from template"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠️  IMPORTANT: You need to edit .env with your credentials"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Run this command to edit:"
    echo "  nano /root/orderly-market-maker/.env"
    echo ""
    echo "Required settings:"
    echo "  - ORDERLY_ACCOUNT_ID=your_account_id"
    echo "  - ORDERLY_KEY=ed25519:your_key"
    echo "  - ORDERLY_SECRET=ed25519:your_secret"
    echo "  - DRY_RUN=true  (for testing first!)"
    echo ""
else
    print_warning ".env file already exists"
fi

echo ""
echo "Step 7: Setting up security..."
chmod 600 .env
print_success ".env file protected (chmod 600)"

# Setup firewall
if ! command -v ufw &> /dev/null; then
    apt install -y ufw
fi

ufw --force enable
ufw allow OpenSSH
print_success "Firewall configured"

echo ""
echo "Step 8: Creating systemd service..."

cat > /etc/systemd/system/mm-bot.service << 'EOF'
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
EOF

systemctl daemon-reload
systemctl enable mm-bot
print_success "Systemd service created and enabled"

echo ""
echo "Step 9: Creating management scripts..."

# Create start script
cat > /root/mm-start.sh << 'EOF'
#!/bin/bash
systemctl start mm-bot
echo "✓ Market maker bot started"
echo "View logs: sudo journalctl -u mm-bot -f"
EOF
chmod +x /root/mm-start.sh

# Create stop script
cat > /root/mm-stop.sh << 'EOF'
#!/bin/bash
systemctl stop mm-bot
echo "✓ Market maker bot stopped"
EOF
chmod +x /root/mm-stop.sh

# Create status script
cat > /root/mm-status.sh << 'EOF'
#!/bin/bash
echo "=== Bot Status ==="
systemctl status mm-bot --no-pager | head -20
echo ""
echo "=== Recent Logs ==="
tail -20 /root/orderly-market-maker/mm_run.log
echo ""
echo "Commands:"
echo "  Start:  /root/mm-start.sh"
echo "  Stop:   /root/mm-stop.sh"
echo "  Logs:   tail -f /root/orderly-market-maker/mm_run.log"
EOF
chmod +x /root/mm-status.sh

print_success "Management scripts created"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ VPS Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Next Steps:"
echo ""
echo "1. Edit configuration with your credentials:"
echo "   nano /root/orderly-market-maker/.env"
echo ""
echo "2. Test in DRY_RUN mode first:"
echo "   cd /root/orderly-market-maker"
echo "   source .venv/bin/activate"
echo "   PYTHONPATH=src python3 -m mm.main"
echo "   (Press Ctrl+C to stop)"
echo ""
echo "3. When ready, change DRY_RUN=false in .env"
echo ""
echo "4. Start the bot:"
echo "   /root/mm-start.sh"
echo ""
echo "📊 Monitoring Commands:"
echo "   Status:  /root/mm-status.sh"
echo "   Logs:    tail -f /root/orderly-market-maker/mm_run.log"
echo "   Stop:    /root/mm-stop.sh"
echo ""
echo "🔧 Bot location: /root/orderly-market-maker"
echo "📁 Logs location: /root/orderly-market-maker/mm_run.log"
echo ""
