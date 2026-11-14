#!/usr/bin/env python3
"""
Archetype Nolly X Root Module Shim & CLI Entrypoint
Enables direct importing and command-line usage from the workspace root.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Fix Windows console UTF-8 output
if sys.platform == "win32":
    try:
        if sys.stdout.encoding.lower() != "utf-8":
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr.encoding.lower() != "utf-8":
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent
PRESET_EDITOR_DIR = ROOT_DIR / "preset_editor"

for p in (str(ROOT_DIR), str(PRESET_EDITOR_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from preset_editor.juce_valuetree import (
    JuceInputStream,
    JuceOutputStream,
    JuceVar,
    ValueTreeNode,
    VarMarker,
    read_value_tree,
    write_value_tree,
)
from preset_editor.nolly_preset import (
    AMP_NAMES,
    CAB_NAMES,
    NollyPreset,
    clock_to_value,
    parse_bool,
    parse_numeric,
    parse_param_value,
    scale10_to_value,
    value_to_clock,
)
from preset_editor.cli import main

__all__ = [
    "NollyPreset",
    "ValueTreeNode",
    "JuceVar",
    "VarMarker",
    "read_value_tree",
    "write_value_tree",
    "value_to_clock",
    "clock_to_value",
    "scale10_to_value",
    "parse_param_value",
    "AMP_NAMES",
    "CAB_NAMES",
    "main",
]

if __name__ == "__main__":
    sys.exit(main())
