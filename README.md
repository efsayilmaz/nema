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

Bu komut tek evrakı önce Görev 1, sonra Görev 2 aşamasından geçirir ve iki sonucu
PowerShell ekranında gösterir. Parametre verilmezse masaüstündeki demo dosyası okunur.
Başka bir dosya kullanmak için:

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

Birden fazla evrakı analiz edip sonuçları dosyaya kaydetmek için:

```powershell
python batch_main.py --dosya "$HOME\OneDrive\Desktop\string.txt"
```

Çıktı, kaynak dosyanın yanına şu adla kaydedilir:

```text
string_gorev1_gorev2_sonuclari.json
```

Dosyada her evrak için `gorev1_ciktisi` ve `gorev2_ciktisi` alanları bulunur.

Görev 2 ajanına aktarım:

```python
from gorev1 import calistir_gorev1
from gorev2.agent import calistir_gorev2

gorev1_sonucu = calistir_gorev1(metin)
gorev2_sonucu = calistir_gorev2(gorev1_sonucu)
```
