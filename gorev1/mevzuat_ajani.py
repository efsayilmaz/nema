import json
import re

from evren_client import validate_response_content


MEVZUAT_AJANI_PROMPT = """
Sen kamu idaresinde görev yapan kıdemli Mevzuat, Hukuk ve Eksik Bilgi Değerlendirme Ajanısın.
GÖREVİN:
Verilen evrak metnini ve RAG mevzuat bağlamını inceleyerek;
1. İlgili mevzuatları (`ilgili_mevzuat_onerisi`) belirlemek,
2. Evrakta mevzuata göre eksik olan unsurları (`eksik_bilgiler`) tespit etmek,
3. Eksik bilgileri MEVZUATTAKİ AĞIRLIĞINA GÖRE DERECELENDİRMEK ve resmi yazı taslağı oluşturulup oluşturulamayacağını (`isleme_devam_edilebilirlik_durumu`) karara bağlamaktır.

MEVZUATA GÖRE DERECELENDİRME VE İŞLEME DEVAM KURALLARI:
1. KRİTİK / ENGELLEYİCİ EKSİKLER (`zorunlu_eksikler`):
   - YALNIZCA İKİ DURUMDA GEÇERLİDİR:
     a) Başvuru sahibinin kimliği (ad-soyad veya kurum unvanı) HİÇ YOKSA (kime resmi yazı yazılacağı bilinemez),
     b) Başvurunun somut konusu/talebi HİÇ ANLAŞILMIYORSA.
   - Bu iki durum dışında İMZA, TARİH, ADRES, BELGE gibi eksiklikleri KESİNLİKLE zorunlu_eksikler'e KOYMAYIN.
   - Bu durumda `taslak_olusturulabilir_mi: false`, `derece: "Kritik (Taslak Üretilemez / İşleme Alınamaz)"` olmalıdır.

2. TAMAMLANABİLİR / İDARİ EKSİKLER (`tamamlanabilir_eksikler`):
   - Başvuru sahibi (ad-soyad) ve talep bellidir; ancak İMZA, EVRAK TARİHİ, KAYIT NO, TELEFON, E-POSTA, İKAMETGÂH ADRESİ veya EK BELGELER eksiktir.
   - İdare bu durumda başvuruyu reddetmez; başvuru sahibine resmi bir "Eksik Bilgi/Belge Talebi" yazısı yazarak eksikliklerin tamamlanmasını ister.
   - Dolayısıyla KESİNLİKLE resmi yazı taslağı oluşturulabilir: `taslak_olusturulabilir_mi: true`, `derece: "Tamamlanabilir (Eksik Belge Talebi Yazılabilir)"` olmalıdır.

3. EKSİKSİZ DURUM:
   - Hiçbir yasal veya idari eksiklik yoksa: `taslak_olusturulabilir_mi: true`, `derece: "Eksiksiz (Doğrudan Üst Yazı Yazılabilir)"` olmalıdır.

DÖNDÜRÜLECEK JSON ŞEMASI:
{
    "ilgili_mevzuat_onerisi": ["3071 Sayılı Dilekçe Hakkının Kullanılmasına Dair Kanun", ...],
    "eksik_bilgiler": ["Dilekçe sahibinin imzası eksiktir (3071 Sayılı Kanun Madde 4)", ...],
    "isleme_devam_edilebilirlik_durumu": {
        "taslak_olusturulabilir_mi": true,
        "derece": "Tamamlanabilir (Eksik Belge Talebi Yazılabilir)",
        "gerekce": "Başvuru sahibinin adı-soyadı ve konusu açık olmakla birlikte imza eksikliği bulunduğundan 3071 sayılı Kanun kapsamında Eksik Bilgi/Belge Talebi yazısı düzenlenebilir.",
        "zorunlu_eksikler": [],
        "tamamlanabilir_eksikler": [
            {
                "bilgi": "Dilekçe Sahibinin İmzası",
                "mevzuat_maddesi": "3071 Sayılı Kanun Madde 4",
                "sonuc": "3071 sayılı Kanun kapsamında eksik bilgi talebi resmi yazısı düzenlenerek başvuru sahibinden imza tamamlanması istenir."
            }
        ]
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
