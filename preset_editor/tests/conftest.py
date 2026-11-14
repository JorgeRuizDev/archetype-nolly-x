import sys
from pathlib import Path

# Automatically ensure workspace root and preset_editor are in sys.path
TEST_DIR = Path(__file__).resolve().parent
PRESET_EDITOR_DIR = TEST_DIR.parent
ROOT_DIR = PRESET_EDITOR_DIR.parent

for p in (str(ROOT_DIR), str(PRESET_EDITOR_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)
