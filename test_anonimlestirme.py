from evren_client import get_evren_client
from gorev2.arsiv_ajani import hibrit_anonimlestirme

evren_client = get_evren_client()

# Sağlık/Özel Nitelikli Veri ve Adres kombinasyonunu içeren zorlu test metni
TEST_METNI = """
Sayı  : E-71073638-950.01.04-8203
Tarih : 28.08.2026
KONU  : Evde sağlık hizmeti ve elektrik kesintisi nedeniyle sağlık riski talebi hakkında
İlgi  : 25.08.2026 tarihli ve Fatma Yılmaz imzalı dilekçe

İLGİLİ MAKAMA
Kadıköy Caferağa Mahallesi Moda Caddesi No:14 adresinde ikamet eden 78 yaşındaki 
KOAH hastası Fatma Yılmaz, bağlı bulunduğu oksijen konsantratörünün mahalledeki 
planlı elektrik kesintileri nedeniyle durduğunu, bu süreçte kan satürasyon değerinin 
85'e kadar düştüğünü beyan ederek 26.08.2026 tarihinde hastaneye sevk edilmiştir.

Konunun ivedilikle değerlendirilerek 0532 123 45 67 numaralı telefondan hastaya
veya yakınına bilgi verilmesi hususunu arz ederim.

İmza:
Dr. Ahmet Çelik
İl Sağlık Müdürlüğü
"""

def run_test():
    print("="*60)
    print(" (a) KULLANICIYA/KURUMA GİDEN GERÇEK TASLAK (NİHAİ ÇIKTI)")
    print(" (Maskeleme YOK - Kurum bu belgeyle işlem yapacak)")
    print("="*60)
    print(TEST_METNI.strip())
    print("\n\n")
    
    print(">>> ARKA PLANDA QDRANT'A KAYIT SÜRECİ (2 AŞAMALI DENETİM) BAŞLADI <<<\n")
    anonim_metin, durum, rapor = hibrit_anonimlestirme(evren_client, TEST_METNI)
    
    print("="*60)
    print(" (b) ARŞİVE (QDRANT'A) GİDEN KOPYA")
    print(" (Sadece Vatandaş Verisi Maskeli - İdari Veriler Açık)")
    print("="*60)
    print(anonim_metin.strip())
    print("="*60)
    
    print("\n[DENETİM RAPORU]")
    print(f"Sonuç Durumu: {durum}")
    print(f"Regex Katmanı Temiz mi? {rapor['regex_clean']}")
    print(f"Bulunan Varlıklar: {rapor['stage1_detected']}")

if __name__ == "__main__":
    run_test()
