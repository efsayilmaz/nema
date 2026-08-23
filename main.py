import argparse
import json
import sys
import unicodedata
from pathlib import Path

from gorev1 import calistir_gorev1


DESKTOP_KOK = Path.home() / "OneDrive" / "Desktop"
ADAYLAR = [
    "string.txt",
    "gorev1.txt",
    "görev1.txt",
    "gorev1.json",
    "görev1.json",
]


def _normalize_name(metin: str) -> str:
    metin = unicodedata.normalize("NFKD", metin.lower())
    return "".join(ch for ch in metin if not unicodedata.combining(ch))


def _bul_evrak_dosyasi() -> Path:
    for dosya_adi in ADAYLAR:
        yol = DESKTOP_KOK / dosya_adi
        if yol.exists():
            return yol

    for dosya in sorted(DESKTOP_KOK.iterdir()):
        if not dosya.is_file() or dosya.suffix.lower() not in {".txt", ".json"}:
            continue

        normalized = _normalize_name(dosya.name)
        if "string" in normalized or "gorev" in normalized or "gorev1" in normalized:
            return dosya

    raise FileNotFoundError(
        "Masaüstünde kullanılacak evrak dosyası bulunamadı. "
        f"Beklenen isimler: {ADAYLAR} | Aranan klasör: {DESKTOP_KOK}"
    )


def _okuma_metni(dosya: Path) -> str:
    if dosya.suffix.lower() == ".json":
        try:
            with dosya.open("r", encoding="utf-8") as fp:
                veri = json.load(fp)
            return json.dumps(veri, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            return dosya.read_text(encoding="utf-8")
    return dosya.read_text(encoding="utf-8")


def _argumanlari_oku() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tek bir evraki Gorev 1 ile analiz eder.")
    parser.add_argument(
        "--file",
        type=Path,
        help="Analiz edilecek evrak dosyasi. Verilmezse eski masaustu demo dosyasi kullanilir.",
    )
    return parser.parse_args()


def main() -> None:
    args = _argumanlari_oku()
    evrak_dosyasi = args.file

    if evrak_dosyasi:
        if not evrak_dosyasi.exists():
            raise FileNotFoundError(f"Evrak dosyasi bulunamadi: {evrak_dosyasi}")
        evrak_metni = _okuma_metni(evrak_dosyasi)
    elif not sys.stdin.isatty():
        evrak_dosyasi = None
        evrak_metni = sys.stdin.read()
    else:
        evrak_dosyasi = _bul_evrak_dosyasi()
        evrak_metni = _okuma_metni(evrak_dosyasi)

    sonuc = calistir_gorev1(evrak_metni)

    if evrak_dosyasi:
        print(f"Islenen dosya: {evrak_dosyasi}")
    print(json.dumps(
        sonuc.model_dump(),
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
