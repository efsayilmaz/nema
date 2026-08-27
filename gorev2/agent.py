import os
from typing import Union, Optional

from evren_client import get_evren_client
from pydantic import BaseModel

from gorev2.schemas import (
    Gorev2CiktiSemasi,
    Gorev1CiktiSemasi,
    AksiyonDurumu
)
from gorev2.yonlendirme_taslak_ajani import (
    calistir_yonlendirme_taslak_ajani,
    _format_resmi_yazi,
    tr_upper,
    duzelt_turkce_buyuk_harf,
    append_direction_suffix,
    determine_arz_rica,
    sanitize_arz_rica,
    dogrula_kimlik_ve_vergi_no,
    _normalize_input
)
from gorev2.kullanici_iletisim_ajani import (
    calistir_kullanici_iletisim_ajani
)

__all__ = [
    "calistir_gorev2",
    "tr_upper",
    "duzelt_turkce_buyuk_harf",
    "append_direction_suffix",
    "determine_arz_rica",
    "sanitize_arz_rica",
    "dogrula_kimlik_ve_vergi_no",
    "_format_resmi_yazi",
    "_normalize_input"
]


def calistir_gorev2(
    girdi_verisi: Union[dict, str, BaseModel, Gorev1CiktiSemasi],
    api_key: Optional[str] = None,
    model_name: str = "qwen/qwen3.6-27b"
) -> Gorev2CiktiSemasi:
    """
    Görev 1 analiz çıktısını alarak, iki alt ajanı sırayla çağırır ve
    birleştirilmiş Görev 2 resmî yazı taslaklama ve yönlendirme çıktısını üretir.

    Args:
        girdi_verisi: Görev 1 analiz çıktısı (dict, JSON string veya Gorev1CiktiSemasi).
        api_key: Groq API Anahtarı.
        model_name: Kullanılacak model (Varsayılan: "qwen/qwen3.6-27b").

    Returns:
        Gorev2CiktiSemasi: Görev 2 standart Pydantic çıktı nesnesi.
    """
    if api_key:
        os.environ["EVREN_API_KEY"] = api_key
        
    client = get_evren_client()
    selected_model = model_name or os.getenv("EVREN_MODEL", "llm-fast")

    girdi_dict = {}
    if isinstance(girdi_verisi, BaseModel):
        girdi_dict = girdi_verisi.model_dump()
    elif isinstance(girdi_verisi, dict):
        girdi_dict = girdi_verisi
    elif isinstance(girdi_verisi, str):
        try:
            import json
            girdi_dict = json.loads(girdi_verisi)
        except Exception:
            girdi_dict = {}

    # 1. Yönlendirme ve ilk taslak üreten ajanı çalıştır
    taslak_yonlendirme = calistir_yonlendirme_taslak_ajani(client, selected_model, girdi_verisi)

    # 2. Kullanıcı iletişim ajanını çalıştır (eksik bilgi kontrolü ve mesaj üretimi)
    kullanici_iletisim = calistir_kullanici_iletisim_ajani(client, selected_model, girdi_verisi, taslak_yonlendirme.yonlendirme_karari)

    # 3. Sonuçları birleştir
    yonlendirme_karari = taslak_yonlendirme.yonlendirme_karari
    kullanici_bilgilendirme = kullanici_iletisim.kullanici_bilgilendirme

    # Eğer eksik bilgi varsa, kullanıcı iletişim ajanının resmi yazı taslağını kullan
    if (kullanici_bilgilendirme.sistem_aksiyon_durumu == AksiyonDurumu.KULLANICI_BEKLENIYOR 
            and kullanici_iletisim.resmi_yazi_taslagi is not None):
        resmi_yazi_taslagi = kullanici_iletisim.resmi_yazi_taslagi
    else:
        resmi_yazi_taslagi = taslak_yonlendirme.resmi_yazi_taslagi

    # Resmi yazı formatlama (şablon giydirme)
    resmi_yazi_taslagi.govde_metni = _format_resmi_yazi(
        resmi_yazi_taslagi,
        yonlendirme_karari,
        girdi_dict
    )

    return Gorev2CiktiSemasi(
        yonlendirme_karari=yonlendirme_karari,
        resmi_yazi_taslagi=resmi_yazi_taslagi,
        kullanici_bilgilendirme=kullanici_bilgilendirme
    )
