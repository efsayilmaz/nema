from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from gorev1 import calistir_gorev1
from gorev2.agent import calistir_gorev2

app = FastAPI(title="Kamu Evrak Agent Backend - TEKNOFEST")

# Streamlit farklı bir portta/origin'de çalışacağı için CORS'u açıyoruz.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Gorev1Istek(BaseModel):
    evrak_metni: str


class Gorev2Istek(BaseModel):
    analiz_sonucu: Dict[str, Any]
    ek_bilgi: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/gorev1")
def gorev1(istek: Gorev1Istek):
    try:
        sonuc = calistir_gorev1(istek.evrak_metni)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Görev 1 ajanı hata verdi: {exc}")
    return sonuc.model_dump(mode="json")


@app.post("/api/gorev2")
def gorev2(istek: Gorev2Istek):
    girdi = dict(istek.analiz_sonucu)

    # calistir_gorev2 ayrı bir "ek_bilgi" parametresi almıyor. Kullanıcı
    # eksik bilgiyi doldurmuşsa, bunu kısa özete ekleyip eksikler listesini
    # temizliyoruz ki ajan "eksik bilgi talebi" yerine normal cevap/üst yazı üretsin.
    if istek.ek_bilgi:
        girdi["eksik_bilgiler"] = []
        onceki_ozet = girdi.get("kisa_ozet", "") or ""
        girdi["kisa_ozet"] = (
            f"{onceki_ozet}\n\n[Kullanıcının sağladığı ek bilgi: {istek.ek_bilgi}]"
        )

    try:
        sonuc = calistir_gorev2(girdi)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Görev 2 ajanı hata verdi: {exc}")
    return sonuc.model_dump(mode="json")
