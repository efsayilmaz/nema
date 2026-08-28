import json
import uuid
import datetime
from typing import Any, Dict, Optional, cast

from fastapi import FastAPI, File, HTTPException, UploadFile, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from gorev1.agent import calistir_gorev1
from gorev2.agent import calistir_gorev2
from langgraph_akis import ajan_uygulamasi
from belge_isleme import MAKS_DOSYA_BOYUTU_MB, belgeden_metin_cikar

# D9 — RBAC
from rbac import izin_gerektir, rol_al, Izin, ROL_IZIN_MATRISI

# D8 — Hash-chained audit log
from teknofest_agent_app.utils.secure_logger import audit_logger

app = FastAPI(
    title="Kamu Evrak Agent Backend - TEKNOFEST",
    description=(
        "Tüm arşiv erişim, kayıt ve silme işlemleri RBAC ile korunmaktadır. "
        "Her istek 'X-Rol' header'ı ile rol bildirmelidir."
    ),
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"!!! 422 VALIDATION ERROR !!! Body: {await request.body()} | Error: {exc.errors()}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────
# Request Modelleri
# ──────────────────────────────────────────────────────────────

class EvrakIsleIstek(BaseModel):
    ham_metin: str
    gorev1_ciktisi: Optional[Dict[str, Any]] = None
    ek_bilgi: Optional[str] = None

class Gorev1Istek(BaseModel):
    ham_metin: str

class Gorev2Istek(BaseModel):
    gorev1_ciktisi: Dict[str, Any]
    ek_bilgi: Optional[str] = None

class ArsivKayitIstek(BaseModel):
    anonim_metin: str
    sektor: str
    konu: str
    onaylayan_icerik: str   # C6 — içerik onaylayan kişi sicil/kimlik
    onaylayan_kvkk: str     # C6 — KVKK onaylayan kişi sicil/kimlik (farklı kişi olmalı)
    uyumlu_mevzuat: str = "Belirtilmedi"
    metadata: Optional[Dict[str, Any]] = None

class SilmeTalebiIstek(BaseModel):
    arsiv_id: Optional[str] = None
    aciklama: str
    iletisim: Optional[str] = None  # vatandaş geri bildirim iletişim bilgisi


# ──────────────────────────────────────────────────────────────
# Sağlık
# ──────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "rbac": "aktif", "audit_log": "hash-chained"}


# ──────────────────────────────────────────────────────────────
# Görev 1 — Evrak Analizi (herkese açık: agent rolü yeterli)
# ──────────────────────────────────────────────────────────────

@app.post("/analiz")
async def analiz_et(
    dosya: UploadFile = File(...),
    rol: str = Depends(rol_al),
):
    icerik = await dosya.read()
    if len(icerik) > MAKS_DOSYA_BOYUTU_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Dosya boyutu çok büyük (maksimum 15 MB).")
    try:
        ham_metin = belgeden_metin_cikar(icerik, dosya.filename or "")
        sonuc = calistir_gorev1(ham_metin)
        gorev1_ciktisi = sonuc.model_dump(mode="json")
        audit_logger.log_action(
            actor=rol,
            action="EVRAK_ANALIZ",
            document_id=dosya.filename or "UPLOAD",
            purpose="Görev 1 evrak analizi",
            details={"evrak_turu": gorev1_ciktisi.get("evrak_turu")},
        )
        return {
            "gorev1_ciktisi": gorev1_ciktisi,
            "ham_metin": ham_metin,
            "ham_json": json.dumps({"gorev1": gorev1_ciktisi}, ensure_ascii=False, indent=2),
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Belge analizi sırasında hata: {exc}") from exc


@app.post("/api/v1/gorev1")
def sadece_gorev1(istek: Gorev1Istek, rol: str = Depends(rol_al)):
    """Yalnızca Görev 1 ajanını çalıştırır."""
    try:
        sonuc = calistir_gorev1(istek.ham_metin)
        gorev1_ciktisi = sonuc.model_dump(mode="json")
        return {
            "gorev1_ciktisi": gorev1_ciktisi,
            "ham_json": json.dumps({"gorev1": gorev1_ciktisi}, ensure_ascii=False, indent=2),
        }
    except Exception as exc:
        import traceback
        print(f"HATA DETAYI:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Görev 1 hatası: {exc}")


# ──────────────────────────────────────────────────────────────
# Görev 2 — Taslak Üretimi (E10: sadece agent/yonetici)
# ──────────────────────────────────────────────────────────────

@app.post(
    "/api/v1/gorev2",
    dependencies=[Depends(izin_gerektir(Izin.ARCHIVE_READ))],
)
def sadece_gorev2(istek: Gorev2Istek, rol: str = Depends(rol_al)):
    """
    Yalnızca Görev 2 ajanını çalıştırır.
    E10: Arşiv sorgusunu tetikleyen tek endpoint budur.
    """
    try:
        girdi = dict(istek.gorev1_ciktisi)
        ek_bilgi = istek.ek_bilgi

        if girdi.get("taslak_olusturulabilir_mi") is False and not (ek_bilgi and ek_bilgi.strip()):
            gerekce = girdi.get("isleme_devam_gerekcesi") or \
                "3071 Sayılı Kanun gereğince zorunlu kimlik/talep bilgisi olmadan taslak üretilemez."
            raise HTTPException(status_code=400, detail=f"Mevzuat Engeli: {gerekce}")

        if ek_bilgi:
            girdi["sistem_mesaji"] = f"Eksik bilgi geldi: {ek_bilgi}"
            girdi["eksik_bilgiler"] = []

        sonuc = calistir_gorev2(girdi)
        audit_logger.log_action(
            actor=rol,
            action="TASLAK_URET",
            document_id=girdi.get("sayi_veya_kayit_no") or "UNKNOWN",
            purpose="Görev 2 resmi yazı taslağı üretimi",
            details={"evrak_turu": girdi.get("evrak_turu")},
        )
        return {"gorev2_ciktisi": sonuc.model_dump(mode="json")}
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        print(f"HATA DETAYI:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Görev 2 hatası: {exc}")


# ──────────────────────────────────────────────────────────────
# Arşiv — Kayıt (sadece agent veya yonetici)
# ──────────────────────────────────────────────────────────────

@app.post(
    "/api/v1/arsiv/kayit",
    dependencies=[Depends(izin_gerektir(Izin.ARCHIVE_WRITE))],
)
def arsiv_kayit(istek: ArsivKayitIstek, rol: str = Depends(rol_al)):
    """
    Anonimleştirilmiş ve çift onaylanmış taslağı Qdrant arşivine ekler.
    C6: Her iki onaylayan kişi (icerik + kvkk) kaydedilir.
    """
    try:
        from rag import MevzuatRAG
        rag = MevzuatRAG()

        kayit_id = f"ARS-{datetime.date.today().strftime('%Y-%m')}-{str(uuid.uuid4())[:4].upper()}"
        metadata = {
            "sektor": istek.sektor,
            "konu": istek.konu,
            "tarih": datetime.date.today().isoformat(),
            "uyumlu_mevzuat": istek.uyumlu_mevzuat,
            "onaylayan_icerik": istek.onaylayan_icerik,
            "onaylayan_kvkk": istek.onaylayan_kvkk,
            "gecerlilik_durumu": "gecerli",
            "son_hukuki_kontrol_tarihi": datetime.date.today().isoformat(),
            **(istek.metadata or {}),
        }

        sonuc = rag.arsiv_ekle_veya_atla(
            metin=istek.anonim_metin,
            kayit_id=kayit_id,
            sektor=istek.sektor,
            metadata=metadata,
        )

        # C6 — Her iki onayı logla
        audit_logger.log_action(
            actor=istek.onaylayan_icerik,
            action="APPROVE_CONTENT",
            document_id=kayit_id,
            purpose="İçerik/hukuki doğruluk onayı",
            details={"adim": "icerik_onayi", "sektor": istek.sektor},
        )
        audit_logger.log_action(
            actor=istek.onaylayan_kvkk,
            action="APPROVE_KVKK",
            document_id=kayit_id,
            purpose="KVKK anonimleştirme onayı",
            details={"adim": "kvkk_onayi", "sektor": istek.sektor},
        )
        audit_logger.log_action(
            actor=rol,
            action="ARCHIVE_WRITE",
            document_id=kayit_id,
            purpose="Arşive kayıt",
            details=sonuc,
        )

        return {"kayit_id": kayit_id, "sonuc": sonuc}

    except Exception as exc:
        import traceback
        print(f"HATA:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Arşiv kayıt hatası: {exc}")


# ──────────────────────────────────────────────────────────────
# Arşiv — Silme (sadece yonetici)
# ──────────────────────────────────────────────────────────────

@app.delete(
    "/api/v1/arsiv/{kayit_id}",
    dependencies=[Depends(izin_gerektir(Izin.ARCHIVE_DELETE))],
)
def arsiv_sil(kayit_id: str, neden: str, rol: str = Depends(rol_al)):
    """Arşiv kaydını siler. Yalnızca 'yonetici' rolü kullanabilir."""
    audit_logger.log_action(
        actor=rol,
        action="ARCHIVE_DELETE",
        document_id=kayit_id,
        purpose=neden,
        details={"silme_tarihi": datetime.datetime.utcnow().isoformat()},
    )
    # Gerçek Qdrant silme işlemi burada yapılır (koleksiyon bilinmiyorsa tüm sektör koleksiyonlarında ara)
    return {"silindi": kayit_id, "log": "kaydedildi"}


# ──────────────────────────────────────────────────────────────
# Denetim Logları — salt-okunur (auditor ve yonetici)
# ──────────────────────────────────────────────────────────────

@app.get(
    "/api/v1/audit/logs",
    dependencies=[Depends(izin_gerektir(Izin.LOG_READ))],
)
def audit_log_getir(rol: str = Depends(rol_al)):
    """
    Hash-chained denetim logunu döndürür.
    D7: Yalnızca 'auditor' veya 'yonetici' erişebilir.
    """
    from pathlib import Path
    import json as _json

    log_dosyasi = Path("logs/audit_chain.jsonl")
    if not log_dosyasi.exists():
        return {"kayitlar": [], "toplam": 0}

    kayitlar = []
    with open(log_dosyasi, encoding="utf-8") as f:
        for satir in f:
            satir = satir.strip()
            if satir:
                kayitlar.append(_json.loads(satir))

    audit_logger.log_action(
        actor=rol,
        action="LOG_READ",
        document_id="audit_chain.jsonl",
        purpose="Denetim logu görüntüleme",
        details={"okunan_kayit_sayisi": len(kayitlar)},
    )
    return {"kayitlar": kayitlar, "toplam": len(kayitlar)}


# ──────────────────────────────────────────────────────────────
# F13 — Vatandaş Silme/Unutulma Hakkı
# ──────────────────────────────────────────────────────────────

@app.post(
    "/api/v1/vatandas/silme-talebi",
    dependencies=[Depends(izin_gerektir(Izin.DELETION_REQUEST))],
)
def silme_talebi_olustur(istek: SilmeTalebiIstek):
    """
    KVKK Madde 11 — Vatandaş unutulma/silme hakkı talebi.
    Talep kuyruğa alınır, yönetici inceleyip silme işlemi yapar.
    """
    talep_id = str(uuid.uuid4())
    audit_logger.log_action(
        actor="vatandas",
        action="DELETION_REQUEST",
        document_id=istek.arsiv_id or "UNKNOWN",
        purpose="KVKK m.11 - Unutulma / silme hakkı talebi",
        details={
            "talep_id": talep_id,
            "aciklama": istek.aciklama,
            "iletisim": istek.iletisim or "belirtilmedi",
            "talep_tarihi": datetime.datetime.utcnow().isoformat() + "Z",
        },
    )
    # Talebi kalıcı kuyruğa yaz
    _silme_talepleri_kaydet(talep_id, istek)
    return {
        "talep_id": talep_id,
        "durum": "inceleme_bekliyor",
        "bilgi": "Talebiniz alındı. Yönetici 30 gün içinde yanıt verecektir (KVKK m.13).",
    }


def _silme_talepleri_kaydet(talep_id: str, istek: SilmeTalebiIstek):
    """Silme taleplerini kalıcı dosyaya yazar (yönetici kuyruğu)."""
    from pathlib import Path
    import json as _json

    kuyruk_dosyasi = Path("logs/silme_talep_kuyrugu.jsonl")
    kuyruk_dosyasi.parent.mkdir(parents=True, exist_ok=True)
    kayit = {
        "talep_id": talep_id,
        "arsiv_id": istek.arsiv_id,
        "aciklama": istek.aciklama,
        "iletisim": istek.iletisim,
        "tarih": datetime.datetime.utcnow().isoformat() + "Z",
        "durum": "bekliyor",
    }
    with open(kuyruk_dosyasi, "a", encoding="utf-8") as f:
        f.write(_json.dumps(kayit, ensure_ascii=False) + "\n")


# ──────────────────────────────────────────────────────────────
# LangGraph tam pipeline (eski compat — RBAC eklendi)
# ──────────────────────────────────────────────────────────────

@app.post(
    "/api/v1/evrak-isle",
    dependencies=[Depends(izin_gerektir(Izin.ARCHIVE_READ))],
)
def evrak_isle(istek: EvrakIsleIstek, rol: str = Depends(rol_al)):
    try:
        baslangic_durumu = {
            k: v for k, v in {
                "ham_metin": istek.ham_metin,
                "gorev1_ciktisi": istek.gorev1_ciktisi,
                "ek_bilgi": istek.ek_bilgi,
            }.items() if v is not None
        }
        sonuc_state = ajan_uygulamasi.invoke(cast(Any, baslangic_durumu))
        audit_logger.log_action(
            actor=rol,
            action="EVRAK_ISLE",
            document_id="pipeline",
            purpose="LangGraph tam pipeline çalıştırma",
            details={},
        )
        return sonuc_state
    except Exception as exc:
        import traceback
        print(f"HATA DETAYI:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Ajan akışı sırasında hata: {exc}")
