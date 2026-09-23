#!/usr/bin/env python3
"""Build dist/unslop.zip for upload to claude.ai (Settings > Capabilities > Skills).

claude.ai has no slash commands, so the manual-only flag is removed:
the skill then runs when you ask for it by name ("unslop this").
"""
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parent.parent
skill = "".join(line for line in (root / "SKILL.md").read_text().splitlines(keepends=True)
                if not line.startswith("disable-model-invocation:"))
(root / "dist").mkdir(exist_ok=True)
out = root / "dist" / "unslop.zip"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("unslop/SKILL.md", skill)
print(out)
