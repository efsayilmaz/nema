import json
import os
import re
import warnings
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional, Union

from evren_client import get_evren_client
from pydantic import ValidationError

from gorev1.mevzuat_ajani import calistir_mevzuat_ajani
from gorev1.ozetleme_ajani import calistir_ozetleme_ajani
from gorev1.siniflandirma_ajani import calistir_siniflandirma_ajani
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


# Anahtarlar evrak türü ve mevzuat numarasıdır; yeni satırlar buraya eklenebilir.
YASAL_YANIT_SURESI_LOOKUP = {
    ("bilgi_edinme_basvurusu", "4982"): ("15 iş günü", "4982 sayılı Kanun m.11"),
    ("bilgi_edinme_basvurusu_aktarim", "4982"): ("30 iş günü", "4982 sayılı Kanun m.11"),
    ("dilekçe", "3071"): ("30 gün", "3071 sayılı Kanun m.7"),
    ("idari_basvuru", "3071"): ("30 gün", "3071 sayılı Kanun m.7"),
    ("tüketici_şikayeti", "6502"): (
        "Kanunda azami süre belirtilmemiştir",
        "6502 sayılı Kanun m.68-70",
    ),
}


def _normalize_document_type(value: str) -> str:
    value = value.casefold().replace("î", "i").replace("ı", "i")
    value = re.sub(r"[^a-z0-9çğıöşü ]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    if "bilgi edinme" in value:
        return "bilgi_edinme_basvurusu"
    if any(term in value for term in ("tüketici", "tuketici", "ayıplı", "ayipli")):
        return "tüketici_şikayeti"
    if "idari başvuru" in value or "idari basvuru" in value:
        return "idari_basvuru"
    if "dilek" in value:
        return "dilekçe"
    return value.replace(" ", "_")


def lookup_yasal_yanit_suresi(evrak_turu: str, mevzuat: list[str], source_text: str = "") -> Optional[str]:
    """Yasal süreyi yalnızca statik tablo eşleşmesine göre döndürür."""
    tur = _normalize_document_type(evrak_turu)
    source = source_text.casefold()
    for madde in mevzuat:
        match = re.search(r"\b(3071|4982|6502)\b", str(madde))
        if not match:
            continue
        kanun_no = match.group(1)
        if tur == "bilgi_edinme_basvurusu" and any(
            ifade in source for ifade in ("başka kurum", "baska kurum", "kurum arşivinde yok", "kurum arsivinde yok")
        ):
            tur = "bilgi_edinme_basvurusu_aktarim"
        kayit = YASAL_YANIT_SURESI_LOOKUP.get((tur, kanun_no))
        if kayit:
            sure, referans = kayit
            return f"{sure} ({referans})"
    return None


def _tuketici_evraki_mi(evrak_turu: str, source_text: str) -> bool:
    metin = f"{evrak_turu} {source_text}".casefold()
    return any(
        ifade in metin
        for ifade in ("tüketici", "tuketici", "ayıplı", "ayipli", "iade", "değişim", "degisim")
    )


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
    if "evrak_ozeti" not in payload:
        payload["evrak_ozeti"] = payload.get("kisa_ozet") or payload.pop("ozet", "")
    if "kisa_ozet" not in payload:
        payload["kisa_ozet"] = payload.get("evrak_ozeti", "")
    payload.setdefault("onemli_bilgi_unsurlari", [])
    payload.setdefault("yasal_yanit_suresi", None)

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
        
    aciliyet = payload.get("aciliyet_durumu", "")
    if isinstance(aciliyet, str):
        aciliyet_lower = aciliyet.lower()
        if any(w in aciliyet_lower for w in ["çok acil", "çok ivedi"]):
            payload["aciliyet_durumu"] = "Çok İvedi"
        elif any(w in aciliyet_lower for w in ["acil", "yüksek", "ivedi"]):
            payload["aciliyet_durumu"] = "İvedi"
        elif aciliyet_lower in ["normal", "düşük", "dusuk", "yok", "belirtilmemiş"]:
            payload["aciliyet_durumu"] = "Normal"
        elif aciliyet_lower not in ["normal", "ivedi", "çok ivedi"]:
            payload["aciliyet_durumu"] = "Normal"
    elif aciliyet is None:
        payload["aciliyet_durumu"] = "Normal"

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
        result = Gorev1CiktiSemasi.model_validate(_normalize_payload(json.loads(raw_text)))
    except (ValidationError, json.JSONDecodeError, TypeError) as exc:
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
    """Üç uzman ajanı çalıştırıp çıktıları tek Görev 1 nesnesinde birleştirir."""
    selected_model = model_name or os.getenv("EVREN_MODEL", "llm-fast")

    client = get_evren_client()
    input_text = _normalize_input(evrak_metni)

    rag = get_rag_sistemi()
    mevzuat_baglami = rag.mevzuat_sorgula(input_text, getirilecek_sonuc_sayisi=2)

    ozet = calistir_ozetleme_ajani(client, selected_model, input_text)
    siniflandirma = calistir_siniflandirma_ajani(client, selected_model, input_text)
    mevzuat = calistir_mevzuat_ajani(
        client, selected_model, input_text, mevzuat_baglami
    )

    merged = dict(siniflandirma)
    merged["konu"] = ozet.get("konu") or merged.get("konu", "")
    merged["evrak_ozeti"] = ozet.get("kisa_ozet") or ozet.get("evrak_ozeti") or ozet.get("ozet") or ""
    merged["kisa_ozet"] = merged["evrak_ozeti"]
    merged["ilgili_mevzuat_onerisi"] = mevzuat.get("ilgili_mevzuat_onerisi", [])
    if not merged["ilgili_mevzuat_onerisi"] and _tuketici_evraki_mi(
        merged.get("evrak_turu", ""), input_text
    ):
        merged["ilgili_mevzuat_onerisi"] = [
            "6502 sayılı Tüketicinin Korunması Hakkında Kanun (ayıplı mal/hizmet, m.8-11; hakem heyeti m.68-70)"
        ]
    merged["eksik_bilgiler"] = mevzuat.get("eksik_bilgiler", [])
    merged["yasal_yanit_suresi"] = lookup_yasal_yanit_suresi(
        merged.get("evrak_turu", ""),
        merged["ilgili_mevzuat_onerisi"],
        input_text,
    )
    try:
        return _parse_gorev1_response(json.dumps(merged, ensure_ascii=False), input_text)
    except ValueError as exc:
        if "kisa_ozet" not in str(exc):
            raise
        duzeltilmis_ozet = calistir_ozetleme_ajani(
            client, selected_model, input_text, duzeltme_istemi=True
        )
        merged["konu"] = duzeltilmis_ozet.get("konu", merged.get("konu", ""))
        merged["evrak_ozeti"] = duzeltilmis_ozet.get("kisa_ozet", duzeltilmis_ozet.get("evrak_ozeti", ""))
        merged["kisa_ozet"] = merged["evrak_ozeti"]
        return _parse_gorev1_response(json.dumps(merged, ensure_ascii=False), input_text)
