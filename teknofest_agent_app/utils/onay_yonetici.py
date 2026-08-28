"""
onay_yonetici.py — C6: Kalıcı İki Aşamalı Onay Durumu Yöneticisi
===================================================================
Sorun: st.session_state sayfa yenilenince veya başka sekmeye geçilince
       sıfırlanır → içerik onayı kaybolur, ikinci onaylayan devam edemez.

Çözüm: Bekleyen onayları 'logs/bekleyen_onaylar.jsonl' dosyasına kalıcı
        olarak yaz. Her taslak için benzersiz bir 'onay_token' kullan.

Akış:
  1. İçerik uzmanı onay verir → kayıt oluşturulur (durum='icerik_onaylandi')
  2. KVKK sorumlusu onay verir → durum='tamamlandi', arşive kayıt tetiklenir
  3. Tamamlanan onaylar 30 dakika sonra temizlenebilir (isteğe bağlı)
"""

import json
import uuid
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

_ONAY_DOSYASI = Path("logs/bekleyen_onaylar.json")
_TTL_DAKIKA = 120  # Tamamlanan onaylar bu süre sonra temizlenir


def _dosya_yukle() -> dict:
    """Mevcut bekleyen onayları yükler."""
    _ONAY_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
    if not _ONAY_DOSYASI.exists():
        return {}
    try:
        with open(_ONAY_DOSYASI, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _dosya_kaydet(veri: dict) -> None:
    """Onay durumlarını dosyaya yazar."""
    _ONAY_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
    with open(_ONAY_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)


def _eski_kayitlari_temizle(veri: dict) -> dict:
    """TTL süresi dolmuş tamamlanmış kayıtları temizler."""
    simdi = datetime.utcnow()
    temizlenen = {
        token: kayit
        for token, kayit in veri.items()
        if not (
            kayit.get("durum") == "tamamlandi"
            and datetime.fromisoformat(kayit["guncelleme_zamani"])
            < simdi - timedelta(minutes=_TTL_DAKIKA)
        )
    }
    return temizlenen


def onay_token_uret(taslak_konu: str, taslak_govde: str) -> str:
    """
    Aynı taslak için her zaman aynı token üretir (deterministik).
    Böylece sayfa yenilendiğinde token kaybolmaz.
    """
    ozet = f"{taslak_konu}|{taslak_govde[:200]}"
    return hashlib.sha256(ozet.encode("utf-8")).hexdigest()[:16]


def icerik_onayi_kaydet(
    onay_token: str,
    onaylayan_sicil: str,
    konu: str,
    evrak_turu: str,
) -> dict:
    """
    C6 Adım 1: İçerik uzmanı onayını kalıcı olarak kaydeder.
    Döner: onay kaydı dict'i
    """
    veri = _dosya_yukle()
    veri = _eski_kayitlari_temizle(veri)

    kayit = {
        "token": onay_token,
        "durum": "icerik_onaylandi",
        "konu": konu,
        "evrak_turu": evrak_turu,
        "icerik_onaylayan": onaylayan_sicil,
        "icerik_onay_zamani": datetime.utcnow().isoformat() + "Z",
        "kvkk_onaylayan": None,
        "kvkk_onay_zamani": None,
        "guncelleme_zamani": datetime.utcnow().isoformat(),
    }
    veri[onay_token] = kayit
    _dosya_kaydet(veri)
    return kayit


def kvkk_onayi_kaydet(
    onay_token: str,
    kvkk_sicil: str,
) -> tuple[bool, str, dict]:
    """
    C6 Adım 2: KVKK sorumlusu onayını kaydeder.
    Döner: (basarili, hata_mesaji, onay_kaydi)

    Kontroller:
      - Token geçerli mi?
      - Adım 1 tamamlanmış mı?
      - Aynı kişi değil mi?
    """
    veri = _dosya_yukle()
    kayit = veri.get(onay_token)

    if not kayit:
        return False, "Onay token'ı bulunamadı veya süresi dolmuş. Lütfen İçerik Onayını tekrar verin.", {}

    if kayit.get("durum") != "icerik_onaylandi":
        return False, f"Geçersiz onay durumu: '{kayit.get('durum')}'. Adım 1 henüz tamamlanmamış.", {}

    icerik_sicil = kayit.get("icerik_onaylayan", "")
    if kvkk_sicil.strip() == icerik_sicil.strip():
        return (
            False,
            "🚫 Aynı kişi hem içerik hem KVKK onayını veremez (four-eyes prensibi). "
            "Farklı bir KVKK sorumlusu gereklidir.",
            kayit,
        )

    kayit["kvkk_onaylayan"] = kvkk_sicil.strip()
    kayit["kvkk_onay_zamani"] = datetime.utcnow().isoformat() + "Z"
    kayit["durum"] = "tamamlandi"
    kayit["guncelleme_zamani"] = datetime.utcnow().isoformat()
    veri[onay_token] = kayit
    _dosya_kaydet(veri)
    return True, "", kayit


def onay_durumu_getir(onay_token: str) -> dict | None:
    """Token'a ait mevcut onay durumunu döndürür (None = bulunamadı)."""
    veri = _dosya_yukle()
    return veri.get(onay_token)


def onay_iptal_et(onay_token: str) -> None:
    """Onay sürecini sıfırlar (güvenlik hatası sonrası)."""
    veri = _dosya_yukle()
    if onay_token in veri:
        del veri[onay_token]
        _dosya_kaydet(veri)
