from pathlib import Path
import runpy

runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "views" / "1_Evrak_Analizi.py"),
    run_name="__main__",
)
