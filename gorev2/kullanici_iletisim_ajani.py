import json
import os
import re
import time
from typing import Dict, Any, Union, Optional

from evren_client import get_evren_client, validate_response_content
from pydantic import BaseModel, Field

from gorev2.schemas import (
    KullaniciBilgilendirme,
    ResmiYaziTaslagi,
    Gorev1CiktiSemasi,
    AksiyonDurumu,
    YonlendirmeKarari
)

KULLANICI_ILETISIM_PROMPT = """
Sen kamu kurumlarında görev yapan, vatandaş ve başvuru sahipleriyle resmi iletişimi yöneten kıdemli bir yapay zeka iletişim ajanısın.
Sana Görev 1 aşamasında analiz edilmiş, özeti, özellikleri ve varsa eksik bilgileri çıkarılmış bir evrak verisi (JSON formatında) sunulacaktır.

GÖREVİN:
Verilen evrak analizini inceleyerek aşağıdaki iki bileşenden oluşan çıktıyı üretmektir:

1. KULLANICI BİLGİLENDİRME (`kullanici_bilgilendirme`):
   - `kullaniciya_gosterilecek_mesaj`: Başvuru sahibine sürecin durumunu açıklayan anlaşılır, nazik ve bilgilendirici bir Türkçe mesaj.
   - `sistem_aksiyon_durumu`:
     * Evrakta herhangi bir eksik bilgi/belge VARSA (örn: `eksik_bilgiler` listesi doluysa veya analizde eksiklik tespit edildiyse): Kesinlikle "Kullanıcı Bekleniyor" olmalıdır.
     * Evrak eksiksiz ve işlem tamamsa: "İşleme Alındı" veya "Onay Bekliyor" (belgenin durumuna veya aciliyetine göre uygun olanı seçin).

2. RESMÎ YAZI TASLAĞI (`resmi_yazi_taslagi`) - YALNIZCA eksik bilgi/belge olması durumunda doldurulacaktır:
   - `yazi_turu`: Kesinlikle "Eksik Bilgi/Belge Talebi" olmalıdır.
   - `konu`: Eksik bilgi/belge talebi konusu (örn: "Eksik Bilgi ve Belge Talebi Hk.").
   - `ilgi`: Başvuru dilekçesine referans veren resmî ilgi tutma cümlesi (örn: "14.11.2025 tarihli dilekçe.").
   - `govde_metni`: Başvuru sahibine yönelik, hangi bilgi/belgelerin eksik olduğunu tek tek belirten resmi talep yazısı metni. Başlık, İlgi, Arz/Rica, İmza GİBİ ŞABLONLARI kesinlikle EKLEMEYİN. Sadece asıl paragrafı yazın.
   - `imza_makami`: Yazıyı imzalayacak/onaylayacak yetkili makam unvanı (örn: Birim Amiri, Zabıta Müdürü, Dekan Yardımcısı vb.).

Eğer eksik bilgi/belge YOKSA, `resmi_yazi_taslagi` alanını null/None olarak döndürün.

ZORUNLU RESMÎ YAZI METNİ ÜRETİM KURALLARI (ASLA İHLAL EDİLEMEZ):
- Eksik bilgi/belge durumunda üretilecek gövde metninde yer tutucu (placeholder) "[...]" kullanmayın. Tespit edilen gerçek eksiklikleri net bir şekilde yazın.
- Arz/rica ifadesi olarak vatandaşa yazıldığı için kesinlikle "Gereğini rica ederim." seçilmelidir. Alternatifli/eğik çizgili yazmayın.
- Türkçe büyük harf kuralına ve İ/I uyumuna dikkat edin.

YALNIZCA geçerli bir JSON döndür. Markdown, açıklama veya düşünme metni yazma.
"""


class KullaniciIletisimCiktisi(BaseModel):
    """Kullanıcı İletişim Ajanı çıktı şeması."""
    kullanici_bilgilendirme: KullaniciBilgilendirme = Field(
        ...,
        description="Kullanıcı bilgilendirme ve sistem aksiyon durumu"
    )
    resmi_yazi_taslagi: Optional[ResmiYaziTaslagi] = Field(
        default=None,
        description="Hazırlanan resmî yazı taslağı (sadece eksik bilgi durumunda doludur)"
    )


