#!/usr/bin/env python3
"""
Archetype Nolly X Unified CLI Tool ('nolly')
High-speed preset management, search, creation, and tone inspection.
Designed for instant AI agent workflows and guitarist pair-programming.
"""

from __future__ import annotations

import argparse
import json
import os
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
from typing import Any, Dict, List, Optional, Tuple

# Ensure package and root paths are available
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
for p in (str(ROOT_DIR), str(SCRIPT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from nolly_preset import (
        AMP_NAMES,
        NollyPreset,
        clock_to_value,
        parse_param_value,
        scale10_to_value,
        value_to_clock,
    )
except ImportError:
    from preset_editor.nolly_preset import (
        AMP_NAMES,
        NollyPreset,
        clock_to_value,
        parse_param_value,
        scale10_to_value,
        value_to_clock,
    )


def resolve_base_preset(base_arg: str, root_dir: Path) -> Path:
    """
    Finds a base preset from an exact path, relative path, or search query.
    """
    # 1. Exact path
    p = Path(base_arg)
    if p.is_file():
        return p.resolve()

    # 2. Relative to root or yml
    for candidate in [
        root_dir / base_arg,
        root_dir / "yml" / base_arg,
        root_dir / "yml" / "Nolly" / base_arg,
        root_dir / "yml" / "Neural DSP" / base_arg,
        root_dir / "yml" / "Artists" / base_arg,
        root_dir / "yml" / "User" / base_arg,
        root_dir / "User" / base_arg,
    ]:
        if candidate.is_file():
            return candidate.resolve()
        # Try appending .yml
        if candidate.with_suffix(".yml").is_file():
            return candidate.with_suffix(".yml").resolve()
        # Try appending .xml
        if candidate.with_suffix(".xml").is_file():
            return candidate.with_suffix(".xml").resolve()

    # 3. Fuzzy search in yml folder
    yml_dir = root_dir / "yml"
    query = base_arg.lower().replace("-", " ").strip()
    matches: List[Tuple[int, Path]] = []

    for f in yml_dir.rglob("*.yml"):
        stem = f.stem.lower().replace("-", " ")
        if query in stem:
            score = 100 if query == stem else (50 if stem.startswith(query) else 20)
            matches.append((score, f))

    if matches:
        matches.sort(key=lambda x: x[0], reverse=True)
        return matches[0][1].resolve()

    raise FileNotFoundError(f"Could not resolve base preset '{base_arg}'. Use 'nolly search <term>' to list presets.")


# -----------------------------------------------------------------------------
# CLI Commands
# -----------------------------------------------------------------------------

def cmd_search(args: argparse.Namespace) -> int:
    """Fast search across all YAML presets in ./yml and ./User."""
    root_dir = ROOT_DIR
    search_dirs = [root_dir / "yml"]
    if getattr(args, "include_user", True):
        search_dirs.append(root_dir / "User")

    query = (args.query or "").lower().strip()
    amp_filter = (args.amp or "").lower().strip()
    max_results = args.limit or 15

    results = []

    for s_dir in search_dirs:
        if not s_dir.exists():
            continue
        for fpath in s_dir.rglob("*.yml"):
            rel_path = fpath.relative_to(root_dir)
            name_str = fpath.stem.lower()
            rel_str = str(rel_path).lower()

            if query and (query not in name_str and query not in rel_str):
                continue

            # Load preset metadata
            try:
                preset = NollyPreset.load(fpath)
                summ = preset.summary()
                amp_name = summ["selected_amp"]

                if amp_filter:
                    if amp_filter in ("clean", "0") and "clean" not in amp_name.lower():
                        continue
                    if amp_filter in ("crunch", "1") and "crunch" not in amp_name.lower():
                        continue
                    if amp_filter in ("rhythm", "2") and "rhythm" not in amp_name.lower():
                        continue
                    if amp_filter in ("lead", "3") and "lead" not in amp_name.lower():
                        continue

                active_pedals = []
                if summ["gate_active"]:
                    active_pedals.append("Gate")
                if summ["overdrive1_active"]:
                    active_pedals.append("OD1")
                if summ["overdrive2_active"]:
                    active_pedals.append("OD2")
                if summ["compressor_active"]:
                    active_pedals.append("Comp")
                if summ["pre_delay_active"]:
                    active_pedals.append("PreDelay")
                if summ["post_delay_active"]:
                    active_pedals.append("Delay")
                if summ["reverb_active"]:
                    active_pedals.append("Reverb")

                results.append({
                    "name": preset.name,
                    "file": str(rel_path).replace("\\", "/"),
                    "amp": amp_name,
                    "fx": ", ".join(active_pedals) if active_pedals else "-",
                })
            except Exception:
                continue

    if args.json:
        print(json.dumps(results[:max_results], indent=2))
        return 0

    if not results:
        print(f"No presets found matching query '{query}'" + (f" with amp '{amp_filter}'" if amp_filter else ""))
        return 0

    print(f"\nFound {len(results)} preset(s) matching '{query or '*'}':\n")
    print(f"| {'Preset Name':<30} | {'Amp Model':<18} | {'Active FX':<18} | {'Path':<40} |")
    print(f"| {'-' * 30} | {'-' * 18} | {'-' * 18} | {'-' * 40} |")
    for r in results[:max_results]:
        print(f"| {r['name']:<30} | {r['amp']:<18} | {r['fx']:<18} | {r['file']:<40} |")

    if len(results) > max_results:
        print(f"\n... and {len(results) - max_results} more. Use --limit to show more.")
    return 0


def cmd_create(args: argparse.Namespace) -> int:
    """
    Atomic Tone Creation Command:
    - Finds base preset
    - Clones and modifies parameters
    - Automatically formats numbering ('00 - Name')
    - Writes both .yml and native JUCE .xml
    - Verifies .xml binary validity
    - Prints full markdown tone report with 0-10 scale and clock positions
    """
    root_dir = ROOT_DIR

    # 1. Resolve base preset
    try:
        base_path = resolve_base_preset(args.base, root_dir)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # 2. Load base
    try:
        preset = NollyPreset.load(base_path)
    except Exception as e:
        print(f"Error loading base preset '{base_path}': {e}", file=sys.stderr)
        return 1

    # 3. Determine song folder and preset name
    song = args.song.strip() if args.song else "Custom"
    num = str(args.num).zfill(2) if args.num is not None else "00"
    raw_name = args.name.strip() if args.name else base_path.stem

    # Form formatted filename/preset name
    if raw_name.startswith(f"{num} - ") or raw_name.startswith(f"{num} "):
        preset_display_name = raw_name
        file_stem = raw_name
    else:
        preset_display_name = f"{num} - {raw_name}"
        file_stem = f"{num} - {raw_name}"

    preset.name = preset_display_name

    # 4. Apply parameter modifications
    assignments = args.set or []
    modified_count = 0
    for assign in assignments:
        if "=" not in assign:
            print(f"Warning: Ignoring invalid assignment '{assign}' (format must be param=val)", file=sys.stderr)
            continue
        k, v = assign.split("=", 1)
        k, v = k.strip(), v.strip()
        if preset.set_parameter(k, v):
            modified_count += 1
        else:
            print(f"Warning: Parameter '{k}' not found in preset tree.", file=sys.stderr)

    # 5. Determine destination paths
    if args.dest_dir:
        dest_dir = Path(args.dest_dir)
    else:
        dest_dir = root_dir / "User" / song

    dest_yml = dest_dir / f"{file_stem}.yml"
    dest_xml = dest_dir / f"{file_stem}.xml"

    if args.dry_run:
        print(f"[DRY-RUN] Would create:")
        print(f"  YAML: {dest_yml}")
        print(f"  XML:  {dest_xml}")
        print(f"  Applied {modified_count} parameter modifications.")
        print("\n" + preset.generate_tone_report(song=song, preset_num=num, base_preset=str(base_path.stem)))
        return 0

    # 6. Save YAML and XML
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        preset.save_yaml(dest_yml)
        preset.save_xml(dest_xml)
    except Exception as e:
        print(f"Error writing preset files: {e}", file=sys.stderr)
        return 1

    # 7. Verify XML binary validity
    try:
        verified = NollyPreset.load_xml(dest_xml)
        assert verified.name == preset.name
        xml_size = dest_xml.stat().st_size
        yml_size = dest_yml.stat().st_size
    except Exception as e:
        print(f"Error: Generated XML preset failed verification: {e}", file=sys.stderr)
        return 1

    # 8. Print Output
    rel_yml = dest_yml.relative_to(root_dir) if dest_yml.is_relative_to(root_dir) else dest_yml
    rel_xml = dest_xml.relative_to(root_dir) if dest_xml.is_relative_to(root_dir) else dest_xml

    print(f"SUCCESS: Generated Nolly X preset '{preset.name}'")
    print(f"  - XML: {rel_xml} ({xml_size} bytes, verified)")
    print(f"  - YML: {rel_yml} ({yml_size} bytes)")
    print(f"  - Changes applied: {modified_count}")

    if not args.quiet:
        print("\n" + "=" * 70)
        report = preset.generate_tone_report(
            song=song,
            preset_num=num,
            base_preset=str(base_path.stem),
        )
        print(report)
        print("=" * 70)

    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    """Inspects any preset (XML or YAML) and displays gear and knob table."""
    in_path = Path(args.file)
    if not in_path.exists():
        print(f"Error: File not found: {in_path}", file=sys.stderr)
        return 1

    try:
        preset = NollyPreset.load(in_path)
    except Exception as e:
        print(f"Error reading preset '{in_path}': {e}", file=sys.stderr)
        return 1

    if args.json:
        data = {
            "summary": preset.summary(),
            "active_controls": preset.get_active_controls(),
        }
        print(json.dumps(data, indent=2))
        return 0

    print(preset.generate_tone_report(song=in_path.parent.name, base_preset=in_path.stem))
    return 0


def cmd_edit(args: argparse.Namespace) -> int:
    """Modifies parameters in an existing preset (.xml and/or .yml)."""
    target = Path(args.file)
    if not target.exists():
        print(f"Error: File not found: {target}", file=sys.stderr)
        return 1

    preset = NollyPreset.load(target)
    modified = 0

    if args.name:
        preset.name = args.name
        modified += 1

    for assign in (args.set or []):
        if "=" in assign:
            k, v = assign.split("=", 1)
            if preset.set_parameter(k.strip(), v.strip()):
                modified += 1
            else:
                print(f"Warning: Parameter '{k}' not found in preset.", file=sys.stderr)

    # Save target
    preset.save(target)

    # If twin exists (.xml <-> .yml), update twin as well
    if target.suffix.lower() == ".yml":
        twin = target.with_suffix(".xml")
        if twin.exists():
            preset.save_xml(twin)
            print(f"Updated twin XML: {twin}")
    elif target.suffix.lower() == ".xml":
        twin = target.with_suffix(".yml")
        if twin.exists():
            preset.save_yaml(twin)
            print(f"Updated twin YAML: {twin}")

    print(f"SUCCESS: Applied {modified} change(s) to '{target}'")
    if not args.quiet:
        print("\n" + preset.format_knob_table(active_only=True))
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    """Compares two presets and prints differences."""
    p1 = Path(args.file1)
    p2 = Path(args.file2)
    preset1 = NollyPreset.load(p1)
    preset2 = NollyPreset.load(p2)

    diffs = preset1.diff(preset2)
    if not diffs:
        print("Presets are identical.")
        return 0

    print(f"\nDifferences between '{p1.name}' and '{p2.name}' ({len(diffs)} parameter(s)):\n")
    print(f"| {'Parámetro':<30} | {p1.stem[:18]:<18} | {p2.stem[:18]:<18} | {'Escala / Reloj 1':<20} | {'Escala / Reloj 2':<20} |")
    print(f"| {'-' * 30} | {'-' * 18} | {'-' * 18} | {'-' * 20} | {'-' * 20} |")

    for k, (v1, v2) in diffs.items():
        n1, n2 = parse_numeric(v1), parse_numeric(v2)
        desc1 = f"{n1*10:.1f}/10 (~{value_to_clock(n1)})" if (n1 is not None and 0 <= n1 <= 1) else str(v1)
        desc2 = f"{n2*10:.1f}/10 (~{value_to_clock(n2)})" if (n2 is not None and 0 <= n2 <= 1) else str(v2)
        print(f"| {k:<30} | {str(v1):<18} | {str(v2):<18} | {desc1:<20} | {desc2:<20} |")

    return 0


def cmd_convert(args: argparse.Namespace) -> int:
    """Universal XML <-> YAML preset converter with verification."""
    in_path = Path(args.input)
    if not in_path.exists():
        print(f"Error: File not found: {in_path}", file=sys.stderr)
        return 1

    preset = NollyPreset.load(in_path)
    if args.name:
        preset.name = args.name

    if args.output:
        out_path = Path(args.output)
    else:
        # Toggle between .xml and .yml
        if in_path.suffix.lower() == ".xml":
            out_path = in_path.with_suffix(".yml")
        else:
            out_path = in_path.with_suffix(".xml")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    preset.save(out_path)

    # Verify
    if out_path.suffix.lower() == ".xml":
        NollyPreset.load_xml(out_path)

    print(f"SUCCESS: Converted '{in_path.name}' -> '{out_path}' ({out_path.stat().st_size} bytes)")
    if args.report:
        print("\n" + preset.generate_tone_report(base_preset=in_path.stem))
    return 0


# -----------------------------------------------------------------------------
# Parser Definition
# -----------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nolly",
        description="Archetype Nolly X Tone Suite: Fast preset editor, search, and validation CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # 1. create (Tone Generator)
    p_create = subparsers.add_parser("create", aliases=["tone", "new"], help="Generate a verified tone preset in one step")
    p_create.add_argument("--base", "-b", required=True, help="Base preset path or keyword (e.g. 'Modern Rhythm')")
    p_create.add_argument("--song", "-s", required=True, help="Band/Song folder name (e.g. 'Tool - Schism')")
    p_create.add_argument("--num", "-n", default="00", help="Two-digit sequence number (default: '00')")
    p_create.add_argument("--name", required=True, help="Descriptive preset name (e.g. 'Main Rhythm Riff')")
    p_create.add_argument("--set", "-p", nargs="*", default=[], help="Parameter assignments (e.g. rhythmGain=0.75 gateActive=true)")
    p_create.add_argument("--dest-dir", help="Custom destination folder (default: .\\User\\<song>)")
    p_create.add_argument("--dry-run", action="store_true", help="Simulate without writing files")
    p_create.add_argument("--quiet", "-q", action="store_true", help="Suppress tone report")
    p_create.set_defaults(func=cmd_create)

    # 2. search (Fast Preset Catalog Search)
    p_search = subparsers.add_parser("search", aliases=["find"], help="Search preset catalog by name, band, or amp")
    p_search.add_argument("query", nargs="?", default="", help="Keyword to search in preset filenames or paths")
    p_search.add_argument("--amp", "-a", choices=["clean", "crunch", "rhythm", "lead", "0", "1", "2", "3"], help="Filter by amplifier model")
    p_search.add_argument("--limit", "-l", type=int, default=15, help="Maximum number of results to display")
    p_search.add_argument("--no-user", dest="include_user", action="store_false", help="Exclude .\\User directory from search")
    p_search.add_argument("--json", action="store_true", help="Output results in JSON format")
    p_search.set_defaults(func=cmd_search)

    # 3. inspect (Tone Inspection & Knob Dump)
    p_insp = subparsers.add_parser("inspect", aliases=["dump", "show", "info"], help="Inspect preset gear, pedals, and exact knob table")
    p_insp.add_argument("file", help="Path to .xml or .yml preset file")
    p_insp.add_argument("--json", action="store_true", help="Output raw JSON data")
    p_insp.set_defaults(func=cmd_inspect)

    # 4. edit (In-place parameter editor)
    p_edit = subparsers.add_parser("edit", help="Modify parameters in an existing preset")
    p_edit.add_argument("file", help="Path to preset file to edit (.yml or .xml)")
    p_edit.add_argument("--set", "-p", nargs="+", required=True, help="Parameter assignments (param=value)")
    p_edit.add_argument("--name", help="Update preset name")
    p_edit.add_argument("--quiet", "-q", action="store_true", help="Suppress knob table output")
    p_edit.set_defaults(func=cmd_edit)

    # 5. diff (Compare presets)
    p_diff = subparsers.add_parser("diff", help="Compare two presets")
    p_diff.add_argument("file1", help="First preset file (.xml or .yml)")
    p_diff.add_argument("file2", help="Second preset file (.xml or .yml)")
    p_diff.set_defaults(func=cmd_diff)

    # 6. convert (Universal XML <-> YAML)
    p_conv = subparsers.add_parser("convert", help="Convert between XML and YAML")
    p_conv.add_argument("input", help="Source preset file")
    p_conv.add_argument("output", nargs="?", help="Destination preset file")
    p_conv.add_argument("--name", help="Override preset name")
    p_conv.add_argument("--report", action="store_true", help="Print tone report after conversion")
    p_conv.set_defaults(func=cmd_convert)

    return parser


def main(cli_args: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(cli_args)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
