#!/usr/bin/env bash
# Ставит расписание: понедельник и четверг, 07:00 по серверному времени.
set -e
LINE="0 7 * * 1,4 /opt/radar/cron.sh"
( crontab -l 2>/dev/null | grep -v '/opt/radar/cron.sh' ; echo "$LINE" ) | crontab -
echo "расписание поставлено:"
crontab -l | grep radar
