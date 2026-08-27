import json
import os
import re
import warnings
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional, Union

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
Evrak türü, kısa resmi konu ve 1-3 cümlelik özet çıkar. KONU ve KISA ÖZET
alanlarını üretirken tek ilke şudur: Bu iki alan yalnızca evrakın NİYETİNİ
(ne istendiğini veya bildirildiğini) ve GEREKÇESİNİ (neden istendiğini) kendi
cümlelerinle anlatır. Evrakın kimliğine ait hiçbir unsur bu alanlara giremez:
kime gönderildiği, yazılma tarihi, sayı/kayıt numarası, gönderenin adı/unvanı,
adresi veya iletişim bilgileri. Bunlar ayrı alanlarda tutulur.
Konu ve özet, evrakın biçimini ya da metindeki başlıkların sırasını kopyalamaz.
Kendine şu kontrolü uygula: "Bu cümleyi, evrakın metnini görmeden yalnızca
olayı bilen biri kurabilir miydi?" Hayırsa cümleyi sıfırdan yeniden yaz.
KONU VE KISA ÖZET — KESİN YASAKLAR: kurum/makam adı, alıcı, gönderen,
"Tarih:" veya "Konu:" ifadesi, herhangi bir tarih/sayı formatı, adres,
iletişim bilgisi ya da başlık satırının kopyası içeremez. Özet, başlık bölümü
görülmeden talebi ve gerekçeyi anlatan özgün cümlelerden oluşmalıdır. JSON'u
döndürmeden önce bu kurala göre kontrol et.
Tarih ve sayı/kayıt numarasını yalnızca açıkça yazılmışsa doldur. Göndereni ve
iletişim bilgilerini çıkar. Kurum, lokasyon ve tarihleri listele. Mevzuat ve
eksik belgeleri listele.
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


def _normalize_summary_text(value: str) -> str:
    return re.sub(r"[^a-z0-9çğıöşüİı ]", " ", value.casefold()).strip()


def _summary_breaks_rule(payload: dict, source_text: str = "") -> bool:
    texts = [payload.get("konu", ""), payload.get("kisa_ozet", "")]
    normalized_texts = [_normalize_summary_text(text) for text in texts]
    if any(not text for text in normalized_texts):
        return True

    if any(
        re.search(r"\b(tarih|konu)\s*:", text, re.IGNORECASE)
        for text in texts
    ):
        return True

    gonderen = payload.get("gonderen", {}) or {}
    forbidden_phrases = list(payload.get("varliklar", {}).get("kurumlar", []))
    forbidden_phrases.extend(
        value for key in ("ad_soyad_veya_unvan", "iletisim_bilgisi")
        if (value := gonderen.get(key))
    )

    for phrase in forbidden_phrases:
        normalized_phrase = _normalize_summary_text(str(phrase))
        if normalized_phrase and any(normalized_phrase in text for text in normalized_texts):
            return True

    dates = list(payload.get("varliklar", {}).get("tarihler", []))
    if payload.get("evrak_tarihi"):
        dates.append(payload["evrak_tarihi"])
    for date in dates:
        normalized_date = _normalize_summary_text(str(date))
        if normalized_date and any(normalized_date in text for text in normalized_texts):
            return True
    if any(re.search(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b", text) for text in texts):
        return True
    if any(re.search(r"\b\S+\s+(mahallesi|mah\.)\b.*\b(sokak|cadde|bulvarı|no:)\b", text, re.IGNORECASE) for text in texts):
        return True

    topic = _normalize_summary_text(str(payload.get("konu", "")))
    topic_tokens = topic.split()
    summary = normalized_texts[1]
    if len(topic_tokens) >= 3 and topic in summary:
        return True
    if topic and SequenceMatcher(None, topic, summary).ratio() >= 0.88:
        return True

    source_first_sentence = re.split(r"(?<=[.!?])\s+|\n+", source_text.strip(), maxsplit=1)[0]
    normalized_first_sentence = _normalize_summary_text(source_first_sentence)
    if normalized_first_sentence:
        for text in normalized_texts:
            overlap = SequenceMatcher(None, normalized_first_sentence, text).ratio()
            if overlap > 0.70:
                return True
    if any(token in text for token in ("başkanlığına", "müdürlüğüne") for text in normalized_texts):
        return True
    return False


def _parse_gorev1_response(raw_text: str, source_text: str = "") -> Gorev1CiktiSemasi:
    raw_text = _remove_thinking(raw_text)
    raw_text = _remove_code_fence(raw_text)
    if not raw_text:
        raise ValueError("Model boş JSON döndürdü.")

    try:
        result = Gorev1CiktiSemasi.model_validate_json(raw_text)
    except ValidationError:
        try:
            result = Gorev1CiktiSemasi.model_validate(_normalize_payload(json.loads(raw_text)))
        except Exception as exc:  # pragma: no cover - hata detayını net göstersin
            raise ValueError(
                "Model çıktısı beklenen şemaya uymuyor. "
                f"Ham çıktı: {raw_text[:500]}"
            ) from exc

    if _summary_breaks_rule(result.model_dump(), source_text):
        raise ValueError("Model kisa_ozet alanında başlık bilgilerini tekrarladı.")
    return result


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

    messages: list[Any] = [
        {"role": "system", "content": GOREV1_SYSTEM_INSTRUCTION},
        {"role": "user", "content": prompt},
    ]
    last_error = None
    for attempt in range(2):
        if attempt:
            messages.append({
                "role": "user",
                "content": (
                    "Önceki konu veya kisa_ozet kurala aykırıydı. Her iki alanı da "
                    "sıfırdan yaz: yalnızca evrakın niyetini ve gerekçesini kendi "
                    "cümlelerinle anlat. Alıcı, gönderen, ad/unvan, adres, iletişim, "
                    "kurum, tarih, sayı/kayıt, başlık ve 'Tarih:'/'Konu:' ifadelerini "
                    "kesinlikle kullanma."
                ),
            })
        response = client.chat.completions.create(
            model=selected_model,
            messages=messages,
            temperature=0.1,
        )
        try:
            return _parse_gorev1_response(validate_response_content(response), input_text)
        except ValueError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise RuntimeError("Görev 1 yanıt üretmedi.")
