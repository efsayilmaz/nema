import json
import re

from evren_client import validate_response_content


MEVZUAT_AJANI_PROMPT = """
Sen yalnızca Mevzuat ve Eksik Bilgi Ajanısın. Verilen RAG bağlamındaki
mevzuatı kullanarak ilgili mevzuatı ve eksik bilgileri belirle. Kanun veya
süre uydurma; süre alanını sen üretme, süre kod tarafından lookup ile
hesaplanacaktır. Her eksik bilgiyi, tespit edilen evrak türü ve önerilen
mevzuata göre ayrı ayrı değerlendir. Bir bilginin zorunlu olduğunu yalnızca
RAG bağlamındaki açık mevzuat maddesine dayanarak belirt; madde yoksa zorunlu
olarak sınıflandırma. Zorunlu olmayan eksiklikler için, ilgili maddenin
sonradan tamamlamaya izin verdiğini açıkça belirt. Yalnızca JSON döndür:
{
    "ilgili_mevzuat_onerisi":[],
    "eksik_bilgiler":[],
    "isleme_devam_edilebilirlik_durumu": {
        "zorunlu_eksikler": [],
        "zorunlu_olmayan_eksikler": []
    }
}
Her değerlendirme nesnesi şu alanları içermelidir: "bilgi",
"mevzuat_maddesi", "sonuc". Değerlendirme nesnesindeki "bilgi", eksik
bilgiler listesindeki ifadeyle aynı olmalıdır. Eksik bilgi yoksa iki listeyi
boş döndür.
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
