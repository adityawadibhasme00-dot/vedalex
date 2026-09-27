"""One-off codemod: demote pure-sync FastAPI route handlers from `async def` to `def`.

Why
---
FastAPI runs a plain ``def`` endpoint in the anyio worker threadpool, but runs an
``async def`` endpoint directly on the event loop.  The IP-SAKTI route handlers
are thin, fully synchronous wrappers around CPU/IO-bound engines
(``WhitespaceNavigator.analyze``, ``ProductClassifier``, dossier builders, ...)
and a number of them sit behind ``async def``.  That blocks the loop for the
whole duration, so one 40s dossier build stalls every other in-flight request.

Rather than hand-editing every call site, a handler that contains no ``await``
has nothing to be ``async`` for: demoting it hands it to the threadpool for
free, with no behavioural change to the body.

Safety
------
A handler is only rewritten when ``ast`` proves it is:
  * decorated with a FastAPI route decorator (``@router.get`` / ``.post`` / ...),
  * free of ``await`` / ``async with`` / ``async for`` / ``yield``,
  * free of nested async functions,
  * not an async generator.

Run:  python scripts/demote_sync_routes.py [--check]
"""

from __future__ import annotations

import argparse
import ast
import pathlib
import re
import sys

ROUTER_DIR = pathlib.Path(__file__).resolve().parents[1] / "app" / "api" / "v1"
ROUTE_DECORATORS = ("get", "post", "put", "patch", "delete", "head", "options")
BANNED_NODES = (ast.Await, ast.AsyncWith, ast.AsyncFor, ast.Yield, ast.YieldFrom)


class _RouteCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.routes: list[ast.AsyncFunctionDef] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        for dec in node.decorator_list:
            if _is_route_decorator(dec):
                self.routes.append(node)  # type: ignore[arg-type]
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        for dec in node.decorator_list:
            if _is_route_decorator(dec):
                self.routes.append(node)
        self.generic_visit(node)


def _is_route_decorator(dec: ast.expr) -> bool:
    if not isinstance(dec, ast.Call):
        return False
    func = dec.func
    if not isinstance(func, ast.Attribute):
        return False
    return func.attr in ROUTE_DECORATORS


def _is_demotable(node: ast.AsyncFunctionDef) -> tuple[bool, str]:
    for sub in ast.walk(node):
        if isinstance(sub, BANNED_NODES):
            return False, f"contains {type(sub).__name__}"
        if isinstance(sub, ast.AsyncFunctionDef) and sub is not node:
            return False, "contains nested async def"
        if isinstance(sub, (ast.AsyncFunctionDef,)) and node not in [
            n for n in ast.walk(node) if n is sub
        ]:
            return False, "unexpected nesting"
    return True, "clean"


def process(path: pathlib.Path, check_only: bool) -> tuple[int, int]:
    raw = path.read_bytes()
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    source = raw.decode("utf-8-sig")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        print(f"  SKIP {path.name}: syntax error {exc}")
        return 0, 0

    collector = _RouteCollector()
    collector.visit(tree)

    lines = source.splitlines(keepends=True)
    changed = 0
    skipped = 0

    for node in sorted(collector.routes, key=lambda n: n.lineno, reverse=True):
        ok, why = _is_demotable(node)
        if not ok:
            skipped += 1
            continue
        idx = node.lineno - 1
        line = lines[idx]
        new_line, n = re.subn(r"\basync def\b", "def", line, count=1)
        if n == 0:
            skipped += 1
            continue
        changed += 1
        if not check_only:
            lines[idx] = new_line

    if changed and not check_only:
        out = "".join(lines).encode("utf-8")
        path.write_bytes(b"\xef\xbb\xbf" + out if has_bom else out)

    if changed or skipped:
        print(f"  {path.name}: {changed} demoted, {skipped} kept async")
    return changed, skipped


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="report only")
    args = parser.parse_args()

    total_changed = total_skipped = 0
    for path in sorted(ROUTER_DIR.glob("*.py")):
        c, s = process(path, args.check)
        total_changed += c
        total_skipped += s

    print(f"\ntotal: {total_changed} demoted, {total_skipped} kept async")
    return 0


if __name__ == "__main__":
    sys.exit(main())
