# ---------- Stage 1: build the frontend with Bun ----------
    FROM oven/bun:1.2.2-alpine AS client-build
    WORKDIR /work
    
    # copy root manifests (lockfile at root)
    COPY package.json bun.lock ./
    # copy client manifest for better caching
    COPY client/package.json ./client/package.json
    
    # install using the root workspace lockfile (preferred)
    RUN bun install --frozen-lockfile
    
    # now copy sources and build
    COPY client/ ./client/
    WORKDIR /work/client
    RUN bun run build   # ✅ no -C
    
    
    
    # ---------- Stage 2: runtime (Python + Caddy + Supervisor) ----------
    FROM python:3.12-slim
    
    ENV PYTHONDONTWRITEBYTECODE=1 \
        PYTHONUNBUFFERED=1 \
        PORT=2022
    
    # Base tools: caddy, supervisor, curl, build deps for wheels if needed
    RUN apt-get update \
     && apt-get install -y --no-install-recommends \
          caddy supervisor curl build-essential vim nano less coreutils\
     && rm -rf /var/lib/apt/lists/*
    
    WORKDIR /app
    
    # --- Backend (Python) ---
    # If you use uv-managed project: install uv and sync deps.
    RUN pip install --no-cache-dir uv || true
    
    # Copy backend project files (adjust if your layout differs)
    COPY server/ /app/server/
    
    # Install Python deps:
    # Option A: uv with pyproject.toml / uv.lock
    # (If you committed uv.lock, uncomment the COPY and sync lines)
    RUN cd /app/server && uv lock
    RUN cd /app/server && uv sync --frozen
    # Option B: pip with requirements.txt
    # COPY server/requirements.txt /app/server/requirements.txt
    # RUN pip install --no-cache-dir -r /app/server/requirements.txt
    # Option C: pip install the project if it's a package
    # RUN pip install --no-cache-dir -e /app/server
    
    # --- Frontend (static + Caddyfile) ---
    COPY --from=client-build /work/client/dist /usr/share/caddy
    COPY client/Caddyfile /app/client/Caddyfile
    
    # --- Supervisor config ---
    COPY supervisord.conf /etc/supervisord.conf
    
    # --- Environment (DB URL picked up by alembic/env.py via your settings) ---
    ENV DATABASE_URL=${DATABASE_URL}
    
    EXPOSE 80 2022

    RUN ls -la /app/server/alembic/versions

    # Run Alembic, then start both processes under supervisor
    CMD sh -lc '\
    set -euo pipefail; \
    cd /app/server; export PYTHONPATH=/app/server; \
    mkdir -p alembic/versions; \
    if ! ls -1 alembic/versions/*.py >/dev/null 2>&1; then \
      echo "[bootstrap] No local revisions; autogenerating baseline…"; \
      uv run alembic revision --autogenerate -m "initial migration"; \
    fi; \
    uv run alembic stamp base; \
    uv run alembic upgrade head; \
    exec /usr/bin/supervisord -c /etc/supervisord.conf'