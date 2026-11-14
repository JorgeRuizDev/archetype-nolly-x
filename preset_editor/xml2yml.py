#!/usr/bin/env python3
"""
CLI tool for converting Archetype Nolly X binary XML presets into YAML presets.

Allows agents to easily dump existing presets to inspect, edit, or use as templates.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure preset_editor package is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from nolly_preset import NollyPreset
except ImportError:
    from preset_editor.nolly_preset import NollyPreset


def main(cli_args: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="xml2yml",
        description="Convert Archetype Nolly X binary XML preset to YAML",
    )
    parser.add_argument(
        "input",
        help="Path to input .xml preset file",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default=None,
        help="Path to output .yml file (if omitted or '-', prints to stdout)",
    )

    args = parser.parse_args(cli_args)

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"Error: Input XML file not found: {in_path}", file=sys.stderr)
        return 1

    try:
        preset = NollyPreset.load(in_path)
        yaml_content = preset.to_yaml()
    except Exception as e:
        print(f"Error reading/converting preset '{in_path}': {e}", file=sys.stderr)
        return 1

    if not args.output or args.output == "-":
        sys.stdout.write(yaml_content)
    else:
        out_path = Path(args.output)
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(yaml_content, encoding="utf-8")
            print(f"SUCCESS: Exported '{preset.name}' to YAML -> {out_path.resolve()}")
        except Exception as e:
            print(f"Error writing YAML file '{out_path}': {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
