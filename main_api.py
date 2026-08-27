import json
from typing import Any, Dict, Optional, cast

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from gorev1.agent import calistir_gorev1
from gorev2.agent import calistir_gorev2
from langgraph_akis import ajan_uygulamasi
from belge_isleme import MAKS_DOSYA_BOYUTU_MB, belgeden_metin_cikar

app = FastAPI(title="Kamu Evrak Agent Backend - TEKNOFEST")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class EvrakIsleIstek(BaseModel):
    ham_metin: str
    gorev1_ciktisi: Optional[Dict[str, Any]] = None
    ek_bilgi: Optional[str] = None

@app.get("/health")
def health():
    return {"status": "ok"}

# ------------------------------------------------------------------
# Ayrı Endpoint'ler: Sadece ilgili ajanı çalıştırır
# ------------------------------------------------------------------

class Gorev1Istek(BaseModel):
    ham_metin: str

class Gorev2Istek(BaseModel):
    gorev1_ciktisi: Dict[str, Any]
    ek_bilgi: Optional[str] = None


@app.post("/analiz")
async def analiz_et(dosya: UploadFile = File(...)):
    icerik = await dosya.read()
    if len(icerik) > MAKS_DOSYA_BOYUTU_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Dosya boyutu çok büyük (maksimum 15 MB).")
    try:
        ham_metin = belgeden_metin_cikar(icerik, dosya.filename or "")
        sonuc = calistir_gorev1(ham_metin)
        gorev1_ciktisi = sonuc.model_dump(mode="json")
        return {
            "gorev1_ciktisi": gorev1_ciktisi,
            "ham_metin": ham_metin,
            "ham_json": json.dumps({"gorev1": gorev1_ciktisi}, ensure_ascii=False, indent=2),
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Belge analizi sırasında hata oluştu: {exc}") from exc

@app.post("/api/v1/gorev1")
def sadece_gorev1(istek: Gorev1Istek):
    """Yalnızca Görev 1 ajanını çalıştırır ve sonucu döndürür."""
    try:
        sonuc = calistir_gorev1(istek.ham_metin)
        gorev1_ciktisi = sonuc.model_dump(mode="json")
        return {
            "gorev1_ciktisi": gorev1_ciktisi,
            "ham_json": json.dumps(
                {"gorev1": gorev1_ciktisi},
                ensure_ascii=False,
                indent=2,
            ),
        }
    except Exception as exc:
        import traceback
        print(f"HATA DETAYI:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Görev 1 hatası: {exc}")

@app.post("/api/v1/gorev2")
def sadece_gorev2(istek: Gorev2Istek):
    """Yalnızca Görev 2 ajanını çalıştırır ve sonucu döndürür."""
    try:
        girdi = dict(istek.gorev1_ciktisi)
        ek_bilgi = istek.ek_bilgi
        if ek_bilgi:
            girdi["sistem_mesaji"] = f"Eksik bilgi geldi, artık üst yazı yazabilirsin. Gelen bilgi: {ek_bilgi}"
            if "eksik_bilgiler" in girdi:
                girdi["eksik_bilgiler"] = []
        sonuc = calistir_gorev2(girdi)
        return {"gorev2_ciktisi": sonuc.model_dump(mode="json")}
    except Exception as exc:
        import traceback
        print(f"HATA DETAYI:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Görev 2 hatası: {exc}")

# ------------------------------------------------------------------
# Eski tam pipeline endpoint (LangGraph): her ikisini de çalıştırır
# ------------------------------------------------------------------

@app.post("/api/v1/evrak-isle")
def evrak_isle(istek: EvrakIsleIstek):
    try:
        baslangic_durumu = {
            "ham_metin": istek.ham_metin,
            "gorev1_ciktisi": istek.gorev1_ciktisi,
            "ek_bilgi": istek.ek_bilgi
        }
        baslangic_durumu = {k: v for k, v in baslangic_durumu.items() if v is not None}
        sonuc_state = ajan_uygulamasi.invoke(cast(Any, baslangic_durumu))
        return sonuc_state
    except Exception as exc:
        import traceback
        hata_detayi = traceback.format_exc()
        print(f"HATA DETAYI:\n{hata_detayi}")
        raise HTTPException(status_code=500, detail=f"Ajan akışı sırasında hata: {exc}")
