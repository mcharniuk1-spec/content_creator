#!/usr/bin/env bash
# Недельный прогон по расписанию: понедельник и четверг.
# Ставится через install-cron.sh; руками звать не нужно — для ручного запуска есть run.py.
set -uo pipefail

# cron запускает скрипт почти без окружения: без этого не находится ни claude, ни git,
# а кириллица в выводе превращается в мусор
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export HOME="/root"
export LANG="C.UTF-8"
export LC_ALL="C.UTF-8"

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

    # читаемые страницы недели. Пока Notion не настроен, это единственный
    # человеческий вид результата, поэтому складываем их рядом с журналом
    # прогона: каждая неделя остаётся, а не затирается следующей.
    RUN_DIR="data/runs/$(date +%Y-%m-%d)"
    mkdir -p "$RUN_DIR"
    if .venv/bin/python pages.py >>"$LOG" 2>&1; then
        cp -f niche.html shoot.html radar.html "$RUN_DIR"/ 2>/dev/null
        echo "страницы недели сохранены: $RUN_DIR (shoot.html — что снимаем)"
    else
        echo "страницы недели собрать не удалось"
    fi
fi

# оставляем последние двадцать журналов, остальное ни к чему
ls -1t data/runs/*.log 2>/dev/null | tail -n +21 | xargs -r rm --
echo "═══ конец $(date '+%H:%M') ═══"
