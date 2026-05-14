from pathlib import Path
from PyQt6 import uic


ROOT = Path(__file__).resolve().parent
FILES = [
    (ROOT / "start_screen.ui", ROOT / "tavla_python" / "ui_start_screen.py"),
    (ROOT / "game_window.ui", ROOT / "tavla_python" / "ui_game_window.py"),
    (ROOT / "end_screen.ui", ROOT / "tavla_python" / "ui_end_screen.py"),
]

for ui_path, py_path in FILES:
    with py_path.open("w", encoding="utf-8") as fout:
        uic.compileUi(str(ui_path), fout)
    print(f"Olusturuldu: {py_path.relative_to(ROOT)}")
