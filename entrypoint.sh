#!/bin/bash

Xvfb $DISPLAY -screen 0 1024x768x16 &
RUN_SCRIPT="python /app/main.py"

echo "Running script when container starts"
if $RUN_SCRIPT; then
    echo "Initial execution succeeded."
else
    echo "Initial execution failed, but continuing with cron setup."
fi

echo "${CRON_TIME} $RUN_SCRIPT >> /var/log/cron.log 2>&1" > /etc/cron.d/my-cron-job

cat /etc/cron.d/my-cron-job

chmod 0644 /etc/cron.d/my-cron-job

crontab /etc/cron.d/my-cron-job

touch /var/log/cron.log

cron

tail -f /var/log/cron.log
