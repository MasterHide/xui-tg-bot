#!/bin/bash
set -e
BOT_DIR="/opt/xui-tg-bot"
SERVICE_FILE="/etc/systemd/system/xui-tg-bot.service"
CONFIG_FILE="$BOT_DIR/config/config.json"
PYTHON=$(command -v python3 || echo "/usr/bin/python3")

if systemctl is-active --quiet xui-tg-bot; then
  echo "⚠️ Service already running. Stop or uninstall first."
  exit 1
fi

mkdir -p "$BOT_DIR/config"

# Download latest files directly from GitHub
echo "📥 Downloading bot files from GitHub..."
rm -rf "$BOT_DIR"
mkdir -p "$BOT_DIR"
curl -L https://github.com/MasterHide/xui-tg-bot/archive/refs/heads/main.zip -o /tmp/xui-tg-bot.zip
apt install -y unzip >/dev/null 2>&1
unzip -q /tmp/xui-tg-bot.zip -d /tmp
mv /tmp/xui-tg-bot-main/* "$BOT_DIR"/
rm -rf /tmp/xui-tg-bot.zip /tmp/xui-tg-bot-main

echo "🔹 Enter Telegram Bot Token:"
read -p "> " TOKEN
echo "🔹 Enter Admin ID:"
read -p "> " ADMIN_ID

cat <<EOF > "$CONFIG_FILE"
{
  "telegram_token": "$TOKEN",
  "admin_ids": [$ADMIN_ID],
  "db_path": "/etc/x-ui/x-ui.db",
  "log_path": "/var/log/xui-tg-bot.log"
}
EOF

# ===========================
# INSTALL SYSTEM DEPENDENCIES
# ===========================
echo "📦 Installing system packages..."
apt update -y >/dev/null
apt install -y python3 python3-pip jq sqlite3 whiptail >/dev/null


# ===========================
# INSTALL PYTHON DEPENDENCIES
# ===========================
echo "📦 Installing Python dependencies..."
if [ -f "$BOT_DIR/install/requirements.txt" ]; then
    pip3 install -r "$BOT_DIR/install/requirements.txt" >/dev/null
else
    echo "⚠️ requirements.txt not found, installing minimal set..."
    pip3 install aiogram apscheduler psutil >/dev/null
fi
echo "✅ Python dependencies installed successfully."


cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=XUI Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/xui-tg-bot
ExecStart=/usr/bin/python3 /opt/xui-tg-bot/bot/xui_bot.py
Restart=always
RestartSec=5
User=root
StandardOutput=append:/var/log/xui-tg-bot.log
StandardError=append:/var/log/xui-tg-bot.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now xui-tg-bot
echo "✅ Installation complete. Bot is running!"
