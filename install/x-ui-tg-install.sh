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
cp -r ../bot ../install ../config ../docs "$BOT_DIR" 2>/dev/null || true

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

apt update -y && apt install -y python3 python3-pip jq sqlite3 whiptail >/dev/null
pip3 install -r "$BOT_DIR/install/requirements.txt" >/dev/null

cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=XUI Telegram Bot
After=network.target

[Service]
ExecStart=$PYTHON $BOT_DIR/bot/bot.py
Restart=always
WorkingDirectory=$BOT_DIR
User=root

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now xui-tg-bot
echo "✅ Installation complete. Bot is running!"