def _normalize_input(girdi_verisi: Union[dict, str, BaseModel, Gorev1CiktiSemasi]) -> str:
    """Görev 1 girdisini JSON string formatına dönüştürür."""
    if isinstance(girdi_verisi, BaseModel) or hasattr(girdi_verisi, "model_dump_json"):
        return girdi_verisi.model_dump_json(indent=2, exclude_none=False)
    elif isinstance(girdi_verisi, dict):
        return json.dumps(girdi_verisi, ensure_ascii=False, indent=2)
    elif isinstance(girdi_verisi, str):
        try:
            parsed = json.loads(girdi_verisi)
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            return girdi_verisi
    else:
        return str(girdi_verisi)


def calistir_kullanici_iletisim_ajani(
    client,
    model: str,
    girdi_verisi: Union[dict, str, BaseModel, Gorev1CiktiSemasi],
    yonlendirme_karari: Optional[YonlendirmeKarari] = None
) -> KullaniciIletisimCiktisi:
    """
    Görev 1 analiz çıktısını alarak eksik bilgi/belge durumunu tespit eder,
    kullanıcı bilgilendirme mesajı ve gerekiyorsa eksik belge talebi resmi yazısı üretir.
    """
    schema_str = json.dumps(KullaniciIletisimCiktisi.model_json_schema(), ensure_ascii=False)
    sistem_mesaji = f"""{KULLANICI_ILETISIM_PROMPT}

Beklenen JSON Şeması:
{schema_str}"""

    input_json_str = _normalize_input(girdi_verisi)
    user_prompt = f"Aşağıdaki Görev 1 evrak analiz verisini inceleyerek Kullanıcı Bilgilendirme çıktısını JSON olarak oluştur:\n\n{input_json_str}"
    
    if yonlendirme_karari:
        user_prompt += f"\n\nEvrak Yönlendirme Kararı (Aynı zamanda bu kurum/birim adına işlem yapılacak):\n{yonlendirme_karari.model_dump_json(indent=2)}"

    messages = [
        {"role": "system", "content": sistem_mesaji},
        {"role": "user", "content": user_prompt}
    ]

    max_deneme = 3
    son_hata = None

    for deneme in range(max_deneme):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1
            )

            raw_text = validate_response_content(response)

            if "<think>" in raw_text:
                if "</think>" in raw_text:
                    raw_text = raw_text.split("</think>")[-1].strip()
                else:
                    raw_text = re.sub(r"^<think>.*?(?=\{)", "", raw_text, flags=re.DOTALL).strip()

            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
            raw_text = re.sub(r"\s*```\s*$", "", raw_text, flags=re.MULTILINE)
            raw_text = raw_text.strip()

            start_idx = raw_text.find("{")
            end_idx = raw_text.rfind("}")
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                raw_text = raw_text[start_idx:end_idx + 1]

            raw_text = re.sub(r"//[^\n]*", "", raw_text)
            raw_text = re.sub(r"/\*.*?\*/", "", raw_text, flags=re.DOTALL)
            raw_text = re.sub(r",\s*([}\]])", r"\1", raw_text)

            try:
                cikti = KullaniciIletisimCiktisi.model_validate_json(raw_text)
            except Exception:
                payload = json.loads(raw_text)
                cikti = KullaniciIletisimCiktisi.model_validate(payload)

            return cikti

        except Exception as e:
            son_hata = e
            hata_str = str(e).lower()
            if "rate limit" in hata_str or "429" in hata_str:
                time.sleep(4)
            elif "json" in hata_str or "validation" in hata_str:
                time.sleep(1)
            else:
                time.sleep(2)

    if son_hata is not None:
        raise son_hata
    raise RuntimeError("Maksimum deneme sayısına ulaşıldı ve bir hata yakalanamadı.")

