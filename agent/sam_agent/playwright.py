import re
import os
import logging
import contextlib
from collections import defaultdict
from typing import Literal
from tempfile import TemporaryDirectory
import jinja2
from sam_agent import playbooks
from core.base_node import Node
from core.workspace import ExecResult
from core.actors import BaseData, Workspace
from core.postgres_utils import create_postgres_service, pg_health_check_cmd
from llm.common import AsyncLLM, Message, TextRaw, AttachedFiles
from llm.utils import merge_text, extract_tag

import dagger

logger = logging.getLogger(__name__)


async def alembic_push(
    client: dagger.Client, ctr: dagger.Container, postgresdb: dagger.Service | None
) -> ExecResult:
    """Run drizzle-kit push with postgres service."""

    if postgresdb is None:
        postgresdb = create_postgres_service(client)

    base_ctr = (
        ctr.with_exec([
    "bash", "-lc",
    "apt-get update && "
    "DEBIAN_FRONTEND=noninteractive apt-get install -y postgresql-client && "
    "rm -rf /var/lib/apt/lists/*"
    ])
        .with_service_binding("postgres", postgresdb)
        .with_env_variable(
            "APP_DATABASE_URL", "postgres+asyncpg://postgres:postgres@postgres:5432/postgres"
        )
        .with_exec(pg_health_check_cmd())
        # .with_workdir("server")

    )


    env_out = await base_ctr.with_exec(["bash", "-lc", "cat server/alembic/env.py"]).stdout()
    logger.debug("ALEMBIC ENV CONTENTS:\n", env_out)

    push_ctr = base_ctr.with_exec(["bash", "-lc", "bun run db:push"])
    result = await ExecResult.from_ctr(push_ctr)
    return result

# async def create_workspace_alpine(
#     client: dagger.Client,
#     context: dagger.Directory,
#     protected: list[str] = [],
#     allowed: list[str] = [],
# ):
#     ctr = (
#         client.container()
#         .from_("oven/bun:1.2.5-alpine")
#         # Tooling + common headers; extend if your Python deps need more
#         .with_exec(["sh", "-lc", "apk add --no-cache curl ca-certificates git build-base python3-dev musl-dev libffi-dev openssl-dev zlib-dev"])
#         # uv install (ensure pipe runs via shell, and put uv on PATH)
#         .with_exec(["sh", "-lc", "UV_INSTALL_DIR=/usr/local/bin curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -y"])
#         .with_workdir("/work")
#         .with_directory("/work", context)
#         .with_mounted_cache("/root/.cache/uv", client.cache_volume("uv-cache"))
#         .with_mounted_cache("/root/.bun", client.cache_volume("bun-home"))
#         .with_mounted_cache("/work/client/node_modules", client.cache_volume("client-node_modules"))
#         .with_exec(["sh", "-lc", "uv sync --all-extras --dev --frozen || uv sync --all-extras --dev"])
#         .with_exec(["sh", "-lc", "cd client && bun install --frozen-lockfile || (echo 'No lockfile; doing bun install' && bun install)"])
#         .with_exec(["sh", "-lc", "cd client && bun run build"])
#     )

#     return {
#         "client": client,
#         "ctr": ctr,
#         "start": context,
#         "protected": set(protected),
#         "allowed": set(allowed),
#     }


@contextlib.contextmanager
def ensure_dir(dir_path: str | None):
    if dir_path is not None:
        yield dir_path
    else:
        with TemporaryDirectory() as temp_dir:
            yield temp_dir
