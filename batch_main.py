import argparse
import json
import re
from pathlib import Path

from gorev1 import calistir_gorev1
from gorev2 import calistir_gorev2
from main import _bul_evrak_dosyasi, _okuma_metni


QUOTED_DOCUMENT_RE = re.compile(r'(?ms)^\s*"\s*(.*?)\s*"\s*$')


def _metinleri_ayir(metin: str) -> list[str]:
    """Dataset icindeki tirnakli ve etiketsiz belgeleri ayri metinlere ayirir."""
    belgeler = [match.group(1).strip() for match in QUOTED_DOCUMENT_RE.finditer(metin)]
    tirnaksiz = QUOTED_DOCUMENT_RE.sub("\n\n", metin).strip()

    if tirnaksiz:
        baslikli_parcalar = re.split(r"(?im)^\s*String\s+\d+\s*:\s*", tirnaksiz)
        if len(baslikli_parcalar) > 1:
            belgeler.extend(parca.strip() for parca in baslikli_parcalar if parca.strip())
        else:
            belgeler.extend(parca.strip() for parca in re.split(r"\n\s*\n\s*\n", tirnaksiz) if parca.strip())

    return belgeler


def main() -> None:
    parser = argparse.ArgumentParser(description="Gorev 1 ve Gorev 2 dataset calistiricisi")
    parser.add_argument("--dosya", type=Path, help="Analiz edilecek dataset dosyasi")
    args = parser.parse_args()

    dosya = args.dosya or _bul_evrak_dosyasi()
    metinler = _metinleri_ayir(_okuma_metni(dosya))
    if not metinler:
        raise ValueError(f"Dosyada ayristirilabilir evrak bulunamadi: {dosya}")

    sonuclar = []
    for sira, evrak in enumerate(metinler, start=1):
        gorev1_sonucu = calistir_gorev1(evrak)
        gorev2_sonucu = calistir_gorev2(gorev1_sonucu)
        sonuclar.append({
            "evrak_sirasi": sira,
            "gorev1_ciktisi": gorev1_sonucu.model_dump(),
            "gorev2_ciktisi": gorev2_sonucu.model_dump(),
        })
        print(f"Tamamlandi: {sira}/{len(metinler)} (Gorev 1 + Gorev 2)")

    cikti = dosya.with_name(f"{dosya.stem}_gorev1_gorev2_sonuclari.json")
    cikti.write_text(json.dumps(sonuclar, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(sonuclar)} evrak ayrica analiz edildi: {cikti}")


if __name__ == "__main__":
    main()
