"""
Archetype Nolly X Preset Editor
Pure Python JUCE ValueTree parser & preset manager.
"""

from .juce_valuetree import (
    JuceInputStream,
    JuceOutputStream,
    JuceVar,
    ValueTreeNode,
    VarMarker,
    read_value_tree,
    write_value_tree,
)
from .nolly_preset import (
    NollyPreset,
    clock_to_value,
    parse_param_value,
    scale10_to_value,
    value_to_clock,
)

__all__ = [
    "JuceInputStream",
    "JuceOutputStream",
    "JuceVar",
    "ValueTreeNode",
    "VarMarker",
    "read_value_tree",
    "write_value_tree",
    "NollyPreset",
    "value_to_clock",
    "clock_to_value",
    "scale10_to_value",
    "parse_param_value",
]
