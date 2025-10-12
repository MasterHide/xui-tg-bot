#!/bin/bash
set -e
BOT_DIR="/opt/xui-tg-bot"
SERVICE_FILE="/etc/systemd/system/xui-tg-bot.service"

echo "⚠️ This will remove the bot but not X-UI."
read -p "Continue? (y/n): " CONFIRM
[[ "$CONFIRM" != "y" ]] && echo "Aborted." && exit 0

systemctl stop xui-tg-bot 2>/dev/null || true
systemctl disable xui-tg-bot 2>/dev/null || true
rm -rf "$BOT_DIR" "$SERVICE_FILE"
systemctl daemon-reload

echo "✅ Bot uninstalled cleanly."
