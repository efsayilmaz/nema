import json
import re

from evren_client import validate_response_content


OZETLEME_AJANI_PROMPT = """
Sen bir kamu kurumu evrak özetleme uzmanısın. Sana verilen resmi yazı veya
dilekçe metnini analiz et ve iki alan üret:
1. konu: Evrakın ne hakkında olduğunu anlatan tek cümlelik, 15-20 kelimeyi
geçmeyen özgün başlık. Başlık bölümünü veya metindeki cümleleri kopyalama.
2. kisa_ozet: Evrakın kimden/nereden geldiğini, temel talep veya şikayeti ve
istenen aksiyonu kendi cümlelerinle 2-4 cümlede anlat. Parafraz yap.
Konu ve özet içinde alıcı, gönderen adı, kurum adı, adres, iletişim bilgisi,
tarih, sayı/kayıt numarası veya antet/başlık bulunamaz. Tarihi özetleme.
Yalnızca JSON döndür: {"konu":"...","kisa_ozet":"..."}
"""


def calistir_ozetleme_ajani(
    client,
    model: str,
    evrak_metni: str,
    duzeltme_istemi: bool = False,
) -> dict:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": OZETLEME_AJANI_PROMPT},
            {
                "role": "user",
                "content": (
                    f"HAM EVRAK:\n{evrak_metni}\n\n"
                    + (
                        "Önceki konu veya özet kuralı ihlal etti. İki alanı da SIFIRDAN YAZ: "
                        "konu tek özgün başlık, kisa_ozet 2-4 cümlelik parafraz olsun; "
                        "alıcı, gönderen, kurum, tarih, sayı, adres, iletişim veya antet kullanma."
                        if duzeltme_istemi
                        else "Yalnızca konu ve kisa_ozet alanlarını üret."
                    )
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
        raise ValueError("Özetleme ajanı geçerli JSON üretmedi.") from exc
    if not isinstance(sonuc, dict):
        raise ValueError("Özetleme ajanı nesne biçiminde JSON üretmedi.")
    return sonuc
