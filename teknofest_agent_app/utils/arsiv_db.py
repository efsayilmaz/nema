"""
arsiv_db.py — Emsal Taslak Arşivi Yerel Veritabanı
====================================================
Bu modül JSON tabanlı yerel arşivi yönetir (demo/geliştirme ortamı).
Üretimde bu katman Qdrant'a (rag.MevzuatRAG.arsiv_ekle_veya_atla) bağlanmalıdır.

G14: arsive_ekle() artık benzerlik eşiği kontrolü yapmaktadır.
G15: Kayıt şeması genişletildi (gecerlilik_durumu, referans_sayaci vb.)
"""

import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Optional

DB_FILE = Path(os.path.dirname(os.path.abspath(__file__))) / ".." / "arsiv_verileri.json"

# G15 — Genişletilmiş metadata şemasının zorunlu varsayılanları
_VARSAYILAN_METADATA = {
    "evrak_turu": "Belirtilmedi",
    "birim": "Belirtilmedi",
    "ilgili_kanun_maddeleri": [],
    "mevzuat_versiyon_tarihi": None,
    "gecerlilik_durumu": "gecerli",        # gecerli | incelemede | gecersiz
    "son_hukuki_kontrol_tarihi": None,
    "kaynak_emsal_idleri": [],             # F12 — traceability
    "rag_benzerlik_skoru": None,
    "referans_sayaci": 0,                  # G14 — duplicate sayacı
    "kullanım_sayisi": 0,
}


def arsiv_verilerini_getir() -> list:
    """Tüm arşiv kayıtlarını döndürür."""
    if not DB_FILE.exists():
        return []
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _arsiv_kaydet(veriler: list) -> None:
    """Tüm arşivi dosyaya yazar."""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(veriler, f, ensure_ascii=False, indent=4)


def arsive_ekle(kayit_dict: dict) -> dict:
    """
    Yeni kayıt ekler. G15 şema garantisi: eksik alanlar varsayılanla doldurulur.
    NOT: Qdrant benzerlik kontrolü rag.MevzuatRAG.arsiv_ekle_veya_atla'da yapılır.
         Bu fonksiyon yalnızca JSON arşivi günceller.
    """
    # G15 — Eksik metadata alanlarını doldur
    for alan, varsayilan in _VARSAYILAN_METADATA.items():
        if alan not in kayit_dict:
            kayit_dict[alan] = varsayilan

    # Tarih garantisi
    if not kayit_dict.get("tarih"):
        kayit_dict["tarih"] = date.today().isoformat()
    if not kayit_dict.get("son_hukuki_kontrol_tarihi"):
        kayit_dict["son_hukuki_kontrol_tarihi"] = date.today().isoformat()

    veriler = arsiv_verilerini_getir()
    veriler.append(kayit_dict)
    _arsiv_kaydet(veriler)
    return kayit_dict


def arsiv_migrate() -> int:
    """
    G15 — Mevcut kayıtları yeni şemaya migrate eder.
    Eksik alanları varsayılan değerlerle doldurur.
    Döner: güncellenen kayıt sayısı.
    """
    veriler = arsiv_verilerini_getir()
    guncellenen = 0
    for kayit in veriler:
        degisti = False
        for alan, varsayilan in _VARSAYILAN_METADATA.items():
            if alan not in kayit:
                kayit[alan] = varsayilan
                degisti = True
        # Eski 'KVKK Otomatı' onaylarını işaretle
        onaylayanlar = kayit.get("onaylayanlar", [])
        if any("Otomatı" in str(o) for o in onaylayanlar):
            kayit["_legacy_otomat_onayi"] = True  # geriye dönük not
            degisti = True
        if degisti:
            guncellenen += 1
    if guncellenen:
        _arsiv_kaydet(veriler)
    return guncellenen


# G15 — Modül yüklendiğinde migration'ı otomatik çalıştır (idempotent)
_migrasyon_sayisi = arsiv_migrate()
if _migrasyon_sayisi:
    print(f"[arsiv_db] G15 migration tamamlandı: {_migrasyon_sayisi} kayıt güncellendi.")



def arsiv_referans_artir(kayit_id: str) -> bool:
    """
    G14 — Duplicate tespit edildiğinde referans sayacını artırır.
    Döner: True (bulundu ve güncellendi), False (bulunamadı)
    """
    veriler = arsiv_verilerini_getir()
    for kayit in veriler:
        if kayit.get("id") == kayit_id:
            kayit["referans_sayaci"] = kayit.get("referans_sayaci", 0) + 1
            _arsiv_kaydet(veriler)
            return True
    return False


def arsiv_gecersizlestir(kayit_id: str, neden: str = "mevzuat_degisikligi") -> bool:
    """
    G16 — Kayıdı 'incelemede' durumuna çeker.
    Mevzuat değişikliği job'ı tarafından çağrılır.
    """
    veriler = arsiv_verilerini_getir()
    for kayit in veriler:
        if kayit.get("id") == kayit_id:
            kayit["gecerlilik_durumu"] = "incelemede"
            kayit["gecersizlestirme_nedeni"] = neden
            kayit["gecersizlestirme_tarihi"] = datetime.utcnow().isoformat() + "Z"
            _arsiv_kaydet(veriler)
            return True
    return False


def mevzuat_degisiklik_tara(degisen_kanun_maddeleri: list[str]) -> list[str]:
    """
    G16 — Değişen kanun maddelerine referans veren arşiv kayıtlarını
    otomatik olarak 'incelemede' durumuna çeker.
    Döner: etkilenen kayıt ID'leri listesi.
    """
    veriler = arsiv_verilerini_getir()
    etkilenenler = []
    for kayit in veriler:
        maddeler = kayit.get("ilgili_kanun_maddeleri", [])
        uyumlu_mevzuat = kayit.get("uyumlu_mevzuat", "")
        etkilendi = any(
            m in maddeler or m in uyumlu_mevzuat
            for m in degisen_kanun_maddeleri
        )
        if etkilendi and kayit.get("gecerlilik_durumu") == "gecerli":
            kayit["gecerlilik_durumu"] = "incelemede"
            kayit["gecersizlestirme_nedeni"] = "mevzuat_degisikligi"
            kayit["gecersizlestirme_tarihi"] = datetime.utcnow().isoformat() + "Z"
            etkilenenler.append(kayit["id"])

    if etkilenenler:
        _arsiv_kaydet(veriler)

    return etkilenenler


def arsiv_kayit_sil(kayit_id: str) -> bool:
    """
    F13 — Vatandaş unutulma hakkı talebi sonrası yönetici silme işlemi.
    Döner: True (silindi), False (bulunamadı)
    """
    veriler = arsiv_verilerini_getir()
    onceki_uzunluk = len(veriler)
    veriler = [k for k in veriler if k.get("id") != kayit_id]
    if len(veriler) < onceki_uzunluk:
        _arsiv_kaydet(veriler)
        return True
    return False


def arsiv_sektor_filtrele(sektor: str) -> list:
    """Belirli sektördeki kayıtları döndürür (auditor görünümü için)."""
    return [k for k in arsiv_verilerini_getir() if sektor.lower() in (k.get("sektor") or "").lower()]
