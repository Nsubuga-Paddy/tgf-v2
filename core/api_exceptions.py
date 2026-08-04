"""Ensure API clients always receive JSON errors, never Django DEBUG HTML."""

from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        if isinstance(response.data, dict) and "detail" not in response.data:
            # Keep field errors, but also provide a single readable detail line.
            response.data = {
                "detail": _flatten(response.data),
                "errors": response.data,
            }
        return response

    logger.exception("Unhandled API exception in %s", context.get("view"))
    return Response(
        {
            "detail": "The server could not process this request. Please try again shortly.",
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _flatten(data) -> str:
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        return " ".join(_flatten(item) for item in data if item).strip()
    if isinstance(data, dict):
        parts = []
        for key, value in data.items():
            text = _flatten(value)
            if not text:
                continue
            if key in {"detail", "non_field_errors"}:
                parts.append(text)
            else:
                parts.append(f"{key}: {text}")
        return " ".join(parts).strip()
    return str(data)
