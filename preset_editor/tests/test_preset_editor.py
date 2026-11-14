"""
Unit tests for Archetype Nolly X Preset Editor & JUCE ValueTree parser.
"""

import glob
from pathlib import Path
import pytest

try:
    from juce_valuetree import (
        JuceInputStream,
        JuceOutputStream,
        read_value_tree,
        write_value_tree,
    )
    from nolly_preset import NollyPreset, value_to_clock
except ImportError:
    from preset_editor.juce_valuetree import (
        JuceInputStream,
        JuceOutputStream,
        read_value_tree,
        write_value_tree,
    )
    from preset_editor.nolly_preset import NollyPreset, value_to_clock


ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_XML = ROOT_DIR / "Default.xml"


def test_roundtrip_default_xml():
    """Verify bit-for-bit roundtrip serialization of Default.xml."""
    assert DEFAULT_XML.exists(), f"Default.xml not found at {DEFAULT_XML}"
    with open(DEFAULT_XML, "rb") as f:
        orig = f.read()

    tree = read_value_tree(orig)
    assert tree is not None
    assert tree.tag == "nolly-x"

    reserialized = write_value_tree(tree)
    assert reserialized == orig, f"Roundtrip mismatch! Orig len={len(orig)}, reserialized len={len(reserialized)}"


def test_roundtrip_all_presets():
    """Verify bit-for-bit roundtrip serialization across all preset files in the folder."""
    all_xmls = list(ROOT_DIR.glob("**/*.xml"))
    # Exclude any temporary or venv xmls if any
    all_xmls = [p for p in all_xmls if ".venv" not in str(p)]
    assert len(all_xmls) > 10, f"Expected many presets, found {len(all_xmls)}"

    passed = 0
    for xml_path in all_xmls:
        with open(xml_path, "rb") as f:
            data = f.read()
        tree = read_value_tree(data)
        assert tree is not None
        out = write_value_tree(tree)
        assert out == data, f"Mismatch in preset: {xml_path}"
        passed += 1

    assert passed == len(all_xmls)


def test_yaml_roundtrip_all_presets():
    """Verify XML -> YAML -> XML byte-accuracy across all presets in the directory."""
    all_xmls = [p for p in ROOT_DIR.glob("**/*.xml") if ".venv" not in str(p)]
    assert len(all_xmls) > 10, f"Expected many presets, found {len(all_xmls)}"

    passed = 0
    for xml_path in all_xmls:
        with open(xml_path, "rb") as f:
            orig = f.read()

        preset = NollyPreset.load(orig)
        yaml_str = preset.to_yaml()
        reloaded = NollyPreset.from_yaml(yaml_str)
        converted = reloaded.to_bytes()

        assert converted == orig, f"Byte mismatch in YAML roundtrip for: {xml_path}"
        passed += 1

    assert passed == len(all_xmls)


def test_preset_metadata_and_summary():
    """Verify high-level preset properties and summary."""
    preset = NollyPreset.load(DEFAULT_XML)
    assert preset.name == "Default"
    assert preset.version == "1.0.0"
    assert preset.is_favorite is False
    assert preset.selected_amp_id in (0, 1, 2, 3)

    summary = preset.summary()
    assert summary["name"] == "Default"
    assert "selected_amp" in summary
    assert "gate_active" in summary


def test_edit_parameter_and_save(tmp_path):
    """Verify that editing parameters updates values and persists correctly."""
    preset = NollyPreset.load(DEFAULT_XML)

    # Edit parameters
    preset.name = "My Custom Test Preset"
    preset.is_favorite = True
    assert preset.set_parameter("overdrive1Active", "true")
    assert preset.set_parameter("overdrive1Drive", "0.65")
    assert preset.set_parameter("rhythmGain", "0.85")

    # Save to tmp_path
    out_file = tmp_path / "custom.xml"
    preset.save(out_file)
    assert out_file.exists()

    # Reload and verify
    reloaded = NollyPreset.load(out_file)
    assert reloaded.name == "My Custom Test Preset"
    assert reloaded.is_favorite is True
    assert reloaded.get_parameter("overdrive1Active") == "true"
    assert reloaded.get_parameter("overdrive1Drive") == "0.65"
    assert reloaded.get_parameter("rhythmGain") == "0.85"


