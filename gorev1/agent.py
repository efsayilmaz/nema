import json
import os
import re
import warnings
from pathlib import Path
from typing import Optional, Union

from evren_client import get_evren_client, validate_response_content
from pydantic import ValidationError

from gorev1.schemas import Gorev1CiktiSemasi
from rag import MevzuatRAG

warnings.filterwarnings("ignore")
MAX_INPUT_CHARACTERS = 6000

# Performans için RAG sistemini global olarak önbellekte (cache) tutalım
_RAG_SISTEMI = None

def get_rag_sistemi() -> MevzuatRAG:
    global _RAG_SISTEMI
    if _RAG_SISTEMI is None:
        _RAG_SISTEMI = MevzuatRAG()
    return _RAG_SISTEMI


GOREV1_SYSTEM_INSTRUCTION = """
Türkçe kamu evrakını analiz et. Yalnızca geçerli JSON üret; açıklama, markdown
ve düşünme metni yazma. Bilgi yoksa null veya [] kullan, asla uydurma.
Evrak türü, kısa resmi konu ve 1-3 cümlelik özet çıkar. Tarih ve sayı/kayıt
numarasını yalnızca açıkça yazılmışsa doldur. Göndereni ve iletişim bilgilerini
çıkar. Kurum, lokasyon ve tarihleri listele. Mevzuat ve eksik belgeleri listele.
Aciliyet yalnızca Normal, İvedi veya Çok İvedi olsun; can/çocuk güvenliği,
elektrik, yangın, afet, haciz veya yakın süreli risk varsa İvedi/Çok İvedi seç.
"""


def _normalize_input(evrak_metni: Union[str, dict]) -> str:
    if isinstance(evrak_metni, dict):
        metin = json.dumps(evrak_metni, ensure_ascii=False, indent=2)
    else:
        metin = str(evrak_metni).strip()

    if len(metin) <= MAX_INPUT_CHARACTERS:
        return metin

    return (
        metin[:MAX_INPUT_CHARACTERS]
        + "\n\n[Belgenin geri kalanı Groq token sınırı nedeniyle kısaltıldı.]"
    )


def _remove_code_fence(raw_text: str) -> str:
    raw_text = raw_text.strip()
    if not raw_text.startswith("```"):
        return raw_text

    lines = raw_text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _remove_thinking(raw_text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()


def _normalize_payload(payload: dict) -> dict:
    if "sayi_veya_kayit_no" not in payload:
        payload["sayi_veya_kayit_no"] = payload.pop("evrak_sayi_kayit", None)
    if "kisa_ozet" not in payload:
        payload["kisa_ozet"] = payload.pop("ozet", "")

    if "gonderen" not in payload:
        bilgiler = payload.pop("gonderen_bilgileri", {}) or {}
        payload["gonderen"] = {
            "gonderen_tipi": payload.pop("gonderen_tipi", "Gerçek Kişi"),
            "ad_soyad_veya_unvan": bilgiler.get("ad_soyad") or bilgiler.get("kurum_sirket_adi"),
            "kimlik_veya_vergi_no": bilgiler.get("tc_vergi_no"),
            "iletisim_bilgisi": ", ".join(
                value for value in (
                    bilgiler.get("telefon"),
                    bilgiler.get("eposta"),
                    bilgiler.get("adres"),
                ) if value
            ) or None,
        }
    return payload


def calistir_gorev1(
    evrak_metni: Union[str, dict],
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Gorev1CiktiSemasi:
    """Tek bir ham evrak metnini analiz ederek Görev 1 çıktısı üretir."""
    selected_model = model_name or os.getenv("EVREN_MODEL", "llm-fast")

    client = get_evren_client()
    input_text = _normalize_input(evrak_metni)

    rag = get_rag_sistemi()
    mevzuat_baglami = rag.mevzuat_sorgula(input_text, getirilecek_sonuc_sayisi=2)

    prompt = f"""
Aşağıdaki tek ham evrakı analiz et ve Görev 1 çıktısını oluştur.

HAM EVRAK:
--------------------
{input_text}
--------------------

SİSTEMDEN GELEN İLGİLİ MEVZUAT BAĞLAMI:
{mevzuat_baglami}
Lütfen Görev 1 analizini yaparken, uydurma kanunlar yazmak yerine SADECE yukarıda verilen mevzuat bağlamını kullan.

Yalnızca aşağıdaki anahtarları kullanarak tek bir JSON nesnesi döndür:
{{"evrak_turu":"...","konu":"...","evrak_tarihi":null,
"sayi_veya_kayit_no":null,"gonderen":{{"gonderen_tipi":"...",
"ad_soyad_veya_unvan":null,"kimlik_veya_vergi_no":null,
"iletisim_bilgisi":null}},"kisa_ozet":"...",
"varliklar":{{"kurumlar":[],"lokasyonlar":[],"tarihler":[]}},
"ilgili_mevzuat_onerisi":[],"eksik_bilgiler":[],"aciliyet_durumu":"Normal"}}
"""

    response = client.chat.completions.create(
        model=selected_model,
        messages=[
            {"role": "system", "content": GOREV1_SYSTEM_INSTRUCTION},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )

    raw_text = validate_response_content(response)
    raw_text = _remove_thinking(raw_text)
    raw_text = _remove_code_fence(raw_text)
    if not raw_text:
        raise ValueError("Model boş JSON döndürdü.")

    try:
        return Gorev1CiktiSemasi.model_validate_json(raw_text)
    except ValidationError:
        try:
            payload = json.loads(raw_text)
            return Gorev1CiktiSemasi.model_validate(_normalize_payload(payload))
        except Exception as exc:  # pragma: no cover - hata detayını net göstersin
            raise ValueError(
                "Model çıktısı beklenen şemaya uymuyor. "
                f"Ham çıktı: {raw_text[:500]}"
            ) from exc
