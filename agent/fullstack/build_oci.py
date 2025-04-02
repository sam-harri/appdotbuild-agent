import sys
import anyio
import subprocess
import dagger
from dagger import dag


async def build_runtime_docker():
    alpine = dag.container().from_("alpine:3.20.6")
    base = (
        dag.container()
        .from_("registry.dagger.io/engine:v0.17.1")
        .with_env_variable("DAGGER_VERSION", "0.17.1")
        .with_env_variable("_EXPERIMENTAL_DAGGER_RUNNER_HOST", "unix:///var/run/buildkit/buildkitd.sock")
        .with_directory("/lib/apk/db", alpine.directory("/lib/apk/db"))
        .with_directory("/etc/apk", alpine.directory("/etc/apk"))
    )
    app = (
        dag.host()
        .directory(
            ".",
            include=[
                "uv.lock",
                "pyproject.toml",
                ".python-version",
                "server.py",
                "start_server.py",
            ]
        )
    )
    runtime = (
        base
        .with_exec(["apk", "update"])
        .with_exec(["apk", "add", "curl"])
        .with_exec(["apk", "add", "python3"])
        .with_exec(["curl", "-fsSL", "https://astral.sh/uv/install.sh", "-o", "/tmp/install.sh"])
        .with_exec(["sh", "-c", "XDG_BIN_HOME=/usr/local/bin INSTALLER_NO_MODIFY_PATH=1 sh /tmp/install.sh"])
        .with_workdir("/app")
        .with_directory("/app", app)
        .with_entrypoint(["uv", "run", "start_server.py"])
    )
    IMG_PATH = "server_image.tar"
    IMG_TAG = "appbuild/fullstack"
    await runtime.export(IMG_PATH)
    load_cmd = subprocess.run(["docker", "load", "-i", IMG_PATH], capture_output=True)
    img_hash = load_cmd.stdout.decode().split(":")[-1].strip()
    subprocess.run(["docker", "tag", img_hash, IMG_TAG])
    subprocess.run(["rm", IMG_PATH])


async def main():
    async with dagger.connection(dagger.Config(log_output=sys.stderr)):
        await build_runtime_docker()


if __name__ == "__main__":
    anyio.run(main)
