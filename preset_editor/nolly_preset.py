"""
Domain model and helper utilities for Archetype Nolly X presets.
Pure Python JUCE ValueTree parser, editor, and tone report generator.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from .juce_valuetree import JuceVar, ValueTreeNode, VarMarker, read_value_tree, write_value_tree
except (ImportError, ValueError):
    try:
        from juce_valuetree import JuceVar, ValueTreeNode, VarMarker, read_value_tree, write_value_tree
    except ImportError:
        from preset_editor.juce_valuetree import JuceVar, ValueTreeNode, VarMarker, read_value_tree, write_value_tree

AMP_NAMES = {
    0: "Clean (Amp 1)",
    1: "Crunch (Amp 2)",
    2: "Rhythm (Amp 3)",
    3: "Lead (Amp 4)",
}

CAB_NAMES = {
    0: "Cab 1",
    1: "Cab 2",
    2: "Cab 3",
    3: "Cab 4",
}


def value_to_clock(val_0_to_1: float) -> str:
    """
    Converts a normalized 0.0 - 1.0 knob value to an approximate clock face position.
    Scale:
      0.0  -> 7:00 (full counter-clockwise)
      0.25 -> 9:30 (~un cuarto)
      0.5  -> 12:00 (noon / center)
      0.75 -> 2:30 (~tres cuartos)
      1.0  -> 5:00 (full clockwise)
    Total rotation arc is 300 degrees (from 210 deg to 510/150 deg).
    """
    val = max(0.0, min(1.0, float(val_0_to_1)))
    # Hours from 7.0 to 17.0 (where 12 is 12:00, 13 is 1:00, 17 is 5:00)
    hour_val = 7.0 + val * 10.0
    hour = int(hour_val)
    minute = int(round((hour_val - hour) * 60 / 5) * 5)
    if minute == 60:
        hour += 1
        minute = 0
    display_hour = hour if hour <= 12 else hour - 12
    return f"{display_hour}:{minute:02d}"


def clock_to_value(clock_str: str) -> float:
    """
    Converts an approximate clock face position (e.g. '1:30', '12:00', '7:00', '~2:15')
    into a normalized 0.0 - 1.0 knob value.
    """
    s = clock_str.strip().lstrip("~").strip()
    if ":" not in s:
        raise ValueError(f"Invalid clock format: '{clock_str}'. Expected 'H:MM' (e.g. '12:00', '1:30').")
    parts = s.split(":")
    h = int(parts[0])
    m = int(parts[1])

    # Arc maps 7:00 -> 12:00 -> 5:00 (represented internally as 7..17)
    if 1 <= h <= 6:
        h += 12
    elif not (7 <= h <= 12):
        raise ValueError(f"Clock hour {parts[0]} is outside the potentiometer rotation range (7:00 to 5:00).")

    hour_val = h + (m / 60.0)
    val = (hour_val - 7.0) / 10.0
    return max(0.0, min(1.0, round(val, 6)))


def scale10_to_value(scale_val: Union[float, int, str]) -> float:
    """
    Converts a 0 to 10 scale value (e.g. 7.2, '7.2/10', '7.2s') into normalized 0.0 - 1.0.
    """
    s = str(scale_val).strip()
    if "/" in s:
        parts = s.split("/")
        val = float(parts[0]) / float(parts[1])
    else:
        s = s.rstrip("sS").strip()
        val = float(s) / 10.0
    return max(0.0, min(1.0, round(val, 6)))


def parse_numeric(val: Any) -> Optional[float]:
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def parse_bool(val: Any) -> Optional[bool]:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        low = val.lower().strip()
        if low in ("true", "1", "yes", "on"):
            return True
        if low in ("false", "0", "no", "off"):
            return False
    return None


def parse_param_value(val: Any) -> Any:
    """
    Smart value parser:
    - Bools ('true', 'false', 'on', 'off') -> 'true' / 'false'
    - Clock positions ('1:30', '12:00') -> normalized float string '0.65'
    - Scales ('7.2/10') -> normalized float string '0.72'
    - Numbers -> numeric string or number
    """
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return val

    s = str(val).strip()
    low = s.lower()
    if low in ("true", "yes", "on"):
        return "true"
    if low in ("false", "no", "off"):
        return "false"

    if "/" in s and s.endswith("/10"):
        return str(scale10_to_value(s))

    if ":" in s:
        try:
            return str(clock_to_value(s))
        except Exception:
            pass

    return s


class NollyPreset:
    """Represents an Archetype Nolly X preset with rich editing, conversion, and reporting capabilities."""

    def __init__(self, root: ValueTreeNode):
        self.root = root

    @classmethod
    def load(cls, target: Union[str, Path, bytes, Dict[str, Any]]) -> "NollyPreset":
        """
        Smart universal loader.
        Accepts:
        - Path or filename of .xml (JUCE binary), .yml/.yaml, or .json
        - Raw bytes (auto-detects JUCE binary vs UTF-8 YAML/JSON)
        - Dict representation of ValueTree
        - String content of YAML or JSON
        """
        if isinstance(target, dict):
            return cls.from_dict(target)

        if isinstance(target, bytes):
            # Check for JUCE binary first
            try:
                root = read_value_tree(target)
                if root is not None and root.tag == "nolly-x":
                    return cls(root)
            except Exception:
                pass
            # Try text YAML/JSON
            try:
                text = target.decode("utf-8")
                return cls.from_yaml(text)
            except Exception as e:
                raise ValueError(f"Could not parse binary or text preset: {e}")

        # target is Path or str
        p = Path(target)
        if p.exists() and p.is_file():
            ext = p.suffix.lower()
            if ext in (".yml", ".yaml"):
                return cls.from_yaml_file(p)
            elif ext == ".json":
                return cls.from_json_file(p)
            elif ext == ".xml":
                return cls.load_xml(p)
            else:
                # Try reading bytes and auto-detecting
                data = p.read_bytes()
                try:
                    root = read_value_tree(data)
                    if root is not None and root.tag == "nolly-x":
                        return cls(root)
                except Exception:
                    pass
                return cls.from_yaml(data.decode("utf-8"))

        # String that might be YAML/JSON content
        s = str(target).strip()
        if "\n" in s or "properties:" in s or "tag:" in s or (s.startswith("{") and s.endswith("}")):
            return cls.from_yaml(s)

        raise FileNotFoundError(f"Preset file not found: {target}")

    @classmethod
    def load_xml(cls, path_or_bytes: Union[str, Path, bytes]) -> "NollyPreset":
        """Loads a preset from JUCE XML binary format."""
        if isinstance(path_or_bytes, (str, Path)):
            data = Path(path_or_bytes).read_bytes()
        else:
            data = path_or_bytes

        root = read_value_tree(data)
        if root is None or root.tag != "nolly-x":
            raise ValueError("Invalid or corrupted Archetype Nolly X preset XML.")
        return cls(root)

    @classmethod
    def load_yaml(cls, path_or_str: Union[str, Path]) -> "NollyPreset":
        """Loads a preset from a YAML file or YAML string."""
        return cls.from_yaml(path_or_str)

    @classmethod
    def from_yaml_file(cls, path: Union[str, Path]) -> "NollyPreset":
        """Loads a preset directly from a YAML file path."""
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"YAML preset file not found: {path}")
        return cls.from_yaml(p.read_text(encoding="utf-8"))

    @classmethod
    def from_yaml(cls, yaml_str_or_dict_or_path: Union[str, Path, Dict[str, Any]]) -> "NollyPreset":
        """Imports a preset from YAML (string, dict, or file path)."""
        import yaml
        if isinstance(yaml_str_or_dict_or_path, dict):
            return cls.from_dict(yaml_str_or_dict_or_path)

        if isinstance(yaml_str_or_dict_or_path, Path) or (
            isinstance(yaml_str_or_dict_or_path, str)
            and "\n" not in yaml_str_or_dict_or_path
            and Path(yaml_str_or_dict_or_path).is_file()
        ):
            content = Path(yaml_str_or_dict_or_path).read_text(encoding="utf-8")
            d = yaml.safe_load(content)
            return cls.from_dict(d)

        d = yaml.safe_load(str(yaml_str_or_dict_or_path))
        if not isinstance(d, dict):
            raise ValueError(f"YAML content did not parse into a dictionary: {d}")
        return cls.from_dict(d)

    @classmethod
    def from_json_file(cls, path: Union[str, Path]) -> "NollyPreset":
        """Loads a preset directly from a JSON file path."""
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"JSON preset file not found: {path}")
        return cls.from_json(p.read_text(encoding="utf-8"))

    @classmethod
    def from_json(cls, json_str_or_dict: Union[str, Dict[str, Any]]) -> "NollyPreset":
        """Imports a preset from JSON."""
        d = json.loads(json_str_or_dict) if isinstance(json_str_or_dict, str) else json_str_or_dict
        return cls.from_dict(d)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NollyPreset":
        """Imports a preset from a ValueTree dictionary."""
        root = ValueTreeNode.from_dict(data)
        return cls(root)

    def clone(self) -> "NollyPreset":
        """Creates a deep copy of the preset."""
        return NollyPreset.from_dict(self.root.to_dict())

    def save(self, path: Union[str, Path]) -> None:
        """
        Smart saver:
        - If path ends with .yml or .yaml -> saves as YAML
        - If path ends with .json -> saves as JSON
        - Otherwise (default .xml) -> saves as JUCE binary XML
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        ext = p.suffix.lower()
        if ext in (".yml", ".yaml"):
            self.save_yaml(p)
        elif ext == ".json":
            self.save_json(p)
        else:
            self.save_xml(p)

    def save_xml(self, path: Union[str, Path]) -> None:
        """Saves preset as JUCE ValueTree binary XML."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = self.to_bytes()
        p.write_bytes(data)

    def save_yaml(self, path: Union[str, Path]) -> None:
        """Saves preset as clean YAML."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_yaml(), encoding="utf-8")

    def save_json(self, path: Union[str, Path], indent: int = 2) -> None:
        """Saves preset as JSON."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json(indent=indent), encoding="utf-8")

    def to_bytes(self) -> bytes:
        """Serializes preset back to exact JUCE ValueTree binary bytes."""
        return write_value_tree(self.root)

    def to_yaml(self) -> str:
        """Exports the full ValueTree representation to YAML."""
        import yaml
        return yaml.dump(self.root.to_dict(), sort_keys=False, allow_unicode=True)

    def to_json(self, indent: int = 2) -> str:
        """Exports the full ValueTree representation to JSON."""
        return json.dumps(self.root.to_dict(), indent=indent)

    # --- Top-level Metadata Properties ---

    @property
    def name(self) -> str:
        return str(self.root.get_property("name", ""))

    @name.setter
    def name(self, val: str) -> None:
        self.root.set_property("name", str(val), marker=VarMarker.STRING)

    @property
    def version(self) -> str:
        return str(self.root.get_property("version", "1.0.0"))

    @version.setter
    def version(self, val: str) -> None:
        self.root.set_property("version", str(val), marker=VarMarker.STRING)

    @property
    def is_favorite(self) -> bool:
        return bool(self.root.get_property("isFavorite", False))

    @is_favorite.setter
    def is_favorite(self, val: bool) -> None:
        self.root.set_property("isFavorite", bool(val))

    # --- High-level Model Properties ---

    def _get_app_model(self) -> Optional[ValueTreeNode]:
        return self.root.find_child("appModel")

    @property
    def selected_amp_id(self) -> int:
        app = self._get_app_model()
        if app is None:
            return 0
        raw = app.get_property("selectedAmp", "0")
        try:
            return int(raw)
        except ValueError:
            return 0

    @selected_amp_id.setter
    def selected_amp_id(self, val: int) -> None:
        app = self._get_app_model()
        if app is not None:
            app.set_property("selectedAmp", str(val), marker=VarMarker.STRING)

    @property
    def selected_amp_name(self) -> str:
        return AMP_NAMES.get(self.selected_amp_id, f"Amp {self.selected_amp_id}")

    @property
    def selected_cab_id(self) -> int:
        app = self._get_app_model()
        if app is None:
            return 0
        raw = app.get_property("selectedCab", "0")
        try:
            return int(raw)
        except ValueError:
            return 0

    @selected_cab_id.setter
    def selected_cab_id(self, val: int) -> None:
        app = self._get_app_model()
        if app is not None:
            app.set_property("selectedCab", str(val), marker=VarMarker.STRING)

    @property
    def selected_cab_name(self) -> str:
        return CAB_NAMES.get(self.selected_cab_id, f"Cab {self.selected_cab_id}")

    # --- Recursive Parameter Lookup & Modification ---

    def find_property_node(self, name: str) -> Optional[Tuple[ValueTreeNode, JuceVar]]:
        """Finds the node containing the given property name."""
        name_lower = name.lower()

        def _search(node: ValueTreeNode) -> Optional[Tuple[ValueTreeNode, JuceVar]]:
            for k, v in node.properties:
                if k.lower() == name_lower and v is not None:
                    return (node, v)
            for c in node.children:
                res = _search(c)
                if res is not None:
                    return res
            return None

        return _search(self.root)

    def get_parameter(self, name: str, default: Any = None) -> Any:
        """Retrieves a parameter's raw value by name."""
        if name.lower() in ("name", "presetname", "preset_name"):
            return self.name
        found = self.find_property_node(name)
        if found is None:
            return default
        _, var = found
        return var.value

    def set_parameter(self, name: str, value: Any, auto_convert: bool = True) -> bool:
        """
        Updates a parameter's value anywhere in the preset tree.
        Supports:
        - Parameter name aliases (e.g. 'name')
        - Clock strings ('1:30' -> '0.65')
        - Scale strings ('7.2/10' -> '0.72')
        - Boolean strings ('true', 'false')
        """
        if name.lower() in ("name", "presetname", "preset_name"):
            self.name = str(value)
            return True

        val = parse_param_value(value) if auto_convert else value
        found = self.find_property_node(name)
        if found is None:
            return False

        node, existing_var = found
        actual_name = name
        for k, _ in node.properties:
            if k.lower() == name.lower():
                actual_name = k
                break

        node.set_property(actual_name, val)
        return True

    def set_parameters(self, assignments: Union[Dict[str, Any], List[str]]) -> int:
        """
        Applies multiple parameter updates from a dict or list of 'param=value' pairs.
        Returns the count of successfully updated parameters.
        """
        modified = 0
        if isinstance(assignments, dict):
            items = assignments.items()
        else:
            items = []
            for item in assignments:
                if "=" in item:
                    k, v = item.split("=", 1)
                    items.append((k.strip(), v.strip()))

        for k, v in items:
            if self.set_parameter(k, v):
                modified += 1
        return modified

    def get_all_parameters(self) -> Dict[str, Any]:
        """Returns a flat dictionary of all parameter names and values."""
        res: Dict[str, Any] = {}

        def _collect(node: ValueTreeNode):
            for k, v in node.properties:
                if v is not None:
                    res[k] = v.value
            for c in node.children:
                _collect(c)

        _collect(self.root)
        return res

    def list_sections(self) -> Dict[str, Dict[str, Any]]:
        """Categorizes all parameters into logical sections."""
        params = self.get_all_parameters()

        sections = {
            "Metadata": {k: params[k] for k in ["name", "version", "isFavorite"] if k in params},
            "Global": {k: params[k] for k in ["selectedAmp", "selectedCab", "ampCabLinkedState", "inputGain", "outputGain", "gateActive", "gateThreshold", "doublerActive", "doublerSpread", "transpose"] if k in params},
            "Pre FX - Compressor": {k: params[k] for k in params if k.startswith("compressor")},
            "Pre FX - Overdrive 1": {k: params[k] for k in params if k.startswith("overdrive1")},
            "Pre FX - Overdrive 2": {k: params[k] for k in params if k.startswith("overdrive2")},
            "Pre FX - Pre Delay": {k: params[k] for k in params if k.startswith("preDelay")},
            "Amp - Clean": {k: params[k] for k in params if k.startswith("clean") and not k.startswith("cleanEQ")},
            "Amp - Crunch": {k: params[k] for k in params if k.startswith("crunch") and not k.startswith("crunchEQ")},
            "Amp - Rhythm": {k: params[k] for k in params if k.startswith("rhythm") and not k.startswith("rhythmEQ")},
            "Amp - Lead": {k: params[k] for k in params if k.startswith("lead") and not k.startswith("leadEQ")},
            "EQ - Clean": {k: params[k] for k in params if k.startswith("cleanEQ")},
            "EQ - Crunch": {k: params[k] for k in params if k.startswith("crunchEQ")},
            "EQ - Rhythm": {k: params[k] for k in params if k.startswith("rhythmEQ")},
            "EQ - Lead": {k: params[k] for k in params if k.startswith("leadEQ")},
            "Post FX - Delay": {k: params[k] for k in params if k.startswith("postDelay")},
            "Post FX - Reverb": {k: params[k] for k in params if k.startswith("reverb")},
            "Cabinet & Mics": {k: params[k] for k in params if "Cab" in k or "Room" in k},
        }
        return {k: v for k, v in sections.items() if v}

    def summary(self) -> Dict[str, Any]:
        """Returns a high-level summary of the active gear and configuration."""
        def is_on(key: str) -> bool:
            return bool(parse_bool(self.get_parameter(key, False)))

        return {
            "name": self.name,
            "version": self.version,
            "is_favorite": self.is_favorite,
            "selected_amp": self.selected_amp_name,
            "selected_amp_id": self.selected_amp_id,
            "selected_cab": CAB_NAMES.get(self.selected_cab_id, f"Cab {self.selected_cab_id}"),
            "selected_cab_id": self.selected_cab_id,
            "gate_active": is_on("gateActive"),
            "gate_threshold": self.get_parameter("gateThreshold", "-80"),
            "doubler_active": is_on("doublerActive"),
            "doubler_spread": self.get_parameter("doublerSpread", "6"),
            "transpose": self.get_parameter("transpose", "0"),
            "compressor_active": is_on("compressorActive"),
            "overdrive1_active": is_on("overdrive1Active"),
            "overdrive2_active": is_on("overdrive2Active"),
            "pre_delay_active": is_on("preDelayActive"),
            "post_delay_active": is_on("postDelayActive"),
            "reverb_active": is_on("reverbActive"),
        }

    def get_active_controls(self) -> List[Dict[str, Any]]:
        """
        Returns structured control info (section, param, raw value, 0-10 scale, clock position)
        for all active gear in this preset.
        """
        controls: List[Dict[str, Any]] = []
        summ = self.summary()
        amp_id = summ["selected_amp_id"]

        # Amp controls definitions
        amp_controls_map = {
            0: ("Amp 1 (Clean)", [
                ("cleanGain", "Gain"),
                ("cleanBass", "Bass"),
                ("cleanMid", "Mid"),
                ("cleanTreble", "Treble"),
                ("cleanMaster", "Master"),
                ("cleanOutput", "Output Level"),
                ("cleanBright", "Bright Switch"),
            ]),
            1: ("Amp 2 (Crunch)", [
                ("crunchGain", "Gain"),
                ("crunchBass", "Bass"),
                ("crunchMid", "Mid"),
                ("crunchTreble", "Treble"),
                ("crunchPresence", "Presence"),
                ("crunchDepth", "Depth"),
                ("crunchMaster", "Master"),
                ("crunchOutput", "Output Level"),
                ("crunchBright", "Bright Switch"),
            ]),
            2: ("Amp 3 (Rhythm)", [
                ("rhythmGain", "Gain"),
                ("rhythmBass", "Bass"),
                ("rhythmMid", "Mid"),
                ("rhythmTreble", "Treble"),
                ("rhythmPresence", "Presence"),
                ("rhythmResonance", "Resonance"),
                ("rhythmMaster", "Master"),
                ("rhythmOutput", "Output Level"),
            ]),
            3: ("Amp 4 (Lead)", [
                ("leadGain", "Gain"),
                ("leadBass", "Bass"),
                ("leadMid", "Mid"),
                ("leadTreble", "Treble"),
                ("leadMaster", "Master"),
                ("leadOutput", "Output Level"),
            ]),
        }

        # 1. Amp controls
        amp_title, amp_params = amp_controls_map.get(amp_id, ("Amp", []))
        for p_key, p_label in amp_params:
            val = self.get_parameter(p_key)
            if val is not None:
                controls.append(self._make_control_dict(amp_title, p_label, p_key, val))

        # 2. Overdrive 1
        if summ["overdrive1_active"]:
            for p_key, p_label in [
                ("overdrive1Drive", "Drive"),
                ("overdrive1Tone", "Tone"),
                ("overdrive1Level", "Level"),
                ("overdrive1Bright", "Bright"),
            ]:
                val = self.get_parameter(p_key)
                if val is not None:
                    controls.append(self._make_control_dict("Overdrive 1", p_label, p_key, val))

        # 3. Overdrive 2
        if summ["overdrive2_active"]:
            for p_key, p_label in [
                ("overdrive2Gain", "Gain"),
                ("overdrive2Bass", "Bass"),
                ("overdrive2Treble", "Treble"),
                ("overdrive2Level", "Level"),
            ]:
                val = self.get_parameter(p_key)
                if val is not None:
                    controls.append(self._make_control_dict("Overdrive 2", p_label, p_key, val))

        # 4. Compressor
        if summ["compressor_active"]:
            for p_key, p_label in [
                ("compressorCompression", "Compression"),
                ("compressorLevel", "Level"),
                ("compressorAttack", "Fast Attack"),
            ]:
                val = self.get_parameter(p_key)
                if val is not None:
                    controls.append(self._make_control_dict("Compressor", p_label, p_key, val))

        # 5. Pre Delay
        if summ["pre_delay_active"]:
            for p_key, p_label in [
                ("preDelayMix", "Mix"),
                ("preDelayFeedback", "Feedback"),
                ("preDelayTone", "Tone"),
                ("preDelayTime", "Time (ms)"),
            ]:
                val = self.get_parameter(p_key)
                if val is not None:
                    controls.append(self._make_control_dict("Pre Delay", p_label, p_key, val))

        # 6. Post Delay
        if summ["post_delay_active"]:
            for p_key, p_label in [
                ("postDelayMix", "Mix"),
                ("postDelayFeedback", "Feedback"),
                ("postDelayTime", "Time (ms)"),
            ]:
                val = self.get_parameter(p_key)
                if val is not None:
                    controls.append(self._make_control_dict("Post Delay", p_label, p_key, val))

        # 7. Post Reverb
        if summ["reverb_active"]:
            for p_key, p_label in [
                ("reverbMix", "Mix"),
                ("reverbDecay", "Decay (ms)"),
            ]:
                val = self.get_parameter(p_key)
                if val is not None:
                    controls.append(self._make_control_dict("Reverb", p_label, p_key, val))

        # 8. Global (Gate, Transpose)
        controls.append({
            "section": "Global",
            "label": "Noise Gate",
            "param": "gateThreshold",
            "raw": self.get_parameter("gateThreshold", "-80"),
            "scale_10": None,
            "clock": None,
            "display": f"{'ON' if summ['gate_active'] else 'OFF'} ({self.get_parameter('gateThreshold')} dB)",
        })
        if str(summ["transpose"]) != "0":
            controls.append({
                "section": "Global",
                "label": "Transposer",
                "param": "transpose",
                "raw": summ["transpose"],
                "scale_10": None,
                "clock": None,
                "display": f"{summ['transpose']} semitonos",
            })

        return controls

    def _make_control_dict(self, section: str, label: str, param: str, val: Any) -> Dict[str, Any]:
        num = parse_numeric(val)
        
        # Check if parameter is explicitly a boolean switch
        is_bool_param = param.lower().endswith(("active", "bright", "attack", "stereo", "phase", "sync", "pingpong"))
        b = parse_bool(val)

        if (isinstance(val, bool) or str(val).lower() in ("true", "false") or is_bool_param) and b is not None:
            return {
                "section": section,
                "label": label,
                "param": param,
                "raw": val,
                "scale_10": None,
                "clock": None,
                "display": "ON" if b else "OFF",
            }

        if num is not None and 0.0 <= num <= 1.0:
            scale_10 = round(num * 10.0, 1)
            clock = value_to_clock(num)
            return {
                "section": section,
                "label": label,
                "param": param,
                "raw": round(num, 4),
                "scale_10": scale_10,
                "clock": clock,
                "display": f"{scale_10:.1f} / 10 (~{clock})",
            }

        return {
            "section": section,
            "label": label,
            "param": param,
            "raw": val,
            "scale_10": None,
            "clock": None,
            "display": str(val),
        }

    def format_knob_table(self, active_only: bool = True) -> str:
        """
        Generates a markdown table displaying parameter settings with both
        the 0-10 scale and clock face representations.
        """
        controls = self.get_active_controls() if active_only else []
        if not controls:
            return "_No active controls found._"

        lines = [
            "| Sección / Pedal | Control | Parámetro | Escala (0–10) | Posición Reloj | Valor Raw |",
            "| :--- | :--- | :--- | :---: | :---: | :---: |",
        ]

        for c in controls:
            sec = f"**{c['section']}**"
            lbl = c["label"]
            prm = f"`{c['param']}`"
            sc = f"**{c['scale_10']:.1f}** / 10" if c["scale_10"] is not None else "-"
            ck = f"~**{c['clock']}**" if c["clock"] is not None else "-"
            raw = f"`{c['raw']}`" if c["scale_10"] is not None else f"{c['display']}"
            lines.append(f"| {sec} | {lbl} | {prm} | {sc} | {ck} | {raw} |")

        return "\n".join(lines)

    def get_guitar_recommendations(self, guitar_type: str = "Squier Stratocaster SSS") -> Dict[str, str]:
        """
        Provides tailored guitar recommendations for a Squier Stratocaster SSS
        plugged into Focusrite Scarlett Solo 2.
        """
        summ = self.summary()
        amp_id = summ["selected_amp_id"]

        if amp_id == 0:  # Clean
            pos = "Posición 4 (Mástil + Media) o Posición 5 (Mástil)"
            tone = "9 – 10 (Abierto, tono cristalino 'glassy')"
            vol = "8 – 10"
            tips = "Pastillas intermedias cancelan zumbido (hum-cancelling) y dan el clásico 'cluck' de Stratocaster."
        elif amp_id == 1:  # Crunch
            pos = "Posición 5 (Mástil) para calidez bluesy o Posición 2 (Puente + Media) para corte rítmico"
            tone = "7 – 8 (Suavizar el brillo agudo sin perder definición)"
            vol = "7 – 9 (Limpia dinámicamente con la púa)"
            tips = "Usa el potenciómetro de volumen de la guitarra para pasar de clean dinámico a crunch crujiente."
        elif amp_id == 2:  # Rhythm (High Gain)
            pos = "Posición 1 (Pastilla de Puente)"
            tone = "7 – 8 (Recorta el 'hiss' agudo punzante de las single-coils)"
            vol = "10 (Máxima salida para excitar la distorsión del ampli)"
            tips = "La pastilla de puente SSS es brillante; asegúrate de que el Noise Gate esté activo (threshold ~ -60 a -70 dB) para silenciar el zumbido de 50/60 Hz."
        else:  # Lead
            pos = "Posición 5 (Mástil) para solos fluidos y cremosos, o Posición 1 (Puente) para solos cortantes"
            tone = "7 – 9"
            vol = "10 (Sustain máximo)"
            tips = "La pastilla de mástil en solo da el clásico tono 'vocal' y redondeado con delay/reverb."

        trans = int(summ["transpose"])
        tuning_note = "Afinación estándar (E Standard)"
        if trans < 0:
            tuning_note = f"Guitarra afinada en E Standard / Drop D con Transposer a {trans} semitonos en el preset"

        return {
            "pickup": pos,
            "volume": vol,
            "tone": tone,
            "tuning": tuning_note,
            "interface": "Focusrite Scarlett Solo (Gain knob ~ 9:00 - 10:00, botón INST activo, LED verde)",
            "tips": tips,
        }

    def generate_tone_report(
        self,
        song: str = "",
        preset_num: str = "",
        base_preset: str = "",
    ) -> str:
        """
        Generates a comprehensive Markdown report of the preset including gear summary,
        knob table (scale 0-10 & clock), and SSS Stratocaster setup.
        """
        summ = self.summary()
        g_recs = self.get_guitar_recommendations()

        title_line = f"### 🎸 Preset: {self.name}"
        if song:
            title_line = f"### 🎸 {song} — Preset {preset_num or ''}: {self.name}"

        # Active pedals list
        active_fx = []
        if summ["gate_active"]:
            active_fx.append(f"Noise Gate ({summ['gate_threshold']} dB)")
        if summ["compressor_active"]:
            active_fx.append("Compressor")
        if summ["overdrive1_active"]:
            active_fx.append("Overdrive 1")
        if summ["overdrive2_active"]:
            active_fx.append("Overdrive 2")
        if summ["pre_delay_active"]:
            active_fx.append("Pre Delay")
        if summ["post_delay_active"]:
            active_fx.append("Post Delay")
        if summ["reverb_active"]:
            active_fx.append("Reverb")
        if summ["doubler_active"]:
            active_fx.append("Doubler")

        fx_str = ", ".join(active_fx) if active_fx else "Ninguno (Ampli directo)"

        report = f"""{title_line}

- **Amplificador Activo**: {summ['selected_amp']}
- **Pantalla (Cab)**: {summ['selected_cab']}
- **Efectos y Pedales Activos**: {fx_str}
{f"- **Preset Base**: `{base_preset}`" if base_preset else ""}

#### 🎛️ Ajustes de Potenciómetros (Escala 0–10 y Posición Horaria)

{self.format_knob_table(active_only=True)}

#### 🎸 Configuración Sugerida de Guitarra (Squier Stratocaster SSS)

- **Selector de Pastillas**: {g_recs['pickup']}
- **Volumen de la Guitarra**: {g_recs['volume']}
- **Tono de la Guitarra**: {g_recs['tone']}
- **Afinación / Transposer**: {g_recs['tuning']}
- **Interfaz (Scarlett Solo)**: {g_recs['interface']}
- **Consejo de Tono**: {g_recs['tips']}
"""
        return report.strip()

    def diff(self, other: "NollyPreset") -> Dict[str, Tuple[Any, Any]]:
        """Compares this preset with another, returning a dict of differences."""
        p1 = self.get_all_parameters()
        p2 = other.get_all_parameters()
        diffs = {}
        all_keys = sorted(set(p1.keys()) | set(p2.keys()))
        for k in all_keys:
            v1 = p1.get(k)
            v2 = p2.get(k)
            if v1 != v2:
                diffs[k] = (v1, v2)
        return diffs
