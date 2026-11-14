#!/usr/bin/env python3
"""
CLI tool for converting YAML presets into Archetype Nolly X binary XML presets.

Designed specifically for AI agents and automated scripts:
- Reads YAML from file or stdin (`-`)
- Creates destination directories automatically
- Verifies output binary validity
- Generates verified knob scale and clock table with --report
- Returns exit code 0 on success, 1 on failure
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure preset_editor package and root are in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
for p in (str(ROOT_DIR), str(SCRIPT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from nolly_preset import NollyPreset
except ImportError:
    from preset_editor.nolly_preset import NollyPreset


def main(cli_args: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="yml2xml",
        description="Convert YAML preset to Archetype Nolly X binary XML preset",
    )
    parser.add_argument(
        "input",
        help="Path to input .yml/.yaml file (use '-' to read from standard input)",
    )
    parser.add_argument(
        "output",
        help="Path to output .xml preset file",
    )
    parser.add_argument(
        "--name",
        "-n",
        help="Optional: Override preset name in output XML",
    )
    parser.add_argument(
        "--report",
        "-r",
        action="store_true",
        help="Print full tone report with 0-10 knob scales and clock positions",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress informational output (errors will still print to stderr)",
    )

    args = parser.parse_args(cli_args)

    # 1. Read input YAML
    try:
        if args.input == "-":
            yaml_content = sys.stdin.read()
            preset = NollyPreset.from_yaml(yaml_content)
        else:
            in_path = Path(args.input)
            if not in_path.exists():
                print(f"Error: Input YAML file not found: {in_path}", file=sys.stderr)
                return 1
            preset = NollyPreset.load(in_path)
    except Exception as e:
        print(f"Error reading/parsing input YAML: {e}", file=sys.stderr)
        return 1

    # 2. Optional name override
    if args.name:
        preset.name = args.name

    # 3. Ensure destination directory exists and write XML
    out_path = Path(args.output)
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        preset.save_xml(out_path)
    except Exception as e:
        print(f"Error saving XML preset to '{out_path}': {e}", file=sys.stderr)
        return 1

    # 4. Verify written binary is readable
    try:
        verified = NollyPreset.load_xml(out_path)
        if not args.quiet:
            file_size = out_path.stat().st_size
            amp_name = verified.selected_amp_name
            print(f"SUCCESS: Generated Nolly X preset '{verified.name}' ({amp_name})")
            print(f"Path: {out_path.resolve()} ({file_size} bytes)")
            if args.report:
                print("\n" + verified.generate_tone_report(base_preset=out_path.stem))
    except Exception as e:
        print(f"Warning: Written file could not be verified: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
