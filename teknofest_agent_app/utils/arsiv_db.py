import json
import os
from pathlib import Path

DB_FILE = Path(os.path.dirname(os.path.abspath(__file__))) / ".." / "arsiv_verileri.json"

def arsiv_verilerini_getir():
    if not DB_FILE.exists():
        return []
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def arsive_ekle(kayit_dict):
    veriler = arsiv_verilerini_getir()
    veriler.append(kayit_dict)
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(veriler, f, ensure_ascii=False, indent=4)
