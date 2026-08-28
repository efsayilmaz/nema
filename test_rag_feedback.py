import sys; sys.path.insert(0, '.')
from evren_client import get_evren_client
from gorev2.yonlendirme_taslak_ajani import calistir_yonlendirme_taslak_ajani

girdi = {
    'evrak_turu': 'Genel İdari',
    'kisa_ozet': 'Belediye sınırları içindeki parkta kırık salıncak onarımı talebi.',
    'ilgili_mevzuat_onerisi': ['5393 Sayılı Kanun'],
    'konu': 'Park Onarım Talebi'
}

client = get_evren_client()
print('Ajan cagiriliyor...')
cikti = calistir_yonlendirme_taslak_ajani(client, 'llm-fast', girdi)
print('\n=== CIKTI ===')
print('Kullanilan Referanslar (ID listesi):', cikti.kullanilan_referanslar)
print('Yazi Turu:', cikti.resmi_yazi_taslagi.yazi_turu)
print('Govde:\n', cikti.resmi_yazi_taslagi.govde_metni)

from teknofest_agent_app.utils.arsiv_db import arsiv_verilerini_getir
kayitlar = arsiv_verilerini_getir()
for ref in cikti.kullanilan_referanslar:
    for k in kayitlar:
        if k['id'] == ref:
            print(f"Sayac guncellendi: {ref} -> {k.get('referans_sayaci')}")
