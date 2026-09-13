#!/usr/bin/env bash
# Project manager pass: a Sonnet 5 agent reconciles Notion and the repository with what is true
# on this machine (prompts/pm.md). Daily at 08:30 server time and after each weekly run (cron.sh).
# Read-only on code and data; writes data/pm/latest.md and applies the kanban/review to Notion.
set -uo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export HOME="/root"
export LANG="C.UTF-8"
export LC_ALL="C.UTF-8"
cd /opt/radar || exit 1
mkdir -p data/pm data/runs
LOG="data/runs/pm-$(date +%Y-%m-%d_%H%M).log"
exec >>"$LOG" 2>&1
echo "═══ project manager pass $(date '+%Y-%m-%d %H:%M') ═══"
git pull -q --ff-only 2>/dev/null || echo "git pull did not apply, running on the current code"
timeout 1800 claude -p "$(cat prompts/pm.md)" --model claude-sonnet-5 \
    --allowed-tools "Bash,Read,Write" || echo "pm agent failed"
if [ -s data/pm/latest.md ]; then
    timeout 900 .venv/bin/python -m engine.notion_kanban --apply || echo "kanban apply failed"
else
    echo "no data/pm/latest.md written"
fi
ls -1t data/runs/pm-*.log 2>/dev/null | tail -n +15 | xargs -r rm --
echo "═══ end $(date '+%H:%M') ═══"
