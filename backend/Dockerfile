FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

# INSTALL_DEV=true inclui pytest/httpx/ruff/mypy (para rodar a suíte no container).
# Em produção deixe false (padrão) — imagem menor e menos superfície.
ARG INSTALL_DEV=false

COPY pyproject.toml ./
COPY app ./app
RUN pip install --upgrade pip \
 && if [ "$INSTALL_DEV" = "true" ]; then pip install ".[dev]"; else pip install .; fi

COPY alembic.ini ./
COPY alembic ./alembic
COPY tests ./tests

RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Aplica migrações, roda o seed idempotente e sobe a API.
# --forwarded-allow-ips '*': o backend não é publicado — só o nginx do frontend
# (ou o proxy TLS embutido) fala com ele, e ambos mandam X-Forwarded-For já
# resolvido (IP real, um valor só). A confiança no proxy externo fica no
# frontend (FORWARDED_ALLOW_IPS, ver frontend/realip.sh).
# --timeout 180: a restauração de backup (DROP/CREATE + INSERT de toda a base)
# roda de forma síncrona no worker e pode passar dos 30s padrão.
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 -w 4 --timeout 180 --forwarded-allow-ips '*' --access-logfile - --error-logfile -"]
