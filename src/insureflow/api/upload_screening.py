"""Run upload screening (password unlock + virus scan) off the event loop, for every route.

FastAPI validates a request body on the event loop, even for plain ``def`` routes.
``InsuranceDocumentPayload`` used to unlock and virus-scan inside its validator,
so a 25 MB base64 decode and a ClamAV round trip ran on the loop and stalled the
whole worker.

``ScreenedRoute`` is the app's route class. For each request it opens a
"screening scope". While the body is being validated inside that scope, the
payload validator only *registers* each document. Before the route function
runs, the route class screens every registered document, in the threadpool for
sync routes and via ``asyncio.to_thread`` for async ones. A route cannot skip
this: the scan happens in the route class, not in the route's own code.

Anything outside a request scope (models built inside a route body, Celery
workers, tests) screens immediately, exactly as before.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
from contextvars import ContextVar
from typing import Any, Callable, Protocol

from fastapi.routing import APIRoute
from starlette.requests import Request
from starlette.responses import Response


class Screenable(Protocol):
    def screen_now(self) -> None: ...


class _Scope:
    __slots__ = ("deferring", "pending")

    def __init__(self) -> None:
        self.deferring = True
        self.pending: list[Screenable] = []


_scope: ContextVar[_Scope | None] = ContextVar("upload_screening_scope", default=None)


def defer_screening(doc: Screenable) -> bool:
    """Called from the payload validator. True means "the route class will screen
    this before the route runs"; False means "screen it yourself, now"."""
    scope = _scope.get()
    if scope is None or not scope.deferring:
        return False
    scope.pending.append(doc)
    return True


def screen_pending() -> None:
    """Screen every document registered during body validation. Blocking: call off the loop."""
    scope = _scope.get()
    if scope is None:
        return
    scope.deferring = False  # documents built later, inside the route, screen themselves
    pending, scope.pending = scope.pending, []
    for doc in pending:
        doc.screen_now()


def _screen_before(endpoint: Callable[..., Any]) -> Callable[..., Any]:
    if inspect.iscoroutinefunction(endpoint):

        @functools.wraps(endpoint)
        async def run_async(*args: Any, **kwargs: Any) -> Any:
            await asyncio.to_thread(screen_pending)  # to_thread copies the context, so the scope travels
            return await endpoint(*args, **kwargs)

        return run_async

    @functools.wraps(endpoint)
    def run_sync(*args: Any, **kwargs: Any) -> Any:
        screen_pending()  # FastAPI already runs sync routes in the threadpool
        return endpoint(*args, **kwargs)

    return run_sync


class ScreenedRoute(APIRoute):
    """Route class that screens uploaded documents in a thread before the route function runs."""

    def __init__(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        super().__init__(path, _screen_before(endpoint), **kwargs)

    def get_route_handler(self) -> Callable[[Request], Any]:
        handler = super().get_route_handler()

        async def screened_handler(request: Request) -> Response:
            token = _scope.set(_Scope())
            try:
                return await handler(request)
            finally:
                _scope.reset(token)

        return screened_handler
