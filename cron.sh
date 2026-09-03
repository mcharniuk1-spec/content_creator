#!/usr/bin/env bash
# Недельный прогон по расписанию: понедельник и четверг.
# Ставится через install-cron.sh; руками звать не нужно — для ручного запуска есть run.py.
set -uo pipefail
cd /opt/radar || exit 1

LOG="data/runs/$(date +%Y-%m-%d_%H%M).log"
mkdir -p data/runs
exec >>"$LOG" 2>&1

echo "═══ прогон $(date '+%Y-%m-%d %H:%M') ═══"

# код мог обновиться на рабочей машине
git pull -q --rebase 2>/dev/null || echo "git pull не прошёл, идём на текущем коде"

# сам прогон: сбор, оценка, разбор, темы, решения, карточки, дельта, страницы
timeout 7200 .venv/bin/python run.py --yes
code=$?
echo "── прогон завершился с кодом $code ──"

# углы пишет агент: он читает позиционирование, кадры и расшифровки
if [ $code -eq 0 ]; then
    timeout 3600 claude -p "$(cat prompts/angles.md)" \
        --allowed-tools "Bash,Read,Edit" >>"$LOG" 2>&1 \
        || echo "агент не отработал — карточки остались без углов"
    timeout 900 .venv/bin/python notion.py push >>"$LOG" 2>&1 \
        || echo "выгрузка углов в Notion не прошла"
fi

# оставляем последние двадцать журналов, остальное ни к чему
ls -1t data/runs/*.log 2>/dev/null | tail -n +21 | xargs -r rm --
echo "═══ конец $(date '+%H:%M') ═══"
