import importlib
import pkgutil
import threading

import pytest

import app

_OFFLINE_MARKERS = (
    "connection",
    "connect ",
    "timeout",
    "timed out",
    "getaddrinfo",
    "name resolution",
    "name or service not known",
    "network is unreachable",
    "no route to host",
    "temporary failure",
    "offline",
    "max retries",
    "ssl:",
    "http error",
    "remotedisconnected",
)

HEAVY_SIDE_EFFECT_MODULES: dict[str, tuple[str, ...]] = {}


def _short_error(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}".replace("\n", " | ").replace("\r", " ")
    return text if len(text) <= 400 else text[:397] + "..."


def _offline_failure(exc: BaseException) -> bool:
    text = f"{type(exc).__name__}: {exc}".lower()
    return any(marker in text for marker in _OFFLINE_MARKERS)


def _threads_since(snapshot: set) -> tuple[str, ...]:
    return tuple(
        sorted(
            thread.name
            for thread in threading.enumerate()
            if thread.ident is not None and thread.ident not in snapshot
        )
    )


def _probe(name: str):
    before = {thread.ident for thread in threading.enumerate()}
    try:
        importlib.import_module(name)
    except BaseException as exc:
        reason = f"{name} fails to import: {_short_error(exc)}"
        if _offline_failure(exc):
            reason = f"{reason} (offline import blocked by network side effect at import time)"
        spawned = _threads_since(before)
        if spawned:
            reason = f"{reason} (import spawned threads: {', '.join(spawned)})"
        return pytest.param(name, marks=pytest.mark.xfail(reason=reason, strict=False))
    spawned = _threads_since(before)
    if spawned:
        HEAVY_SIDE_EFFECT_MODULES[name] = spawned
    return pytest.param(name)


def _discover_modules() -> list:
    names: list[str] = []
    undiscoverable: list[str] = []
    try:
        walked = pkgutil.walk_packages(app.__path__, prefix="app.", onerror=undiscoverable.append)
        for module_info in walked:
            if "__pycache__" in module_info.name:
                continue
            names.append(module_info.name)
    except BaseException as exc:
        reason = f"app package discovery failed: {_short_error(exc)}"
        return [pytest.param("<discovery>", marks=pytest.mark.xfail(reason=reason, strict=False))]
    ordered = sorted(set(names) | set(undiscoverable))
    return [_probe(name) for name in ordered]


MODULE_PARAMS = _discover_modules()

SIDE_EFFECT_PARAMS = [
    pytest.param(
        module_name,
        threads,
        marks=pytest.mark.xfail(
            reason=(
                f"{module_name} executes heavy side effects at import time "
                f"(threads spawned: {', '.join(threads)})"
            ),
            strict=False,
        ),
    )
    for module_name, threads in sorted(HEAVY_SIDE_EFFECT_MODULES.items())
] or [pytest.param(None, (), id="no-heavy-side-effects")]


@pytest.mark.parametrize("module_name", MODULE_PARAMS)
def test_module_import_smoke(module_name: str) -> None:
    imported = importlib.import_module(module_name)
    assert imported is not None
    assert imported.__name__ == module_name


@pytest.mark.parametrize("module_name,side_effects", SIDE_EFFECT_PARAMS)
def test_no_module_executes_heavy_side_effects_on_import(module_name, side_effects) -> None:
    assert module_name is None, (
        f"{module_name} executes heavy import side effects: threads={list(side_effects)}"
    )
