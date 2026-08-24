from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from langgraph_akis import ajan_uygulamasi

# FastAPI uygulamasını başlatıyoruz
app = FastAPI(
    title="Yapay Zeka Dil Ajanları API",
    description="Kamu Evrak ve Yazışma Süreçleri için Akıllı Agent Destek Sistemi",
    version="1.0.0"
)

# ---------------------------------------------------------
# 1. İstek (Request) Şeması
# Streamlit'ten veya OCR'dan API'ye gelecek verinin yapısı
# ---------------------------------------------------------
class EvrakIstegi(BaseModel):
    ham_metin: str

# ---------------------------------------------------------
# 2. Sahte (Mock) Veritabanı
# LLM entegrasyonu yapılana kadar kullanılacak test verisi
# ---------------------------------------------------------
MOCK_GOREV1_CIKTISI = {
    "evrak_meta": {"evrak_turu": "Dilekçe", "konu": "Aydınlatma Arızası"},
    "gonderen_bilgileri": {"ad_soyad": "Ahmet Yılmaz"},
    "icerik_analizi": {"kisa_ozet": "Direkler çalışmıyor, onarım talebi."},
    "hukuki_ve_surec_analizi": {"eksik_bilgiler": ["TCKN", "Tarih"]}
}

MOCK_GOREV2_CIKTISI = {
    "yonlendirme_karari": {"geregi_icin_yonlendirilecek_birim": "Fen İşleri Daire Başkanlığı"},
    "resmi_yazi_taslagi": {"yazi_turu": "Eksik Belge Talep Yazısı", "taslak": "Sayın Yılmaz, TCKN eksiktir..."},
    "kullanici_bilgilendirme": {"mesaj": "Talebiniz alındı ancak kimlik bilginiz eksik."}
}

# ---------------------------------------------------------
# 3. Uç Noktalar (Endpoints)
# ---------------------------------------------------------

@app.get("/")
def health_check():
    """Sistemin ayakta olup olmadığını kontrol eden basit bir uç nokta."""
    return {"status": "ok", "mesaj": "Agent Sistemi Aktif"}

@app.post("/api/v1/evrak-isle")
def evrak_isle(istek: EvrakIstegi):
    # LangGraph akışını tetikliyoruz!
    baslangic_durumu = {"ham_metin": istek.ham_metin}
    
    # Ajan zinciri çalışır ve sonucu döner
    sonuc = ajan_uygulamasi.invoke(baslangic_durumu)
    
    return {
        "durum": "basarili",
        "sonuclar": {
            "gorev1_analizi": sonuc["gorev1_ciktisi"],
            "gorev2_üretimi": sonuc["gorev2_ciktisi"]
        }
    }

if __name__ == "__main__":
    # Sunucuyu yerel ortamda 8000 portunda çalıştır
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)