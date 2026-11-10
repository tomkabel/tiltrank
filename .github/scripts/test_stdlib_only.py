#!/usr/bin/env python3
"""Each shape below must be reported; the stdlib-only file must not."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from stdlib_only import offenders  # noqa: E402

BAD = {
    "plain.py": "import requests\n",
    "from_.py": "from yaml import safe_load\n",
    "dunder.py": "__import__('numpy')\n",
    "attr.py": "import importlib\nimportlib.import_module('pandas')\n",
    "alias.py": "from importlib import import_module as load\nload('requests')\n",
    "bare.py": "from importlib import import_module\nimport_module('requests')\n",
    "builtin_alias.py": "from builtins import __import__ as imp\nimp('requests')\n",
    "non_literal.py": "name = 'x'\n__import__(name)\n",
}

with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    for name, src in BAD.items():
        (root / name).write_text(src)
    (root / "ok.py").write_text(
        "import json\nfrom importlib import import_module as load\nload('json')\n"
    )
    found = offenders(root)
    for name in BAD:
        assert any(name in line for line in found), f"{name} not reported: {found}"
    assert not any("ok.py" in line for line in found), found
print(f"stdlib_only: {len(BAD)} bad shapes reported, clean file passes")
