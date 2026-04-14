"""
ASGI entry for Streamlit + PWA routes (manifest + service worker at document root).

Deploy: uvicorn asgi:app --host 0.0.0.0 --port $PORT
Local:   uvicorn asgi:app --reload --host 127.0.0.1 --port 8501
"""
from __future__ import annotations

from pathlib import Path

from starlette.responses import FileResponse
from starlette.routing import Route
from streamlit.starlette import App

from auth_middleware import wrap_basic_auth_if_configured

_ROOT = Path(__file__).resolve().parent
_STATIC = _ROOT / "static"


async def _manifest(_request):
    return FileResponse(
        _STATIC / "manifest.json",
        media_type="application/manifest+json",
        headers={"Cache-Control": "public, max-age=3600"},
    )


async def _service_worker(_request):
    return FileResponse(
        _STATIC / "sw.js",
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=0"},
    )


async def _icon_192(_request):
    return FileResponse(_STATIC / "icon-192.png", media_type="image/png")


async def _icon_512(_request):
    return FileResponse(_STATIC / "icon-512.png", media_type="image/png")


app = wrap_basic_auth_if_configured(
    App(
        str(_ROOT / "app.py"),
        routes=[
            Route("/manifest.json", endpoint=_manifest, methods=["GET"]),
            Route("/sw.js", endpoint=_service_worker, methods=["GET"]),
            Route("/pwa/icon-192.png", endpoint=_icon_192, methods=["GET"]),
            Route("/pwa/icon-512.png", endpoint=_icon_512, methods=["GET"]),
        ],
    )
)
