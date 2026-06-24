"""Uvicorn launcher for the DX Pro FastAPI app."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    from dxpro_runtime.api import create_app

    app = create_app()
    host = os.getenv("DXPRO_HOST", "127.0.0.1")
    port = int(os.getenv("DXPRO_PORT", "8310"))
    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
