from pathlib import Path
import runpy

runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "views" / "3_Sistem_Demosu.py"),
    run_name="__main__",
)
