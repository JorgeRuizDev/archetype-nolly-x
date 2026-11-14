## Gear:
- Squier Stratocaster SSS
- Focusrite Scarlett Solo 2
- Usually - E Standard or D Drop. So use the transposer for lower tunes 
Try to suggest guitar config (pickup position, knobs, etc) with each preset. Avoid repeating yourself.

## Organisation

- Generate new tones under `.\User`
- Each song must be stored in a dedicated subfolder: `.\User\<band> - <song-name>`
- Each preset configuration must start with a two-digit number sequence starting from `00`:
  `.\User\<band> - <song-name>\XX - <name>.yml` and `.\User\<band> - <song-name>\XX - <name>.xml`
  (e.g., `00 - Intro Clean.xml`, `01 - Main Rhythm.xml`, `02 - Solo Lead.xml`)

## Fast AI Tone Generation Workflow (CLI All-in-One)

The suite provides a unified, high-speed CLI tool `.\nolly.cmd` designed to generate, compile, validate, and report presets in **a single command (~0.3s)**, eliminating multi-turn tool latency and manual math errors.

### Step 1: Search Base Preset (Optional)
If you need to explore or pick a base tone from the catalog:
```cmd
.\nolly.cmd search "<keyword>" [--amp clean|crunch|rhythm|lead]
```
Example:
`.\nolly.cmd search "metal" --amp rhythm`

### Step 2: Create & Validate Tone in 1 Step
Run `.\nolly.cmd create`:
```cmd
.\nolly.cmd create --base "<base_preset_or_keyword>" --song "<Band> - <Song>" --num "<XX>" --name "<Preset Name>" --set param=val ...
```
Example:
```cmd
.\nolly.cmd create --base "All-Purpose Metal Rhythm" --song "Tool - Lateralus" --num "00" --name "Main Drop D Riff" --set "rhythmGain=0.72" "rhythmBass=0.6" "rhythmPresence=2:30" "gateThreshold=-65"
```

What `nolly create` does automatically:
1. Resolves and clones the base preset (supports fuzzy name matching across `.\yml`).
2. Applies parameter changes. Supports **raw floats** (`0.72`), **scale notation** (`7.2/10`), **clock notation** (`2:30`), and **booleans** (`true`/`false`).
3. Saves both `.\User\<song>\XX - <name>.yml` AND `.\User\<song>\XX - <name>.xml`.
4. Re-reads and validates the generated JUCE binary XML.
5. Prints the full Markdown report: active gear, table with exact 0–10 scale and clock positions, and tailored SSS Stratocaster settings.

### Step 3: Present Result to User
Deliver the generated Markdown directly to the user.

---

## Python API Reference (`nolly` / `preset_editor`)

For custom scripting or complex programmatic tweaks, the Python module is importable from anywhere in the workspace with **zero `sys.path` boilerplate**:

```python
from nolly import NollyPreset, value_to_clock, clock_to_value, scale10_to_value

# Universal polymorphic loader (accepts .xml, .yml, .json, file path, bytes, or string)
preset = NollyPreset.load(r".\yml\Nolly\All-Purpose Metal Rhythm.yml")

# Explicit helpers also exist (no more from_yaml vs from_yaml_file confusion):
# preset = NollyPreset.from_yaml_file("path.yml")
# preset = NollyPreset.load_yaml("path.yml")
# preset = NollyPreset.load_xml("path.xml")

# Smart parameter updates with clock or 0-10 scale support:
preset.set_parameter("rhythmGain", "1:30")       # Converts ~1:30 to 0.65
preset.set_parameter("rhythmBass", "7.5/10")     # Converts 7.5/10 to 0.75
preset.set_parameter("gateActive", "true")

# Smart saver (detects .yml vs .xml from file extension):
preset.save(r".\User\Band - Song\00 - Tone.yml")
preset.save(r".\User\Band - Song\00 - Tone.xml")

# Get formatted markdown table & full report:
print(preset.format_knob_table())
print(preset.generate_tone_report(song="Band - Song", preset_num="00"))
```

---

## Legacy Conversion Scripts Reference

Backward-compatible standalone scripts:
- **XML a YML**:
  `.\xml2yml.cmd <archivo.xml> [archivo.yml]`
- **YML a XML**:
  `.\yml2xml.cmd <archivo.yml> <archivo.xml> [--name "<preset_name>"] [--report]`
  *(Use `--report` to output the knob scale & clock table upon generation)*

---

## UI Knobs & Values Representation (Archetype Nolly X)

- **No numeric text displays on pedals or amps**: Pedals and amp faceplates do NOT have numerical readouts or text input boxes. Only the top bar (Gate, Transpose, Doubler, Input/Output) and graphic EQ show numbers.
- **Double-click resets**: Double-clicking a knob RESETS it to its default value; it does NOT allow typing numbers.
- **Dots are decorative**: The dots around pedal and amp knobs are visual design elements; they do NOT correspond to a 0 to 10 scale (there are over 20 dots around each knob).
- **Fine Adjustment**: Holding `Ctrl` while dragging a knob enables precision/fine adjustment.
- **Mandatory format for knob recommendations**: Because agents must describe settings blindly without UI screenshots, ALWAYS give knob settings using **both approximate clock positions (horas del reloj) AND the 0 to 10 scale**:
  - **0 (Mínimo)** = **7:00** (totalmente girado a la izquierda / abajo)
  - **2.5** = **9:30** (~un cuarto)
  - **5.0 (Centro / Default)** = **12:00** (apuntando hacia arriba)
  - **7.5** = **2:30** (~tres cuartos)
  - **10 (Máximo)** = **5:00** (totalmente girado a la derecha / abajo)
  - Common intermediate references:
    - ~1.5 – 2.0 = 8:30 – 9:00
    - ~3.5 – 4.0 = 10:30 – 11:00
    - ~6.0 – 6.5 = 1:00 – 1:30
    - ~8.0 – 9.0 = 3:30 – 4:00
