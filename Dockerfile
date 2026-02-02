# STAGE 1 : Builder - Compilation & Installation

FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

ARG APP_USER=appuser
ARG APP_UID=1000
ARG APP_GID=1000

RUN groupadd -g ${APP_GID} ${APP_USER} && \
    useradd -u ${APP_UID} -g ${APP_GID} -m -s /bin/bash ${APP_USER}

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .
RUN python -m venv /opt/venv && \
    chown -R ${APP_UID}:${APP_GID} /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install -r requirements.txt

# STAGE 2 : Runtime - Image légère + non-root

FROM python:3.14-slim

ARG APP_USER=appuser
ARG APP_UID=1000
ARG APP_GID=1000

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DEBIAN_FRONTEND=noninteractive

RUN groupadd -g ${APP_GID} ${APP_USER} && \
    useradd -u ${APP_UID} -g ${APP_GID} -m -s /bin/bash -d /app ${APP_USER} && \
    apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
RUN chown -R ${APP_UID}:${APP_GID} /opt/venv

COPY --chown=${APP_UID}:${APP_GID} . .

RUN mkdir -p /app/media /app/logs && \
    chown -R ${APP_UID}:${APP_GID} /app/media /app/logs && \
    chmod -R 755 /app

USER ${APP_UID}:${APP_GID}

EXPOSE 8000

CMD ["gunicorn", "ma_chorale.wsgi:application", "--bind", "0.0.0.0:8000"]