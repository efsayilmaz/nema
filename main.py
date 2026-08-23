import argparse
import json
import sys
import unicodedata
from pathlib import Path

from gorev1 import calistir_gorev1
from gorev2 import calistir_gorev2


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
    parser = argparse.ArgumentParser(
        description="Kullanıcı metnini Görev 1 ve Görev 2 ile analiz eder."
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Analiz edilecek evrak dosyası. Verilmezse terminalden metin istenir.",
    )
    return parser.parse_args()


def calistir_pipeline(evrak_metni: str) -> None:
    """Ham evrak metnini Görev 1 ve Görev 2'den geçirerek nihai sonucu ekrana basar."""
    print("--- 1. AŞAMA: GÖREV 1 (EVRAK ANALİZİ) BAŞLATILIYOR ---")
    gorev1_sonuc = calistir_gorev1(evrak_metni)
    print("\n[Görev 1 Tamamlandı. Çıktı Şeması Başarıyla Oluşturuldu.]")
    print(json.dumps(gorev1_sonuc.model_dump(), ensure_ascii=False, indent=2))
    
    print("\n--- 2. AŞAMA: GÖREV 2 (YÖNLENDİRME VE TASLAK HAZIRLAMA) BAŞLATILIYOR ---")
    gorev2_sonuc = calistir_gorev2(gorev1_sonuc)
    print("\n[Görev 2 Tamamlandı. Nihai Karar ve Resmî Yazı Taslağı:]")
    print(json.dumps(gorev2_sonuc.model_dump(), ensure_ascii=False, indent=2))


def main() -> None:
    args = _argumanlari_oku()
    evrak_dosyasi = args.file
    evrak_metni = None

    if evrak_dosyasi:
        if not evrak_dosyasi.exists():
            raise FileNotFoundError(f"Evrak dosyasi bulunamadi: {evrak_dosyasi}")
        evrak_metni = _okuma_metni(evrak_dosyasi)
        print(f"İşlenen dosya: {evrak_dosyasi}")
    elif not sys.stdin.isatty():
        evrak_dosyasi = None
        evrak_metni = sys.stdin.read().strip()
        if not evrak_metni:
            print("Standart girdi boş veya bulunamadı. Örnek senaryo (dilekçe metni) çalıştırılıyor...\n")
            evrak_metni = ORNEK_DILEKCE
        else:
            print("İşlenen veri: Standart girdi (stdin)")
    else:
        evrak_metni = input("Evrak metnini girin: ").strip()
        if not evrak_metni:
            raise ValueError("Evrak metni boş bırakılamaz.")
        print("İşlenen veri: Kullanıcı girişi")

    calistir_pipeline(evrak_metni)


if __name__ == "__main__":
    main()
