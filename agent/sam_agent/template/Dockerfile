
    FROM oven/bun:1.2.2-alpine AS client-build
    WORKDIR /work/client2

    COPY client2/package.json .
    COPY client2/bun.lock* ./ 
    
    RUN bun install --frozen-lockfile
    
    COPY client2/ .
    RUN bun run build
    
    FROM python:3.12-slim
    
    ENV PYTHONDONTWRITEBYTECODE=1 \
        PYTHONUNBUFFERED=1 \
        PORT=2022
    
    RUN apt-get update \
     && apt-get install -y --no-install-recommends \
          caddy supervisor curl build-essential vim nano less coreutils\
     && rm -rf /var/lib/apt/lists/*
    
    WORKDIR /app/server
    RUN pip install --no-cache-dir uv
    
    COPY server/pyproject.toml ./
    COPY server/uv.lock* ./
    RUN uv lock || true
    RUN uv sync --frozen || uv sync
    COPY server/ . 

    RUN mkdir -p /app/client2
    COPY --from=client-build /work/client2/dist /app/client2
    COPY client2/Caddyfile /app/client2/Caddyfile
    
    COPY supervisord.conf /etc/supervisord.conf
    
    ENV DATABASE_URL=${DATABASE_URL}
    
    EXPOSE 80 2022

    WORKDIR /app/
    COPY Makefile .

    # run migrations then start both processes under supervisor
    # if the alembic/versions directory is empty, autogenerate the baseline
    # then stamp the base revision and upgrade the database
    CMD sh -lc '\
    set -euo pipefail; \
    cd /app/server; \
    mkdir -p alembic/versions; \
    if ! ls -1 alembic/versions/*.py >/dev/null 2>&1; then \
      echo "[bootstrap] No local revisions; autogenerating baseline…"; \
      uv run alembic revision --autogenerate -m "initial migration"; \
    fi; \
    uv run alembic stamp base; \
    uv run alembic upgrade head; \
    exec /usr/bin/supervisord -c /etc/supervisord.conf'