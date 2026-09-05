#!/usr/bin/env bash
# Print the explicit timer instruction. No package/service/crontab mutation.
set -euo pipefail
cat <<'NOTICE'
Review and pin the checkout, restore-test the database, and supply M2_RUN_CONFIG.
The intended legacy cadence is Monday and Thursday 07:00 Europe/Berlin.
Install/update the timer through your normal server change process.
cron.sh runs existing data only. HikerAPI collection requires a separate approved adapter invocation and a reviewed live schema pilot.
No cron package, service or schedule was changed by this script.
NOTICE
