# Archetype Nolly X Tone Suite & Preset Engine

A comprehensive pure-Python toolsuite for preset management, search, reverse engineering, atomic tone creation, and AI agent integration (Antigravity / LLMs) for **Archetype Nolly X** by Neural DSP.

It parses and serializes the internal binary **JUCE `ValueTree`** structure with byte-by-byte precision (100% roundtrip bit-for-bit fidelity) and provides high-speed YAML representations for interacting with presets in milliseconds.

---

## 1-Command Installation & Restore

If you reinstall Archetype Nolly X or switch machines, you can download and restore the complete toolsuite, AI instructions (`AGENTS.md`), YAML preset catalog, and all your custom tones in `User/` with **a single PowerShell command**:

```powershell
irm https://raw.githubusercontent.com/JorgeRuizDev/archetype-nolly-x/main/install.ps1 | iex
```

### What does this command do automatically?
1. Detects or initializes the official Windows preset directory (`C:\ProgramData\Neural DSP\Archetype Nolly X`).
2. Configures Git permissions (`safe.directory`) to prevent security blocks in `ProgramData`.
3. Downloads and synchronizes the toolsuite, `AGENTS.md`, YAML preset catalog, and user songs in `User/` (safely overlaying without conflicting with the factory XML presets installed by Nolly).
4. Sets up the Python virtual environment with `uv` or standard `python`.
5. Runs a smoke test to ensure `.\nolly.cmd` is ready for instant use.

---

## Manual Installation via Git

If you prefer using Git directly from your terminal:

### Option A: After reinstalling Nolly (directory already exists with factory presets)
```cmd
cd /d "%ProgramData%\Neural DSP\Archetype Nolly X"
git config --global --add safe.directory "C:/ProgramData/Neural DSP/Archetype Nolly X"
git init -b main
git remote add origin https://github.com/JorgeRuizDev/archetype-nolly-x.git
git fetch origin main
git checkout -f main
uv sync
```

### Option B: On a fresh machine (before installing Nolly)
```cmd
git clone https://github.com/JorgeRuizDev/archetype-nolly-x.git "%ProgramData%\Neural DSP\Archetype Nolly X"
cd /d "%ProgramData%\Neural DSP\Archetype Nolly X"
uv sync
```

---

## Fast CLI Workflow (nolly.cmd)

The root `.\nolly.cmd` script executes in ~0.25 seconds using the optimized `.venv` virtual environment:

### 1. Instant Catalog Search
```cmd
.\nolly.cmd search "metal" --amp rhythm
.\nolly.cmd search "clean"
```

### 2. 1-Step Tone Creation & Validation
Clones a base preset, applies parameter updates (supports decimal floats, 0–10 scale, and clock notation), compiles both `.xml` and `.yml`, validates binary integrity, and prints a formatted guitar tone report:

```cmd
.\nolly.cmd create --base "All-Purpose Metal Rhythm" --song "Tool - Lateralus" --num "00" --name "Main Drop D Riff" --set "rhythmGain=0.72" "rhythmBass=7.5/10" "rhythmPresence=2:30" "gateThreshold=-65"
```

### 3. Detailed Preset Inspection (with Clock & 0–10 Scale Table)
```cmd
.\nolly.cmd inspect "User/Tool - Lateralus/00 - Main Drop D Riff.xml"
```

---

## AI Assistant Integration (AGENTS.md)

This repository includes [AGENTS.md](AGENTS.md), which specifies the exact rules for AI models (Antigravity, Cursor, Claude Code, etc.) to craft tailored presets for your guitar gear (e.g., Squier Stratocaster SSS, Scarlett Solo interface, Drop D / E Standard tunings).

Organizational rules:
- Presets are saved to `.\User\<Band> - <Song>\XX - <Name>.xml` and `.yml`.
- Knobs are always presented in both **approximate clock positions** (7:00 to 5:00) and **0 to 10 scale** (since the plugin UI does not show numerical values on amp/pedal knobs).

---

## Python API Usage

The package is directly importable without manual `sys.path` configuration:

```python
from nolly import NollyPreset, value_to_clock, clock_to_value, scale10_to_value

# Universal polymorphic loader (.xml or .yml)
preset = NollyPreset.load(r".\yml\Nolly\All-Purpose Metal Rhythm.yml")

# Smart parameter manipulation
preset.set_parameter("rhythmGain", "2:30")     # Converts clock notation to float
preset.set_parameter("rhythmBass", "7.0/10")   # Converts 0-10 scale to float
preset.set_parameter("gateActive", "true")

# Dual format export
preset.save(r".\User\My Band - Song\00 - Riff.yml")
preset.save(r".\User\My Band - Song\00 - Riff.xml")

# Formatted Markdown tone report
print(preset.generate_tone_report(song="My Band - Song", preset_num="00"))
```

---

## Testing

Run the test suite (15 unit tests covering byte-for-byte binary roundtrip and parsing):

```cmd
uv run pytest
```

---

## Repository Structure

```text
├── AGENTS.md            # AI agent instructions and guitar gear specifications
├── README.md            # Main documentation (this file)
├── install.ps1          # 1-line PowerShell installer and restorer
├── nolly.py             # Root module shim and CLI entrypoint
├── nolly.cmd            # Windows batch CLI runner
├── xml2yml.cmd          # Standalone XML to YAML converter
├── yml2xml.cmd          # Standalone YAML to XML converter
├── pyproject.toml       # Python package definition and dependencies
├── uv.lock              # Reproducible dependency lockfile
├── preset_editor/       # JUCE ValueTree binary parser & preset engine
│   ├── cli.py           # Unified CLI (search, create, inspect)
│   ├── juce_valuetree.py# Pure JUCE binary serializer / deserializer
│   ├── nolly_preset.py  # Preset model, parameter mapping & clock conversions
│   └── tests/           # pytest unit test suite
├── yml/                 # Complete factory catalog converted to YAML for rapid search
└── User/                # User presets organized by song folders
```
