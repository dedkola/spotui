FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SPOTUI_HOST=0.0.0.0 \
    SPOTUI_PORT=8080 \
    SPOTUI_OUTPUT_DIR=/music \
    SPOTUI_CONFIG_DIR=/config \
    SPOTUI_COOKIE_FILE=/config/cookies.txt

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY app /app/app

EXPOSE 8080
VOLUME ["/music", "/config"]

CMD ["python", "-m", "app.main"]
