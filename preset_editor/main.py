"""
Command-line interface for the Archetype Nolly X preset editor.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Handle relative or absolute import depending on execution mode
try:
    from .nolly_preset import NollyPreset, parse_numeric, value_to_clock
except ImportError:
    from nolly_preset import NollyPreset, parse_numeric, value_to_clock


def cmd_info(args: argparse.Namespace) -> None:
    preset = NollyPreset.load(args.file)
    summary = preset.summary()
    print("=" * 60)
    print(f" Preset: {summary['name']} (v{summary['version']})")
    print("=" * 60)
    print(f" Favorite:          {summary['is_favorite']}")
    print(f" Selected Amp:      {summary['selected_amp']}")
    print(f" Selected Cab:      {summary['selected_cab']}")
    print("-" * 60)
    print(" Active Sections / Pedals:")
    print(f"  - Gate:           {'ON' if summary['gate_active'] else 'OFF'} (Threshold: {summary['gate_threshold']} dB)")
    print(f"  - Doubler:        {'ON' if summary['doubler_active'] else 'OFF'}")
    print(f"  - Compressor:     {'ON' if summary['compressor_active'] else 'OFF'}")
    print(f"  - Overdrive 1:    {'ON' if summary['overdrive1_active'] else 'OFF'}")
    print(f"  - Overdrive 2:    {'ON' if summary['overdrive2_active'] else 'OFF'}")
    print(f"  - Pre Delay:      {'ON' if summary['pre_delay_active'] else 'OFF'}")
    print(f"  - Post Delay:     {'ON' if summary['post_delay_active'] else 'OFF'}")
    print(f"  - Reverb:         {'ON' if summary['reverb_active'] else 'OFF'}")
    print("=" * 60)


def cmd_dump(args: argparse.Namespace) -> None:
    preset = NollyPreset.load(args.file)
    sections = preset.list_sections()

    for sec_name, params in sections.items():
        if args.section and args.section.lower() not in sec_name.lower():
            continue
        print(f"\n[{sec_name}]")
        for k, v in params.items():
            num = parse_numeric(v)
            if num is not None and 0.0 <= num <= 1.0 and ("Level" in k or "Gain" in k or "Bass" in k or "Mid" in k or "Treble" in k or "Presence" in k or "Resonance" in k or "Depth" in k or "Master" in k or "Output" in k or "Tone" in k or "Drive" in k or "Mix" in k or "Feedback" in k or "Compression" in k):
                scale_10 = num * 10.0
                clock = value_to_clock(num)
                print(f"  {k:30} = {v:<12} (scale: {scale_10:4.1f}/10, clock: ~{clock})")
            else:
                print(f"  {k:30} = {v}")


def cmd_get(args: argparse.Namespace) -> None:
    preset = NollyPreset.load(args.file)
    val = preset.get_parameter(args.parameter)
    if val is None:
        print(f"Error: Parameter '{args.parameter}' not found in preset.", file=sys.stderr)
        sys.exit(1)

    num = parse_numeric(val)
    if num is not None and 0.0 <= num <= 1.0:
        scale_10 = num * 10.0
        clock = value_to_clock(num)
        print(f"{args.parameter} = {val} (scale: {scale_10:.1f}/10, clock: ~{clock})")
    else:
        print(f"{args.parameter} = {val}")


def parse_param_pair(pair: str) -> tuple[str, str]:
    if "=" not in pair:
        raise ValueError(f"Expected format key=value, got '{pair}'")
    k, v = pair.split("=", 1)
    return k.strip(), v.strip()


def cmd_set(args: argparse.Namespace) -> None:
    preset = NollyPreset.load(args.file)
    output_path = args.output or args.file

    if args.parameter.lower() in ("name", "presetname", "preset_name"):
        preset.name = args.value
        preset.save(output_path)
        print(f"Updated preset name to '{args.value}' -> Saved to {output_path}")
        return

    ok = preset.set_parameter(args.parameter, args.value)
    if not ok:
        print(f"Error: Parameter '{args.parameter}' not found in preset.", file=sys.stderr)
        sys.exit(1)

    preset.save(output_path)
    print(f"Updated '{args.parameter}' to '{args.value}' -> Saved to {output_path}")


def cmd_set_many(args: argparse.Namespace) -> None:
    preset = NollyPreset.load(args.file)
    output_path = args.output or args.file

    modified = 0
    for item in args.assignments:
        k, v = parse_param_pair(item)
        if k.lower() in ("name", "presetname", "preset_name"):
            preset.name = v
            modified += 1
            print(f" - name = {v}")
            continue

        ok = preset.set_parameter(k, v)
        if ok:
            modified += 1
            print(f" - {k} = {v}")
        else:
            print(f" [Warning] Parameter '{k}' not found in preset.", file=sys.stderr)

    preset.save(output_path)
    print(f"Applied {modified} changes -> Saved to {output_path}")


def cmd_copy_edit(args: argparse.Namespace) -> None:
    preset = NollyPreset.load(args.source)
    if args.name:
        preset.name = args.name

    modified = 0
    for item in args.assignments:
        k, v = parse_param_pair(item)
        if k.lower() in ("name", "presetname", "preset_name"):
            preset.name = v
            modified += 1
            print(f" - name = {v}")
            continue

        ok = preset.set_parameter(k, v)
        if ok:
            modified += 1
            print(f" - {k} = {v}")
        else:
            print(f" [Warning] Parameter '{k}' not found in preset.", file=sys.stderr)

    preset.save(args.dest)
    print(f"Copied from '{args.source}' with {modified} changes -> Created '{args.dest}' (Name: '{preset.name}')")


def cmd_to_json(args: argparse.Namespace) -> None:
    preset = NollyPreset.load(args.file)
    json_str = preset.to_json()
    if args.output:
        Path(args.output).write_text(json_str, encoding="utf-8")
        print(f"Exported preset JSON to {args.output}")
    else:
        print(json_str)


def cmd_from_json(args: argparse.Namespace) -> None:
    content = Path(args.json_file).read_text(encoding="utf-8")
    preset = NollyPreset.from_json(content)
    preset.save(args.output)
    print(f"Created preset XML from JSON -> {args.output} (Name: '{preset.name}')")


def cmd_to_yaml(args: argparse.Namespace) -> None:
    preset = NollyPreset.load(args.file)
    yaml_str = preset.to_yaml()
    if args.output:
        Path(args.output).write_text(yaml_str, encoding="utf-8")
        print(f"Exported preset YAML to {args.output}")
    else:
        print(yaml_str)


def cmd_from_yaml(args: argparse.Namespace) -> None:
    content = Path(args.yaml_file).read_text(encoding="utf-8")
    preset = NollyPreset.from_yaml(content)
    preset.save(args.output)
    print(f"Created preset XML from YAML -> {args.output} (Name: '{preset.name}')")


def cmd_validate(args: argparse.Namespace) -> None:
    target_dir = Path(args.path or "..")
    if target_dir.is_file():
        files = [target_dir]
    else:
        files = [p for p in target_dir.glob("**/*.xml") if ".venv" not in str(p)]

    if not files:
        print(f"No .xml files found in {target_dir}")
        return

    print(f"Validating XML -> YAML -> XML byte accuracy across {len(files)} preset(s)...")
    passed = 0
    mismatches = []

    for fpath in files:
        with open(fpath, "rb") as f:
            orig = f.read()
        try:
            preset = NollyPreset.load(orig)
            yaml_str = preset.to_yaml()
            reloaded = NollyPreset.from_yaml(yaml_str)
            reserialized = reloaded.to_bytes()

            if orig == reserialized:
                passed += 1
            else:
                mismatches.append((fpath, len(orig), len(reserialized)))
        except Exception as e:
            mismatches.append((fpath, "ERROR", str(e)))

    print(f"\nResult: {passed}/{len(files)} presets passed (100% byte-accurate).")
    if mismatches:
        print(f"Failed presets ({len(mismatches)}):")
        for m in mismatches:
            print(f" - {m[0]}: {m[1]} -> {m[2]}")
        sys.exit(1)
    else:
        print("All presets are 100% byte-accurate through the YAML roundtrip!")


def cmd_diff(args: argparse.Namespace) -> None:
    p1 = NollyPreset.load(args.file1)
    p2 = NollyPreset.load(args.file2)
    diffs = p1.diff(p2)

    if not diffs:
        print("Presets are identical.")
        return

    print(f"Differences between '{args.file1}' and '{args.file2}' ({len(diffs)} changes):")
    print(f" {'PARAMETER':<35} | {'FILE 1':<20} | {'FILE 2':<20}")
    print("-" * 80)
    for k, (v1, v2) in diffs.items():
        print(f" {k:<35} | {str(v1):<20} | {str(v2):<20}")


def main(cli_args: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="preset-editor",
        description="Archetype Nolly X Preset Editor (JUCE ValueTree Binary Parser & Serializer)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # info
    p_info = subparsers.add_parser("info", help="Display preset gear summary")
    p_info.add_argument("file", help="Path to preset .xml file")
    p_info.set_defaults(func=cmd_info)

    # dump
    p_dump = subparsers.add_parser("dump", help="Dump all parameter values by section")
    p_dump.add_argument("file", help="Path to preset .xml file")
    p_dump.add_argument("--section", "-s", help="Filter by section name (e.g. amp, fx, eq)")
    p_dump.set_defaults(func=cmd_dump)

    # get
    p_get = subparsers.add_parser("get", help="Get a single parameter value")
    p_get.add_argument("file", help="Path to preset .xml file")
    p_get.add_argument("parameter", help="Parameter name (case-insensitive)")
    p_get.set_defaults(func=cmd_get)

    # set
    p_set = subparsers.add_parser("set", help="Set a parameter value in a preset")
    p_set.add_argument("file", help="Path to preset .xml file")
    p_set.add_argument("parameter", help="Parameter name")
    p_set.add_argument("value", help="New value")
    p_set.add_argument("-o", "--output", help="Output file path (overwrites input if not specified)")
    p_set.set_defaults(func=cmd_set)

    # set-many
    p_many = subparsers.add_parser("set-many", help="Set multiple parameters at once")
    p_many.add_argument("file", help="Path to preset .xml file")
    p_many.add_argument("assignments", nargs="+", help="Parameter assignments (param=value)")
    p_many.add_argument("-o", "--output", help="Output file path")
    p_many.set_defaults(func=cmd_set_many)

    # copy-edit
    p_copy = subparsers.add_parser("copy-edit", help="Create a copy of a preset with edits")
    p_copy.add_argument("source", help="Path to source preset .xml")
    p_copy.add_argument("dest", help="Path to new destination preset .xml")
    p_copy.add_argument("--name", "-n", help="New preset name")
    p_copy.add_argument("assignments", nargs="*", help="Optional parameter assignments (param=value)")
    p_copy.set_defaults(func=cmd_copy_edit)

    # to-json
    p_to_json = subparsers.add_parser("to-json", help="Export preset to JSON")
    p_to_json.add_argument("file", help="Path to preset .xml")
    p_to_json.add_argument("-o", "--output", help="Output JSON file path")
    p_to_json.set_defaults(func=cmd_to_json)

    # from-json
    p_from_json = subparsers.add_parser("from-json", help="Convert JSON to preset XML")
    p_from_json.add_argument("json_file", help="Path to input JSON file")
    p_from_json.add_argument("output", help="Output preset .xml path")
    p_from_json.set_defaults(func=cmd_from_json)

    # to-yaml / to-yml
    p_to_yaml = subparsers.add_parser("to-yaml", aliases=["to-yml"], help="Export preset to YAML")
    p_to_yaml.add_argument("file", help="Path to preset .xml")
    p_to_yaml.add_argument("-o", "--output", help="Output YAML file path")
    p_to_yaml.set_defaults(func=cmd_to_yaml)

    # from-yaml / from-yml
    p_from_yaml = subparsers.add_parser("from-yaml", aliases=["from-yml"], help="Convert YAML to preset XML")
    p_from_yaml.add_argument("yaml_file", help="Path to input YAML file")
    p_from_yaml.add_argument("output", help="Output preset .xml path")
    p_from_yaml.set_defaults(func=cmd_from_yaml)

    # diff
    p_diff = subparsers.add_parser("diff", help="Compare two presets")
    p_diff.add_argument("file1", help="First preset .xml")
    p_diff.add_argument("file2", help="Second preset .xml")
    p_diff.set_defaults(func=cmd_diff)

    # validate
    p_val = subparsers.add_parser("validate", help="Validate XML -> YAML -> XML byte accuracy across presets")
    p_val.add_argument("path", nargs="?", default="..", help="Directory or file to validate (default: parent directory)")
    p_val.set_defaults(func=cmd_validate)

    args = parser.parse_args(cli_args)
    args.func(args)


if __name__ == "__main__":
    main()
