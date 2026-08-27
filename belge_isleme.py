import io
from pathlib import Path

import pypdf
import pytesseract
from pdf2image import convert_from_bytes
DESTEKLENEN_PDF_UZANTILARI = {".pdf"}
MAKS_DOSYA_BOYUTU_MB = 15


def _normalize_metin(metin: str) -> str:
    return " ".join((metin or "").split())


def belge_turunu_tespit_et(dosya_adi: str, content_type: str | None) -> bool:
    uzanti = Path(dosya_adi or "").suffix.lower()
    if uzanti in DESTEKLENEN_PDF_UZANTILARI or content_type == "application/pdf":
        return True
    raise ValueError("Desteklenmeyen dosya türü. Yalnızca PDF dosyaları kabul edilir.")


def pdf_den_metin_cikar(dosya_baytlari: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(dosya_baytlari))
    metin = _normalize_metin("\n".join(page.extract_text() or "" for page in reader.pages))
    if len(metin) >= 20:
        return metin

    sayfalar = convert_from_bytes(dosya_baytlari)
    metin = _normalize_metin("\n".join(pytesseract.image_to_string(page, lang="tur") for page in sayfalar))
    if not metin:
        raise ValueError("PDF'den metin çıkarılamadı; belge boş veya okunamayacak durumda.")
    return metin


def belgeden_metin_cikar(dosya_baytlari: bytes, dosya_adi: str) -> str:
    belge_turunu_tespit_et(dosya_adi, None)
    return pdf_den_metin_cikar(dosya_baytlari)