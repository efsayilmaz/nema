# Evrak Analiz Ajanı

Groq API ve Pydantic structured output kullanarak tek bir Türkçe evrakı analiz eder.

## Kurulum

```powershell
cd "$HOME\OneDrive\Desktop\nema"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:GROQ_API_KEY="yeni_groq_api_anahtariniz"
$env:GROQ_MODEL="qwen/qwen3.6-27b"
```

Yerel demo için `string.txt` dosyası şu konumda olabilir:

```text
$HOME\OneDrive\Desktop\string.txt
```

## Çalıştırma

```powershell
python main.py
```

Parametre verilmeden çalıştırıldığında masaüstündeki demo dosyası okunur. Başka bir
dosya kullanmak için:

```powershell
python main.py --file "C:\ornekler\dilekce.txt"
```

Chatbot entegrasyonunda masaüstündeki dosyaya ihtiyaç yoktur. Kullanıcının gönderdiği
tek metin doğrudan Görev 1 fonksiyonuna aktarılır:

```python
from gorev1 import calistir_gorev1

gorev1_sonucu = calistir_gorev1(kullanici_mesaji)
gorev1_verisi = gorev1_sonucu.model_dump()
```

İsterseniz komut satırından da standart giriş kullanılabilir:

```powershell
Get-Content "C:\ornekler\dilekce.txt" | python main.py
```

Görev 2 ajanına aktarım:

```python
from gorev1 import calistir_gorev1
from gorev2.agent import calistir_gorev2

gorev1_sonucu = calistir_gorev1(metin)
gorev2_sonucu = calistir_gorev2(gorev1_sonucu)
```
