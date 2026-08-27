import os
import requests
import warnings
from openai import OpenAI
from pathlib import Path

# Singleton istemci ve dogrulama durumu
_EVREN_CLIENT = None
_MODELS_VALIDATED = False

EVREN_BASE_URL = "https://evren-llmapi.ssyz.org.tr/v1"

def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for satir in path.read_text(encoding="utf-8").splitlines():
        satir = satir.strip()
        if not satir or satir.startswith("#") or "=" not in satir:
            continue
        anahtar, deger = satir.split("=", 1)
        anahtar = anahtar.strip()
        deger = deger.strip().strip('"').strip("'")
        if anahtar and not os.getenv(anahtar):
            os.environ[anahtar] = deger

def _resolve_api_key() -> str:
    api_key = os.getenv("EVREN_API_KEY")
    if api_key:
        return api_key

    proje_klasoru = Path(__file__).resolve().parent
    for dosya_adi in (".env", ".env.example"):
        _load_env_file(proje_klasoru / dosya_adi)

    api_key = os.getenv("EVREN_API_KEY")
    if not api_key:
        raise ValueError("EVREN_API_KEY bulunamadı! Lütfen ortam değişkenlerine ekleyin.")
    return api_key

def _validate_models(api_key: str):
    """
    Uygulama başlangıcında modelleri doğrular.
    Yanlış model isimleri hata vermeden sessizce llm-fast'e yönlendiği için bu kritik.
    """
    global _MODELS_VALIDATED
    if _MODELS_VALIDATED:
        return
    
    try:
        response = requests.get(
            f"{EVREN_BASE_URL}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        response.raise_for_status()
        models_data = response.json()
        available_models = [m["id"] for m in models_data.get("data", [])]
        
        # Beklenen temel modellerin varlığını kontrol et
        expected = ["llm-fast", "llm-large", "bge-m3-embed"]
        for exp in expected:
            if exp not in available_models:
                warnings.warn(f"Uyarı: Beklenen model '{exp}' EVREN servisinde bulunamadı. "
                              f"Mevcut modeller: {available_models}")
                
        _MODELS_VALIDATED = True
        print("EVREN API modelleri başarıyla doğrulandı.")
    except Exception as e:
        warnings.warn(f"EVREN API model doğrulaması yapılamadı: {e}")
        # Hata fırlatmıyoruz, servisin anlık kapalı olma ihtimaline karşı çalışmaya devam edebiliriz.

def get_evren_client() -> OpenAI:
    """
    Timeout süresi 1800 sn (EVREN sınırı) olarak ayarlanmış OpenAI istemcisi döndürür.
    """
    global _EVREN_CLIENT
    if _EVREN_CLIENT is None:
        api_key = _resolve_api_key()
        _validate_models(api_key)
        
        _EVREN_CLIENT = OpenAI(
            api_key=api_key,
            base_url=EVREN_BASE_URL,
            timeout=1800.0  # EVREN tavan sınırı
        )
    return _EVREN_CLIENT

def validate_response_content(response) -> str:
    """
    EVREN servisinde 'enable_thinking' açıkken veya max_tokens aşıldığında
    finish_reason="length" ile sessizce boş content dönebilir.
    Bu durumu yakalayıp düzgün bir hata fırlatır.
    """
    choice = response.choices[0]
    content = choice.message.content
    
    if choice.finish_reason == "length":
        raise ValueError("Model çıktısı uzunluk sınırına (length) takıldı. max_tokens değerini artırın.")
    
    if not content or not content.strip():
        raise ValueError("Model boş içerik (content) döndürdü. finish_reason: " + str(choice.finish_reason))
        
    return content.strip()
