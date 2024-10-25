FROM mcr.microsoft.com/playwright/python:v1.48.0-noble

ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y cron && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN chmod +x entrypoint.sh

ENV DISPLAY=:99
ENV CRON_TIME="0 0 * * *"

ENTRYPOINT ["/app/entrypoint.sh"]