#!/usr/bin/env python
"""Report which ERD backends are available, without installing or importing anything.

Usage:
    python detect_erd_backends.py
    python detect_erd_backends.py --json

Uses importlib.util.find_spec (which locates a module without importing it, so a
package whose system binary is missing cannot crash this probe) and shutil.which.
It never installs anything and never runs a subprocess.

The built-in Mermaid backend needs only pyyaml, so it is always available and this
script's exit status is always 0 - detection decides whether to *upgrade* the output,
never whether a diagram can be produced at all.
"""

import argparse
import importlib.util
import json
import shutil

# (module name, label, note shown when missing)
PY_CANDIDATES = [
    ("yaml", "pyyaml", "required by the built-in backend; uv add pyyaml"),
    ("eralchemy", "eralchemy >=1.7", "optional; uv add \"eralchemy[graphviz]\""),
    ("eralchemy2", "eralchemy2", "DEPRECATED, merged into eralchemy 1.5+; do not install"),
    ("paracelsus", "paracelsus", "optional; uv add paracelsus"),
    ("mermaidx", "mermaidx", "optional; renders mermaid without node or graphviz"),
    ("sqlalchemy", "sqlalchemy", "only needed by the SQLAlchemy-based backends"),
    ("felis", "lsst-felis", "only needed by the SQLAlchemy-based backends"),
    ("graphviz", "graphviz (python)", "needs the system graphviz binary as well"),
    ("pydot", "pydot", "needs the system graphviz binary as well"),
    ("sqlalchemy_schemadisplay", "sqlalchemy-schemadisplay", "optional; needs system graphviz"),
]

# (binary, label, note shown when missing)
BIN_CANDIDATES = [
    ("d2", "d2 binary", "not required; https://d2lang.com"),
    ("mmdc", "mermaid-cli (mmdc)", "not required; npx -y @mermaid-js/mermaid-cli"),
    ("npx", "npx", "not required; only a route to mermaid-cli"),
    ("dot", "graphviz `dot`", "NOT required by this skill"),
    ("plantuml", "plantuml", "not supported by this skill; see references/backends.md"),
    ("java", "java", "only relevant to PlantUML, which this skill does not use"),
]

# Renderers we will use if they are already present, best first. We never ask the
# user to install any of these - graphviz in particular is listed, never recommended.
RENDERER_PREFERENCE = ["d2", "mmdc", "dot"]


def probe():
    modules = {}
    for name, label, note in PY_CANDIDATES:
        try:
            found = importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):
            found = False
        modules[name] = {"label": label, "available": found, "note": note}

    binaries = {}
    for name, label, note in BIN_CANDIDATES:
        path = shutil.which(name)
        binaries[name] = {
            "label": label,
            "available": path is not None,
            "path": path,
            "note": note,
        }
    return modules, binaries


def main():
    parser = argparse.ArgumentParser(
        description="Report available ERD backends without installing anything."
    )
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable report")
    args = parser.parse_args()

    modules, binaries = probe()

    builtin_ok = modules["yaml"]["available"]
    renderer = next((b for b in RENDERER_PREFERENCE if binaries[b]["available"]), None)

    result = {
        "builtin_mermaid": builtin_ok,
        "recommendation": "builtin-mermaid" if builtin_ok else "none",
        "renderer": renderer,
        "modules": modules,
        "binaries": binaries,
    }

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print("Backend availability")
    status = "AVAILABLE" if builtin_ok else "MISSING"
    detail = "pyyaml only - always works" if builtin_ok else "pyyaml is missing; uv add pyyaml"
    print("  %-22s %-11s (%s)" % ("builtin-mermaid", status, detail))

    for name, label, _ in BIN_CANDIDATES:
        info = binaries[name]
        print(
            "  %-22s %-11s %s"
            % (label, "available" if info["available"] else "missing",
               info["path"] or info["note"])
        )
    for name, label, _ in PY_CANDIDATES:
        if name == "yaml":
            continue
        info = modules[name]
        state = "available" if info["available"] else "missing"
        if name == "eralchemy2" and info["available"]:
            state = "DEPRECATED"
        print("  %-22s %-11s %s" % (label, state, info["note"]))

    print()
    if builtin_ok:
        print("RECOMMENDATION: builtin-mermaid - no installs needed.")
    else:
        print("RECOMMENDATION: install pyyaml (uv add pyyaml), then use builtin-mermaid.")
    if renderer:
        print(
            "OPTIONAL: %s is already on PATH and can also produce a rendered image."
            % binaries[renderer]["label"]
        )
    else:
        print("No image renderer found on PATH. None is required - Mermaid text is the deliverable.")
    if modules["eralchemy2"]["available"]:
        print(
            "WARNING: eralchemy2 is deprecated - it was merged into eralchemy at 1.5.0 "
            "(current 1.7.0). Prefer `uv add \"eralchemy[graphviz]\"`."
        )


if __name__ == "__main__":
    main()
