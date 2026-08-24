import json
import os
import re
import time
from typing import Dict, Any, Union, Optional

from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel

from gorev2.schemas import (
    Gorev2CiktiSemasi,
    Gorev1CiktiSemasi,
    YaziTuru,
    AksiyonDurumu
)

load_dotenv()


GOREV2_SYSTEM_INSTRUCTION = """
Sen kamu kurumlarında görev yapan kıdemli ve uzman bir evrak işleme, yönlendirme ve resmî yazışma yapay zeka ajanısın.
Sana Görev 1 aşamasında analiz edilmiş, özeti ve özellikleri çıkarılmış bir evrak verisi (JSON formatında) sunulacaktır.

GÖREVİN:
Verilen evrak analizini dikkatle inceleyerek aşağıdaki üç temel bileşenden oluşan yapılandırılmış çıktıyı (Gorev2CiktiSemasi) üretmektir:

1. YÖNLENDİRME KARARI (`yonlendirme_karari`):
   - `islem_yapacak_ana_kurum`: Evrakla ilgili asıl yetkili ve görevli ana kamu kurumu/idare.
   - `geregi_icin_yonlendirilecek_birim`: Doğrudan alt birim / müdürlük / bölüm.
   - `bilgi_icin_iletilecek_birimler`: Bilgilendirilmesi gereken diğer ilgili yan birimlerin listesi.
   - `yonlendirme_gerekcesi`: Mevzuat, aciliyet ve görev alanına dayanan açıklayıcı gerekçe.

2. RESMÎ YAZI TASLAĞI (`resmi_yazi_taslagi`):
   - `yazi_turu`: Yalnızca şu 4 değerden biri olmalıdır: "Eksik Bilgi/Belge Talebi", "Üst Yazı", "Cevap Yazısı", "Bilgilendirme Metni".
   - `konu`: Resmî yazının özü ve mevzuata uygun konusu.
   - `ilgi`: Evraka referans veren resmî ilgi tutma cümlesi.
   - `govde_metni`: Resmî yazışma kurallarına uygun, kurumsal ve ciddi bir dille yazılmış gövde metni.
   - `imza_makami`: Yazıyı imzalayacak/onaylayacak yetkili makam unvanı.

3. KULLANICI BİLGİLENDİRME (`kullanici_bilgilendirme`):
   - `kullaniciya_gosterilecek_mesaj`: Ayrıntılı ve anlaşılır bilgilendirme mesajı.
   - `sistem_aksiyon_durumu`: Yalnızca şu 3 değerden biri olmalıdır: "Kullanıcı Bekleniyor", "İşleme Alındı", "Onay Bekliyor".

Tüm alan adlarına (%100 birebir aynı key'ler) ve belirtilen enum değerlerine harfiyen uy.
YALNIZCA geçerli bir JSON nesnesi döndür. Markdown, açıklama veya düşünme metni YAZMA.
"""


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


def calistir_gorev2(
    girdi_verisi: Union[dict, str, BaseModel, Gorev1CiktiSemasi],
    api_key: Optional[str] = None,
    model_name: str = "qwen/qwen3.6-27b"
) -> Gorev2CiktiSemasi:
    """
    Görev 1 analiz çıktısını alarak, Groq API (Qwen 3.6 27B) structured output
    mekanizması ile Görev 2 resmî yazı taslaklama ve yönlendirme çıktısı üretir.

    Args:
        girdi_verisi: Görev 1 analiz çıktısı (dict, JSON string veya Gorev1CiktiSemasi).
        api_key: Groq API Anahtarı (Verilmezse GROQ_API_KEY ortam değişkeninden alınır).
        model_name: Kullanılacak Groq modeli (Varsayılan: "qwen/qwen3.6-27b").

    Returns:
        Gorev2CiktiSemasi: Görev 2 standart Pydantic çıktı nesnesi.
    """
    client = Groq(api_key=api_key or os.getenv("GROQ_API_KEY"))

    schema_str = json.dumps(Gorev2CiktiSemasi.model_json_schema(), ensure_ascii=False)

    sistem_mesaji = f"""{GOREV2_SYSTEM_INSTRUCTION}

Beklenen JSON Şeması:
{schema_str}"""

    input_json_str = _normalize_input(girdi_verisi)
    user_prompt = f"Aşağıdaki Görev 1 evrak analiz verisini inceleyerek Görev 2 çıktısını eksiksiz bir JSON nesnesi olarak oluştur:\n\n{input_json_str}"

    messages = [
        {"role": "system", "content": sistem_mesaji},
        {"role": "user", "content": user_prompt}
    ]

    max_deneme = 3
    son_hata = None

    for deneme in range(max_deneme):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.1,
                max_tokens=4000
            )

            raw_text = response.choices[0].message.content.strip()

            # <think>...</think> düşünce bloklarını temizle
            if "<think>" in raw_text:
                if "</think>" in raw_text:
                    raw_text = raw_text.split("</think>")[-1].strip()
                else:
                    raw_text = re.sub(r"^<think>.*?(?=\{)", "", raw_text, flags=re.DOTALL).strip()

            # Markdown kod blokları varsa temizle
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
            raw_text = re.sub(r"\s*```\s*$", "", raw_text, flags=re.MULTILINE)
            raw_text = raw_text.strip()

            # Geçerli JSON nesnesini bul ({ ile } arasındaki en dış blok)
            start_idx = raw_text.find("{")
            end_idx = raw_text.rfind("}")
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                raw_text = raw_text[start_idx:end_idx + 1]

            # JSON yorum satırlarını temizle (// ... ve /* ... */)
            raw_text = re.sub(r"//[^\n]*", "", raw_text)
            raw_text = re.sub(r"/\*.*?\*/", "", raw_text, flags=re.DOTALL)

            # Trailing comma'ları temizle (], } öncesindeki virgüller)
            raw_text = re.sub(r",\s*([}\]])", r"\1", raw_text)

            # Önce JSON olarak doğrulamayı dene
            try:
                return Gorev2CiktiSemasi.model_validate_json(raw_text)
            except Exception:
                # JSON parse edip dict üzerinden doğrula
                payload = json.loads(raw_text)
                return Gorev2CiktiSemasi.model_validate(payload)

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

