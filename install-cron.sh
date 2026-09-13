#!/usr/bin/env bash
# Ставит расписание: понедельник и четверг, 07:00 по времени сервера (Europe/Berlin).
# Время выбрано так, чтобы к началу дня карточки уже лежали в Notion.
set -e
command -v crontab >/dev/null || { apt-get update -qq && apt-get install -y -qq cron; }
systemctl enable --now cron >/dev/null 2>&1 || true

TMP=$(mktemp)
crontab -l 2>/dev/null | grep -v '/opt/radar/cron.sh\|/opt/radar/pm.sh' > "$TMP" || true
echo '0 7 * * 1,4 /opt/radar/cron.sh' >> "$TMP"
# project manager pass (prompts/pm.md, Sonnet 5): daily, after the weekly run has finished
echo '30 8 * * * /opt/radar/pm.sh' >> "$TMP"
crontab "$TMP"
rm -f "$TMP"

echo "расписание:"
crontab -l | grep radar
