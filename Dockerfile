FROM python:3.12-slim-bookworm

LABEL com.calco.app="inventarios-mensuales"

WORKDIR /app

# ICU is required by app.models.text for Spanish collation.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata libicu72 \
    && rm -rf /var/lib/apt/lists/*

# This repository has no requirements-lock.txt.
COPY requirements.txt ./
RUN python -B -m pip install --no-cache-dir --disable-pip-version-check \
    -r requirements.txt gunicorn==23.0.0

RUN groupadd --gid 10002 appgroup \
    && useradd --uid 10002 --gid 10002 --no-create-home \
        --shell /usr/sbin/nologin appuser \
    && mkdir -p /app/credentials /app/.runtime \
    && chown -R appuser:appgroup /app

# Copy only application sources: never .env, credentials, secrets or local runtime.
COPY --chown=appuser:appgroup app/ ./app/
COPY --chown=appuser:appgroup scripts/ ./scripts/

USER appuser

EXPOSE 8000

# One process shares the read/single-flight and SSO replay caches between threads.
# Use the existing Flask factory; neither run.py nor wsgi.py is required.
CMD ["python", "-B", "-u", "-m", "gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "app:create_app()"]
