#!/usr/bin/env python3
"""Fail on any import outside the stdlib under the given root (default .claude).

Covers `import x`, `from x import y`, `__import__("x")` and
`importlib.import_module("x")`, including an imported alias of either. A dynamic import whose name is not a string
literal is reported too: it cannot be checked, so it is not allowed.
"""

import ast
import sys
from pathlib import Path

LOCAL = {"rubric", "check_trace"}


def offenders(root: Path) -> list[str]:
    bad = []
    for f in sorted(root.rglob("*.py")):
        local = LOCAL | {p.stem for p in f.parent.glob("*.py")}
        tree = ast.parse(f.read_bytes(), str(f))
        # `from importlib import import_module as load` makes `load(...)` dynamic too.
        # ponytail: plain assignment (`load = importlib.import_module`) is not tracked.
        loaders = {"__import__"} | {
            a.asname or a.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module in ("importlib", "builtins")
            for a in node.names
            if a.name in ("import_module", "__import__")
        }
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            elif isinstance(node, ast.Call):
                fn = node.func
                dynamic = (isinstance(fn, ast.Name) and fn.id in loaders) or (
                    isinstance(fn, ast.Attribute) and fn.attr == "import_module"
                )
                if dynamic:
                    arg = node.args[0] if node.args else None
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        names = [arg.value]
                    else:
                        bad.append(
                            f"{f}:{node.lineno}: dynamic import of a non-literal name"
                        )
            for n in names:
                root_name = n.split(".")[0]
                if root_name not in sys.stdlib_module_names and root_name not in local:
                    bad.append(f"{f}:{node.lineno}: {n}")
    return bad


if __name__ == "__main__":
    found = offenders(Path(sys.argv[1] if len(sys.argv) > 1 else ".claude"))
    print("\n".join(found) or "stdlib only")
    sys.exit(1 if found else 0)
