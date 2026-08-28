import sys; sys.path.insert(0, '.')
from evren_client import get_evren_client
from gorev1.siniflandirma_ajani import calistir_siniflandirma_ajani
from gorev2.yonlendirme_taslak_ajani import calistir_yonlendirme_taslak_ajani
import json

evrak_metni = """
Konu: Devlet Hastanesi Kardiyoloji Bölümündeki cihaz arızası hakkında şikayet.
Geçen hafta kardiyoloji bölümüne gittiğimde EKG cihazının bozuk olduğu ve 
muayene olamayacağım söylendi. Sağlık hakkımın gasp edildiğini düşünüyorum. 
Gereğinin yapılmasını arz ederim.
Ahmet Yılmaz.
"""

client = get_evren_client()

print("--- 1. GOREV 1 SINIFLANDIRMA AJANI ÇALIŞIYOR ---")
siniflandirma_cikti = calistir_siniflandirma_ajani(client, 'llm-fast', evrak_metni)
print(f"Tespit Edilen Evrak Turu: {siniflandirma_cikti.get('evrak_turu')}")
print(f"Tespit Edilen Sektor: {siniflandirma_cikti.get('sektor')}")
print(f"Kisa Ozet: {siniflandirma_cikti.get('konu')}")

# Gorev 2 icin mock payload hazirlayalim
girdi = {
    'evrak_turu': siniflandirma_cikti.get('evrak_turu', 'Şikayet'),
    'sektor': siniflandirma_cikti.get('sektor', 'sağlık'),
    'kisa_ozet': siniflandirma_cikti.get('konu', ''),
    'ilgili_mevzuat_onerisi': ['Sağlık Hizmetleri Temel Kanunu'],
    'konu': siniflandirma_cikti.get('konu', '')
}

print("\n--- 2. GOREV 2 TASLAK AJANI ÇALIŞIYOR ---")
cikti = calistir_yonlendirme_taslak_ajani(client, 'llm-fast', girdi)
print('\n=== CIKTI ===')
print('Kullanilan Referanslar (ID listesi):', cikti.kullanilan_referanslar)
if len(cikti.kullanilan_referanslar) == 0:
    print("(Not: RAG havuzunda bu sektorde kayit olabilir ancak 'legacy' ise veya 2 insan onayi yoksa filtreden gecemez ve referans alinmaz.)")
