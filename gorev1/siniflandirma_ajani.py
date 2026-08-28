import json
import re

from evren_client import validate_response_content


SINIFLANDIRMA_AJANI_PROMPT = """
Sen yalnızca Sınıflandırma ve Bilgi Çıkarım Ajanısın. Evrak türünü belirle ve
metindeki önemli bilgi unsurlarını çıkar. Ayrıca, evrakın içeriğine bakarak 'sektor' 
alanını belirle (Seçenekler: sağlık, hukuk, savunma, eğitim, belediye, tüketici, bilgi, genel).
İçeriğinde belirli bir konu/sektör varsa kesinlikle ona ata, sadece hiçbir kategoriye
girmiyorsa 'genel' seç. Gönderen, tarih, sayı, kurum ve lokasyon gibi kimlik bilgilerini 
ayrı alanlara koy. Konu yalnızca evrakın niyetini ve gerekçesini anlatan yeni bir cümle olsun; 
başlık bilgilerini tekrar etme. Yalnızca JSON döndür ve şu alanları kullan:
{"evrak_turu":"...","sektor":"...","konu":"...","evrak_tarihi":null,
"sayi_veya_kayit_no":null,"gonderen":{"gonderen_tipi":"...",
"ad_soyad_veya_unvan":null,"kimlik_veya_vergi_no":null,
"iletisim_bilgisi":null},"varliklar":{"kurumlar":[],"lokasyonlar":[],
"tarihler":[]},"onemli_bilgi_unsurlari":[],"aciliyet_durumu":"Normal"}
"""


def calistir_siniflandirma_ajani(client, model: str, evrak_metni: str) -> dict:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SINIFLANDIRMA_AJANI_PROMPT},
            {"role": "user", "content": f"HAM EVRAK:\n{evrak_metni}"},
        ],
        temperature=0.1,
    )
    raw_text = re.sub(r"<think>.*?</think>", "", validate_response_content(response), flags=re.DOTALL).strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text, flags=re.IGNORECASE).strip()
    try:
        sonuc = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Sınıflandırma ajanı geçerli JSON üretmedi.") from exc
    if not isinstance(sonuc, dict):
        raise ValueError("Sınıflandırma ajanı nesne biçiminde JSON üretmedi.")
    return sonuc
