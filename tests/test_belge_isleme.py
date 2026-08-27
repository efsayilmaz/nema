import io
from unittest.mock import patch

import pytest

from belge_isleme import (
    belge_turunu_tespit_et,
    belgeden_metin_cikar,
)


def test_belge_turu_pdf_tespit_eder():
    assert belge_turunu_tespit_et("dilekce.pdf", "application/pdf") is True


def test_fotograf_desteklenmez():
    with pytest.raises(ValueError, match="Yalnızca PDF"):
        belgeden_metin_cikar(b"foto", "belge.jpg")


def test_belgeden_metin_cikar_pdf_metin_akisini_korur():
    from pypdf import PdfWriter

    pdf_buffer = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.write(pdf_buffer)

    with patch("belge_isleme.pypdf.PdfReader") as reader:
        pdf_text = "PDF belge metni ve yeterli uzunlukta içerik"
        reader.return_value.pages = [type("Page", (), {"extract_text": lambda self: pdf_text})()]
        assert belgeden_metin_cikar(pdf_buffer.getvalue(), "belge.pdf") == pdf_text


def test_desteklenmeyen_dosya_turu_anlasilir_hata_verir():
    with pytest.raises(ValueError, match="Yalnızca PDF"):
        belgeden_metin_cikar(b"metin", "belge.txt")


