# Archetype Nolly X Preset Editor

A pure-Python library and CLI built from scratch based on the **JUCE** framework source code specifications (`juce_ValueTree.cpp`, `juce_Variant.cpp`, `juce_InputStream.cpp`, and `juce_OutputStream.cpp`), capable of reading, inspecting, editing, and serializing **Archetype Nolly X** `.xml` preset files with **byte-for-byte fidelity (100% bit-for-bit roundtrip)**.

The project is managed with [uv](https://docs.astral.sh/uv/).

---

## 🎸 Technical Context: What Are These `.xml` Files?

Despite their `.xml` file extension, Archetype Nolly X presets (and other Neural DSP plugins) are neither plain text nor standard XML. They are binary streams representing the internal **`juce::ValueTree`** structure serialized via `ValueTree::writeToStream()` and `var::writeToStream()`:

1. **Node Tag**: UTF-8 string terminated with `\0` (e.g., `"nolly-x"`).
2. **Property Count**: Compressed variable-length integer (`InputStream::readCompressedInt()`).
3. **Property-Value Pairs**:
   - Property name (UTF-8 string terminated with `\0`).
   - Typed `juce::var` value:
     - Type marker (`varMarker_Int=1`, `varMarker_BoolTrue=2`, `varMarker_BoolFalse=3`, `varMarker_Double=4`, `varMarker_String=5`, `varMarker_Int64=6`, `varMarker_Array=7`, `varMarker_Binary=8`).
     - Value payload according to type (packed length or fixed little-endian bytes).
4. **Child Nodes**: Number of child nodes (compressed integer) followed recursively by each subtree.

This package implements full serializers and deserializers without heavy third-party dependencies.

---

## 🚀 Requirements & Installation

Only `uv` (or Python 3.11+) is required:

```bash
cd preset_editor
uv sync
```

---

## ⚡ Unified CLI: `nolly.cmd` (For AI Agents & Guitarists)

The repository root includes the ultra-fast `nolly.cmd` tool (executes in ~0.25s) that automates search, 1-step tone generation, verification, and knob table reporting:

```bash
# 1. Instant catalog search
.\nolly.cmd search "metal" --amp rhythm

# 2. Atomic tone creation (clones base, edits, compiles XML+YML, validates, and prints report)
.\nolly.cmd create --base "All-Purpose Metal Rhythm" \
                   --song "Tool - Lateralus" \
                   --num "00" \
                   --name "Main Drop D Riff" \
                   --set "rhythmGain=0.72" "rhythmBass=0.6" "rhythmPresence=2:30" "gateThreshold=-65"

# 3. Detailed inspection with clock table and 0-10 scale
.\nolly.cmd inspect "User/Tool - Lateralus/00 - Main Drop D Riff.xml"
```

---

## 🛠️ Command-Line Interface (CLI)

All commands can be executed via `uv run python main.py <command>` from the `preset_editor` folder:

### 1. View Preset Summary (`info`)
Displays the selected amp, cabs, noise gate, and active pedals:
```bash
uv run python main.py info ../Default.xml
```

### 2. Inspect All Parameters (`dump`)
Displays values for all parameters organized by section (Amp, Gate, Overdrive, Delay, Reverb, etc.). For normalized knobs (0.0 to 1.0), it automatically displays both the 0 to 10 scale and the approximate clock position (7:00 to 5:00):
```bash
# Dump the entire preset
uv run python main.py dump ../Default.xml

# Filter by section (e.g., overdrive, amp, or reverb only)
uv run python main.py dump ../Default.xml -s overdrive
uv run python main.py dump ../Default.xml -s rhythm
uv run python main.py dump ../Default.xml -s reverb
```

### 3. Query a Specific Parameter (`get`)
```bash
uv run python main.py get ../Default.xml rhythmGain
uv run python main.py get ../Default.xml overdrive1Level
```

### 4. Modify a Single Parameter (`set`)
Modifies an existing parameter (overwrite in place or save to a new path with `-o`):
```bash
# Rename preset
uv run python main.py set ../Default.xml name "My Custom Tone" -o ../User/MyTone.xml

# Turn on Overdrive 1 and adjust gain
uv run python main.py set ../User/MyTone.xml overdrive1Active true
uv run python main.py set ../User/MyTone.xml rhythmGain 0.75
```

### 5. Modify Multiple Parameters (`set-many`)
```bash
uv run python main.py set-many ../User/MyTone.xml \
    overdrive1Active=true \
    overdrive1Drive=0.4 \
    rhythmGain=0.68 \
    rhythmTreble=0.55 \
    -o ../User/MyTone.xml
```

### 6. Duplicate and Edit an Existing Preset (`copy-edit`)
Recommended workflow for creating new presets from existing ones:
```bash
uv run python main.py copy-edit \
    --name "Deftones Heavy Rhythm" \
    ../Default.xml \
    "../User/Deftones - Be Quiet and Drive/00 - Heavy Riff.xml" \
    overdrive1Active=true \
    overdrive1Level=0.7 \
    rhythmGain=0.8
```

### 7. Compare Two Presets (`diff`)
Displays a clear comparison table showing which parameters differ between two preset files:
```bash
uv run python main.py diff ../Default.xml "../User/Deftones - Be Quiet and Drive (Far Away)/00 - Heavy Riff and Chorus.xml"
```

### 8. Export and Import YAML / YML (`to-yaml` / `from-yaml`)
The **YAML** format is human-readable, clean, and easily editable in any code editor:
```bash
# Export XML to YAML
uv run python main.py to-yaml ../Default.xml -o default.yml
# (or the alias to-yml)
uv run python main.py to-yml ../Default.xml -o default.yml

# Re-convert YAML to native binary XML
uv run python main.py from-yaml default.yml ../User/MyToneFromYaml.xml
# (or the alias from-yml)
uv run python main.py from-yml default.yml ../User/MyToneFromYaml.xml
```

### 9. Export and Import JSON (`to-json` / `from-json`)
Exports the full preset to an editable JSON file and compiles it back into native `.xml` format:
```bash
# Export to JSON
uv run python main.py to-json ../Default.xml -o default.json

# Import from JSON to XML preset
uv run python main.py from-json default.json new_preset.xml
```

### 10. Validate Bit-for-Bit Fidelity (`validate`)
Verifies that all `.xml` presets roundtrip through YAML with 100% binary accuracy:
```bash
uv run python main.py validate
```

---

## 🐍 Python Library Usage

You can also use the package directly in Python scripts or notebooks:

```python
from preset_editor import NollyPreset, value_to_clock

# 1. Load preset
preset = NollyPreset.load("../Default.xml")

# 2. Query metadata
print(f"Preset: {preset.name}")
print(f"Active Amp: {preset.selected_amp_name}")

# 3. Read a knob
gain = float(preset.get_parameter("rhythmGain"))
print(f"Gain: {gain * 10.0}/10 (Clock: ~{value_to_clock(gain)})")

# 4. Modify parameters
preset.name = "Lead Solos"
preset.selected_amp_id = 3  # 0=Clean, 1=Crunch, 2=Rhythm, 3=Lead
preset.set_parameter("leadGain", "0.75")
preset.set_parameter("overdrive1Active", "true")
preset.set_parameter("postDelayActive", "true")

# 5. Save to a new file
preset.save("../User/Lead Solos.xml")
```

---

## 🧪 Automated Testing

The project includes unit tests with `pytest` verifying byte-by-byte roundtrip fidelity across all presets:

```bash
uv run pytest
```
