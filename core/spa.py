"""Serve the Vite/React member portal from Django on the same origin."""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.views import View


def frontend_dist_dir() -> Path:
    configured = getattr(settings, "FRONTEND_DIST_DIR", None)
    if configured:
        return Path(configured)
    return Path(settings.BASE_DIR) / "frontend_dist"


def frontend_index_path() -> Path:
    return frontend_dist_dir() / "index.html"


class ReactAppView(View):
    """
    Return the React SPA shell (index.html).

    React Router handles client-side routes. API and admin stay on Django URLs
    registered before the catch-all.
    """

    def get(self, request, *args, **kwargs):
        index = frontend_index_path()
        if not index.is_file():
            return HttpResponse(
                (
                    "<!doctype html><html><body style='font-family:sans-serif;padding:2rem'>"
                    "<h1>MCS React frontend is not built</h1>"
                    "<p>From the <code>front-end</code> folder run:</p>"
                    "<pre>npm run build:django</pre>"
                    "<p>Then reload this page (Django serves it at the same origin).</p>"
                    "</body></html>"
                ),
                status=503,
                content_type="text/html; charset=utf-8",
            )
        return FileResponse(index.open("rb"), content_type="text/html; charset=utf-8")
