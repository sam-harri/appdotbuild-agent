import os
import dagger
from dagger import dag
from fastapi import FastAPI


app = FastAPI()


@app.get("/healthcheck/bun")
async def healthcheck_bun():
    async with dagger.connection(dagger.Config(log_output=open(os.devnull, "w"))):
        container = dag.container().from_("oven/bun:1.2.5-alpine")
        result = await container.with_exec(["bun"])
        return {
            "status": "success",
            "output": await result.stdout(),
        }
