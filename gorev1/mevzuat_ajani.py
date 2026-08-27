import json
import re

from evren_client import validate_response_content


MEVZUAT_AJANI_PROMPT = """
Sen kamu idaresinde görev yapan kıdemli Mevzuat, Hukuk ve Eksik Bilgi Değerlendirme Ajanısın.
GÖREVİN:
Verilen evrak metnini ve RAG mevzuat bağlamını inceleyerek;
1. İlgili mevzuatları (`ilgili_mevzuat_onerisi`) belirlemek,
2. Evrakta mevzuata göre GERÇEKTEN eksik olan unsurları (`eksik_bilgiler`) tespit etmek,
3. Eksik bilgileri MEVZUATTAKİ AĞIRLIĞINA GÖRE DERECELENDİRMEK ve resmi yazı taslağı oluşturulup oluşturulamayacağını (`isleme_devam_edilebilirlik_durumu`) karara bağlamaktır.

KRİTİK KURALLAR (ASLA İHLAL EDİLEMEZ):
1. İMZA VE METİN KARİNESİ (ÇOK ÖNEMLİ):
   - Dijital metin veya OCR ile okunan evraklarda fiziki ıslak imza metne dökülemez. Evrakta başvuru sahibinin veya kurum yetkilisinin Adı-Soyadı / Unvanı yer alıyorsa evrak İMZALI kabul edilir.
   - Evrakta adı-soyadı yazılı olan standart dilekçe veya yazılarda KESİNLİKLE "imza eksiktir" ÇIKARIMI YAPMAYIN.
   - "İmza eksiktir" çıkarımı YALNIZCA metinde açıkça "imzasızdır", "imza bulunmamaktadır" gibi bir not düşüldüğünde yapılabilir.

2. DERECELENDİRME VE İŞLEME DEVAM KURALLARI:
   - 🔴 KRİTİK / ENGELLEYİCİ EKSİKLER (`zorunlu_eksikler`):
     Yalnızca başvuru sahibinin kimliği (ad-soyad / unvan) HİÇ YOKSA veya somut talep/konu HİÇ ANLAŞILMIYORSA geçerlidir.
     Bu durumda `taslak_olusturulabilir_mi: false`, `derece: "Kritik (Taslak Üretilemez / İşleme Alınamaz)"` olur.

   - 🟡 TAMAMLANABİLİR / İDARİ EKSİKLER (`tamamlanabilir_eksikler`):
     Başvuru sahibi ve talep bellidir; ancak itiraz edilen sınavın tarihi/kodu, şikayet edilen yerin açık adresi veya zorunlu ek belge gibi unsurlar eksiktir.
     Bu durumda `taslak_olusturulabilir_mi: true`, `derece: "Tamamlanabilir (Eksik Belge Talebi Yazılabilir)"` olur.

   - 🟢 EKSİKSİZ DURUM:
     Evrakta başvuru sahibi, konu, tarih ve gerekli bilgiler mevcutsa hiçbir eksik bilgi üretmeyin (`eksik_bilgiler: []`).
     Bu durumda `taslak_olusturulabilir_mi: true`, `derece: "Eksiksiz (Doğrudan Üst Yazı Yazılabilir)"` olur.

DÖNDÜRÜLECEK JSON ŞEMASI:
{
    "ilgili_mevzuat_onerisi": ["3071 Sayılı Dilekçe Hakkının Kullanılmasına Dair Kanun", ...],
    "eksik_bilgiler": [],
    "isleme_devam_edilebilirlik_durumu": {
        "taslak_olusturulabilir_mi": true,
        "derece": "Eksiksiz (Doğrudan Üst Yazı Yazılabilir)",
        "gerekce": "Evrak yasal ve idari unsurları tam taşımaktadır. Doğrudan yetkili birime üst yazı ve sevk kararı oluşturulabilir.",
        "zorunlu_eksikler": [],
        "tamamlanabilir_eksikler": []
    }
}
YALNIZCA geçerli bir JSON nesnesi döndür. Markdown veya açıklama yazma.
"""


def calistir_mevzuat_ajani(
    client,
    model: str,
    evrak_metni: str,
    mevzuat_baglami,
) -> dict:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": MEVZUAT_AJANI_PROMPT},
            {
                "role": "user",
                "content": (
                    f"HAM EVRAK:\n{evrak_metni}\n\n"
                    f"RAG mevzuat bağlamı (tek kaynak):\n{mevzuat_baglami}"
                ),
            },
        ],
        temperature=0.1,
    )
    raw_text = re.sub(r"<think>.*?</think>", "", validate_response_content(response), flags=re.DOTALL).strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text, flags=re.IGNORECASE).strip()
    try:
        sonuc = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Mevzuat ajanı geçerli JSON üretmedi.") from exc
    if not isinstance(sonuc, dict):
        raise ValueError("Mevzuat ajanı nesne biçiminde JSON üretmedi.")
    return sonuc
