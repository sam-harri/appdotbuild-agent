import os
import uvicorn


def start_app() -> None:
    uvicorn.run(
        "server:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8080")),
        access_log=False,
        reload=os.getenv("RELOAD", "false").lower() == "true"
    )


if __name__ == "__main__":
    start_app()
