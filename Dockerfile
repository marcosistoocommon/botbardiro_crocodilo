FROM python:3.11-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install build deps for cryptography/matplotlib if wheels aren't available
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       gcc \
       libffi-dev \
       libssl-dev \
       libpng-dev \
       libfreetype6-dev \
       pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt /app/
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt
RUN pip install "python-telegram-bot[job-queue]" matplotlib

# Final runtime image (smaller)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy installed packages from build stage
COPY --from=build /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=build /usr/local/bin /usr/local/bin

# Copy application code
COPY . /app

# Create a non-root user
RUN groupadd -r bot && useradd -r -g bot bot \
    && chown -R bot:bot /app

USER bot

CMD ["python", "bot.py"]
