from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from gorev1.agent import calistir_gorev1
from gorev2.agent import calistir_gorev2
from langgraph_akis import ajan_uygulamasi

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

@app.post("/api/v1/gorev1")
def sadece_gorev1(istek: Gorev1Istek):
    """Yalnızca Görev 1 ajanını çalıştırır ve sonucu döndürür."""
    try:
        sonuc = calistir_gorev1(istek.ham_metin)
        return {"gorev1_ciktisi": sonuc.model_dump(mode="json")}
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
        sonuc_state = ajan_uygulamasi.invoke(baslangic_durumu)
        return sonuc_state
    except Exception as exc:
        import traceback
        hata_detayi = traceback.format_exc()
        print(f"HATA DETAYI:\n{hata_detayi}")
        raise HTTPException(status_code=500, detail=f"Ajan akışı sırasında hata: {exc}")