def test_clock_representation():
    """Verify 0.0 - 1.0 to clock position conversion."""
    assert value_to_clock(0.0) == "7:00"
    assert value_to_clock(0.25) == "9:30" or value_to_clock(0.25) == "9:00" or "9:" in value_to_clock(0.25)
    assert value_to_clock(0.5) == "12:00"
    assert value_to_clock(0.75) == "2:30" or value_to_clock(0.75) == "3:00" or "2:" in value_to_clock(0.75)
    assert value_to_clock(1.0) == "5:00"


def test_json_roundtrip():
    """Verify exporting to JSON and importing back produces identical preset."""
    preset = NollyPreset.load(DEFAULT_XML)
    json_str = preset.to_json()
    reloaded = NollyPreset.from_json(json_str)

    assert reloaded.name == preset.name
    assert reloaded.to_bytes() == preset.to_bytes()


def test_yaml_roundtrip():
    """Verify exporting to YAML and importing back produces identical preset bytes."""
    preset = NollyPreset.load(DEFAULT_XML)
    yaml_str = preset.to_yaml()
    reloaded = NollyPreset.from_yaml(yaml_str)

    assert reloaded.name == preset.name
    assert reloaded.to_bytes() == preset.to_bytes()


def test_yaml_human_edited(tmp_path):
    """Verify that YAML edited with native Python/YAML types (floats, bools) converts to valid XML."""
    preset = NollyPreset.load(DEFAULT_XML)
    yaml_str = preset.to_yaml()

    # Modify YAML text directly as a human would
    yaml_str = yaml_str.replace("name: Default", "name: YAML Custom Tone")
    yaml_str = yaml_str.replace("overdrive1Active: 'false'", "overdrive1Active: true")
    yaml_str = yaml_str.replace("rhythmGain: '0.5'", "rhythmGain: 0.77")

    reloaded = NollyPreset.from_yaml(yaml_str)
    out_xml = tmp_path / "from_yaml.xml"
    reloaded.save(out_xml)

    # Load again as a fresh preset from XML
    verified = NollyPreset.load(out_xml)
    assert verified.name == "YAML Custom Tone"
    assert verified.get_parameter("overdrive1Active") == "true"
    assert verified.get_parameter("rhythmGain") == "0.77"


def test_diff():
    """Verify diff calculation between two presets."""
    p1 = NollyPreset.load(DEFAULT_XML)
    p2 = NollyPreset.load(DEFAULT_XML)

    p2.name = "Modified"
    p2.set_parameter("leadGain", "0.9")

    diffs = p1.diff(p2)
    assert "name" in diffs
    assert "leadGain" in diffs
    assert diffs["name"] == ("Default", "Modified")


def test_yml2xml_and_xml2yml_cli(tmp_path):
    """Test standalone yml2xml and xml2yml CLI scripts."""
    import subprocess
    import sys

    # 1. Export Default.xml to YAML via xml2yml.py
    yml_file = tmp_path / "exported.yml"
    xml2yml_script = ROOT_DIR / "preset_editor" / "xml2yml.py"
    res1 = subprocess.run(
        [sys.executable, str(xml2yml_script), str(DEFAULT_XML), str(yml_file)],
        capture_output=True,
        text=True,
    )
    assert res1.returncode == 0
    assert yml_file.exists()

    # 2. Convert exported.yml back to XML via yml2xml.py
    out_xml = tmp_path / "SubDir" / "rebuilt.xml"
    yml2xml_script = ROOT_DIR / "preset_editor" / "yml2xml.py"
    res2 = subprocess.run(
        [sys.executable, str(yml2xml_script), str(yml_file), str(out_xml), "--name", "Rebuilt CLI Tone"],
        capture_output=True,
        text=True,
    )
    assert res2.returncode == 0
    assert out_xml.exists()

    # 3. Verify reconstructed preset
    verified = NollyPreset.load(out_xml)
    assert verified.name == "Rebuilt CLI Tone"


