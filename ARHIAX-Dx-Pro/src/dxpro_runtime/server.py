"""Uvicorn launcher for the DX Pro FastAPI app."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.getenv("DXPRO_HOST", "127.0.0.1")
    port = int(os.getenv("DXPRO_PORT", "8310"))
    uvicorn.run("dxpro_runtime.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
