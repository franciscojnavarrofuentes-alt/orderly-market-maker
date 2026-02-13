# VPS Deployment Guide

Complete guide to deploy the Orderly Market Maker bot on a VPS (Ubuntu/Debian).

## Prerequisites

- VPS with Ubuntu 20.04+ or Debian 11+
- At least 1GB RAM
- Python 3.10+
- SSH access to your VPS

## Step 1: Prepare VPS

SSH into your VPS:
```bash
ssh user@your-vps-ip
```

Update system:
```bash
sudo apt update && sudo apt upgrade -y
```

Install required packages:
```bash
sudo apt install -y python3 python3-pip python3-venv git screen htop
```

## Step 2: Clone Repository

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/MM-bot.git
cd MM-bot
```

## Step 3: Setup Python Environment

Create virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 4: Configure Bot

Copy and edit config:
```bash
cp .env.example .env
nano .env
```

Update with your credentials:
```env
ORDERLY_ACCOUNT_ID=your_account_id
ORDERLY_KEY=ed25519:your_key
ORDERLY_SECRET=ed25519:your_secret

SYMBOL=PERP_ETH_USDC
SPREAD_BPS=18
ORDER_SIZE_USD=60
REFRESH_INTERVAL=3
DRY_RUN=false
LOG_LEVEL=INFO
```

**Important:** Start with `DRY_RUN=true` for testing!

## Step 5: Test Run

Test the bot works:
```bash
PYTHONPATH=src python3 -m mm.main
```

You should see:
```
Starting Dynamic Loss-Protected Market Maker for PERP_ETH_USDC
Base spread: 18 bps, Size: $60
Strategy: Dynamic loss protection from order #1 + $0.08 take-profit
```

Stop with `Ctrl+C`.

## Step 6: Run in Background with Screen

### Option A: Using Screen (Recommended for beginners)

Start a screen session:
```bash
screen -S mm-bot
```

Run the bot:
```bash
cd ~/MM-bot
source .venv/bin/activate
./run_bot.sh
```

Detach from screen: Press `Ctrl+A` then `D`

Reattach to screen:
```bash
screen -r mm-bot
```

### Option B: Using nohup (Simpler but no live view)

```bash
cd ~/MM-bot
nohup ./run_bot.sh > mm_run.log 2>&1 &
```

Check if running:
```bash
ps aux | grep "python.*mm.main"
```

View logs:
```bash
tail -f mm_run.log
```

Stop the bot:
```bash
kill $(cat /tmp/mm_bot.pid)
```

## Step 7: Setup Systemd Service (Production)

For production, create a systemd service:

```bash
sudo nano /etc/systemd/system/mm-bot.service
```

Add this content:
```ini
[Unit]
Description=Orderly Market Maker Bot
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/MM-bot
Environment="PYTHONPATH=/home/YOUR_USERNAME/MM-bot/src"
ExecStart=/home/YOUR_USERNAME/MM-bot/.venv/bin/python -m mm.main
Restart=always
RestartSec=10
StandardOutput=append:/home/YOUR_USERNAME/MM-bot/mm_run.log
StandardError=append:/home/YOUR_USERNAME/MM-bot/mm_run.log

[Install]
WantedBy=multi-user.target
```

**Replace `YOUR_USERNAME` with your actual username.**

Enable and start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mm-bot
sudo systemctl start mm-bot
```

Check status:
```bash
sudo systemctl status mm-bot
```

View logs:
```bash
sudo journalctl -u mm-bot -f
```

Stop/restart:
```bash
sudo systemctl stop mm-bot
sudo systemctl restart mm-bot
```

## Monitoring

### Check Bot Status

```bash
cd ~/MM-bot
source .venv/bin/activate
python3 check_status.py
```

### Check Logs

```bash
tail -f mm_run.log
```

### Monitor Resources

```bash
htop
```

Look for the python process running `mm.main`.

### Check Position on Orderly

Visit: https://orderly.network/portfolio

## Troubleshooting

### Bot not starting

Check Python version:
```bash
python3 --version  # Should be 3.10+
```

Check dependencies:
```bash
source .venv/bin/activate
pip list
```

### Connection errors

Check firewall:
```bash
sudo ufw status
```

If firewall is active, allow outbound HTTPS:
```bash
sudo ufw allow out 443/tcp
```

### Out of Memory

Check memory usage:
```bash
free -h
```

If low, consider upgrading VPS or adding swap:
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Bot dies unexpectedly

Check system logs:
```bash
sudo journalctl -xe
```

Check if OOM killed it:
```bash
sudo dmesg | grep -i "killed process"
```

## Security Best Practices

1. **Use SSH key authentication** (disable password login):
   ```bash
   sudo nano /etc/ssh/sshd_config
   # Set: PasswordAuthentication no
   sudo systemctl restart sshd
   ```

2. **Enable firewall**:
   ```bash
   sudo ufw allow OpenSSH
   sudo ufw enable
   ```

3. **Keep system updated**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

4. **Protect .env file**:
   ```bash
   chmod 600 ~/MM-bot/.env
   ```

5. **Setup fail2ban** (optional but recommended):
   ```bash
   sudo apt install fail2ban
   sudo systemctl enable fail2ban
   ```

## Updating the Bot

Pull latest changes:
```bash
cd ~/MM-bot
git pull origin main
```

Restart bot:
```bash
# If using screen:
screen -r mm-bot
# Press Ctrl+C, then restart with ./run_bot.sh

# If using systemd:
sudo systemctl restart mm-bot

# If using nohup:
kill $(cat /tmp/mm_bot.pid)
nohup ./run_bot.sh > mm_run.log 2>&1 &
```

## Performance Optimization

### For High-Frequency Trading

Increase file descriptor limit:
```bash
sudo nano /etc/security/limits.conf
```

Add:
```
* soft nofile 65536
* hard nofile 65536
```

### Network Optimization

```bash
sudo sysctl -w net.ipv4.tcp_fin_timeout=30
sudo sysctl -w net.ipv4.tcp_tw_reuse=1
```

## Backup and Recovery

### Backup Configuration

```bash
# Backup .env file (encrypted)
tar -czf mm-bot-backup-$(date +%Y%m%d).tar.gz .env
```

### Recovery

If bot stops or VPS restarts:

1. SSH into VPS
2. Check if bot is running: `ps aux | grep mm.main`
3. If not, restart using systemd: `sudo systemctl start mm-bot`
4. Or manually: `cd ~/MM-bot && ./run_bot.sh`

## Cost Optimization

Recommended VPS providers:
- **DigitalOcean**: $6/month (Basic Droplet)
- **Linode**: $5/month (Nanode)
- **Vultr**: $5/month (Basic Instance)
- **Hetzner**: €4.51/month (CX11)

All have sufficient resources for this bot.

## Questions?

Check logs first:
```bash
tail -100 mm_run.log
```

Check bot status:
```bash
python3 check_status.py
```

If still stuck, check GitHub issues or create a new one.

---

**Pro Tip:** Use `screen` for easy management. You can detach/reattach anytime to check on the bot without stopping it.