def test_clock_and_scale_conversion():
    """Verify clock face to normalized value and scale conversion."""
    from preset_editor.nolly_preset import clock_to_value, scale10_to_value, parse_param_value

    assert clock_to_value("7:00") == 0.0
    assert clock_to_value("12:00") == 0.5
    assert clock_to_value("5:00") == 1.0
    assert clock_to_value("1:30") == 0.65
    assert clock_to_value("~2:15") == 0.725

    assert value_to_clock(0.0) == "7:00"
    assert value_to_clock(0.5) == "12:00"
    assert value_to_clock(0.65) == "1:30"
    assert value_to_clock(1.0) == "5:00"

    assert scale10_to_value("7.2/10") == 0.72
    assert scale10_to_value(8.5) == 0.85

    assert parse_param_value("1:30") == "0.65"
    assert parse_param_value("7.2/10") == "0.72"
    assert parse_param_value("true") == "true"
    assert parse_param_value("off") == "false"


def test_polymorphic_load_and_save(tmp_path):
    """Verify smart universal load and save for XML and YAML."""
    preset = NollyPreset.load(DEFAULT_XML)
    
    # Save as YAML
    yml_path = tmp_path / "test_tone.yml"
    preset.save(yml_path)
    assert yml_path.exists()

    # Load from YAML via smart load
    p_yml = NollyPreset.load(yml_path)
    assert p_yml.name == preset.name

    # Load from YAML via from_yaml_file
    p_yml2 = NollyPreset.from_yaml_file(yml_path)
    assert p_yml2.name == preset.name

    # Save as XML
    xml_path = tmp_path / "test_tone.xml"
    p_yml.save(xml_path)
    assert xml_path.exists()

    # Reload XML
    p_xml = NollyPreset.load(xml_path)
    assert p_xml.name == preset.name
    assert p_xml.to_bytes() == preset.to_bytes()


def test_parameter_setting_clock_and_scale():
    """Verify setting parameters with clock and scale strings."""
    preset = NollyPreset.load(DEFAULT_XML)
    
    preset.set_parameter("rhythmGain", "1:30")
    assert preset.get_parameter("rhythmGain") == "0.65"

    preset.set_parameter("rhythmBass", "8.0/10")
    assert preset.get_parameter("rhythmBass") == "0.8"

    table = preset.format_knob_table()
    assert "rhythmGain" in table
    assert "1:30" in table
    assert "6.5" in table

    report = preset.generate_tone_report(song="Test Song")
    assert "Test Song" in report
    assert "Squier Stratocaster SSS" in report


def test_cli_search_and_create(tmp_path):
    """Test nolly CLI search and create commands."""
    from preset_editor.cli import build_parser

    parser = build_parser()
    
    # 1. Search
    args_search = parser.parse_args(["search", "metal", "--limit", "5"])
    assert args_search.func(args_search) == 0

    # 2. Create in tmp_path
    args_create = parser.parse_args([
        "create",
        "--base", "All-Purpose Metal Rhythm",
        "--song", "Meshuggah - Bleed",
        "--num", "01",
        "--name", "Heavy Chug",
        "--dest-dir", str(tmp_path),
        "--set", "rhythmGain=1:30", "gateActive=true", "gateThreshold=-65",
        "--quiet",
    ])
    assert args_create.func(args_create) == 0

    created_yml = tmp_path / "01 - Heavy Chug.yml"
    created_xml = tmp_path / "01 - Heavy Chug.xml"
    assert created_yml.exists()
    assert created_xml.exists()

    p_created = NollyPreset.load(created_xml)
    assert p_created.name == "01 - Heavy Chug"
    assert p_created.get_parameter("rhythmGain") == "0.65"
    assert p_created.get_parameter("gateThreshold") == "-65"

