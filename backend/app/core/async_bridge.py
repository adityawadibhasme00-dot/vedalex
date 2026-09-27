"""Async bridge helpers for IP-SAKTI.

The RAG stack (hybrid retrieval, cross-encoder reranking, semantic
entailment, corpus loading) and the outbound HTTP clients (LLM providers,
Bhashini, WIPO Patentscope, IndiaCode) are synchronous by design.  Calling
them straight from an ``async def`` route blocks the event loop for the whole
duration — and with a 25-45s LLM timeout that stalls every other in-flight
request, health checks included.

``run_sync`` offloads a blocking callable onto a worker thread so the event
loop stays free and slow I/O from concurrent requests overlaps instead of
serialising.

Scope note: the GIL still serialises pure-Python CPU work, so this buys
concurrency for I/O-bound waits, not parallel embedding throughput.  Moving
BGE-M3 + the reranker out of the web process into a dedicated model sidecar
is what unlocks true horizontal scale; this module is the prerequisite that
makes the web tier stateless enough to be replicated.
"""

from __future__ import annotations

import asyncio
import functools
import logging
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def run_sync(fn: Callable[..., T], /, *args: Any, **kwargs: Any) -> T:
    """Await a blocking callable on a worker thread.

    Usage inside a route handler::

        result = await run_sync(SomeOrchestrator.run, question, passport_id)

    Exceptions propagate unchanged to the caller, so existing error handling
    around the synchronous call keeps working.
    """
    loop = asyncio.get_running_loop()
    call = functools.partial(fn, *args, **kwargs)
    return await loop.run_in_executor(None, call)


async def run_sync_timed(
    fn: Callable[..., T],
    /,
    *args: Any,
    timeout: float,
    label: str = "blocking-call",
    **kwargs: Any,
) -> T:
    """``run_sync`` with a hard ceiling.

    On timeout the coroutine raises :class:`asyncio.TimeoutError`` but the
    worker thread keeps running to completion (threads cannot be cancelled).
    That is deliberate: the alternative is leaving a half-written DB row or a
    half-built index behind.  The timeout bounds what the *client* waits for,
    which is what protects the connection pool.
    """
    try:
        return await asyncio.wait_for(
            run_sync(fn, *args, **kwargs), timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.warning(
            "%s exceeded %.1fs; client detached, worker still finishing",
            label,
            timeout,
        )
        raise
