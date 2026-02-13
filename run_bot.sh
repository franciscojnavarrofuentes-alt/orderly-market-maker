#!/bin/bash
# Safe bot launcher - ensures only one instance runs

LOCKFILE="/tmp/mm_bot.lock"
PIDFILE="/tmp/mm_bot.pid"

# Function to cleanup on exit
cleanup() {
    echo "Cleaning up..."
    rm -f "$LOCKFILE" "$PIDFILE"
    # Cancel all orders on exit
    cd /Users/paconavarro/MM-bot
    python3 -c "
import asyncio, sys
sys.path.insert(0, 'src')
from mm.config import load_config
from mm.client import OrderlyClient

async def main():
    config = load_config()
    async with OrderlyClient(config.base_url, config.account_id, config.api_key, config.api_secret) as client:
        print('Canceling all orders on exit...')
        await client.cancel_all(config.symbol)
        print('✓ Orders canceled')

asyncio.run(main())
" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

# Check if already running
if [ -f "$LOCKFILE" ]; then
    OLD_PID=$(cat "$PIDFILE" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "ERROR: Bot already running (PID: $OLD_PID)"
        echo "To stop it, run: kill $OLD_PID"
        exit 1
    else
        echo "Removing stale lockfile..."
        rm -f "$LOCKFILE" "$PIDFILE"
    fi
fi

# Kill any orphaned bot processes
echo "Checking for orphaned bot processes..."
ORPHANS=$(ps aux | grep -i "[p]ython.*mm.main" | awk '{print $2}')
if [ -n "$ORPHANS" ]; then
    echo "Killing orphaned processes: $ORPHANS"
    echo "$ORPHANS" | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# Create lockfile
touch "$LOCKFILE"
echo $$ > "$PIDFILE"

echo "Starting Market Maker Bot..."
echo "Lockfile: $LOCKFILE"
echo "PID: $$"
echo "Preventing Mac from sleeping..."
echo "----------------------------------------"

# Change to bot directory and run
cd /Users/paconavarro/MM-bot
export PYTHONPATH="${PYTHONPATH}:src"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run with caffeinate to prevent Mac from sleeping
caffeinate -i python3 -m mm.main

# Cleanup happens automatically via trap
