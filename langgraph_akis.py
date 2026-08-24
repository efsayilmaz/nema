from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, START, END

# ---------------------------------------------------------
# 1. State (Durum) Tanımı
# Ajanlar arasında taşınacak verilerin tutulduğu depo
# ---------------------------------------------------------
class EvrakState(TypedDict):
    ham_metin: str
    gorev1_ciktisi: Dict[str, Any]
    gorev2_ciktisi: Dict[str, Any]

# ---------------------------------------------------------
# 2. Mock Düğüm (Node) Fonksiyonları
# Gerçek LLM kodları yazılana kadar sahte veri dönerler
# ---------------------------------------------------------
def gorev1_ajani(state: EvrakState):
    print("-> Görev 1 Ajanı çalışıyor... (Mock Veri Döndürülüyor)")
    
    # Arkadaşlarınızla hazırladığınız GÖREV 1 Sokak Köpekleri Çıktısı
    mock_gorev1 = {
      "evrak_turu": "Şikayet / İhbar",
      "konu": "Başıboş Sokak Köpekleri Şikayeti",
      "eksik_bilgiler": [
        "Evrak Tarihi",
        "Başvuru Sahibinin Adı ve Soyadı",
        "T.C. Kimlik Numarası",
        "İletişim Bilgisi (Telefon/E-posta)"
      ],
      "ilgili_mevzuat_onerisi": [
        "5199 Sayılı Hayvanları Koruma Kanunu",
        "5393 Sayılı Belediye Kanunu"
      ]
      # İhtiyaca göre diğer alanları da buraya ekleyebilirsin
    }
    return {"gorev1_ciktisi": mock_gorev1}

def gorev2_ajani(state: EvrakState):
    print("-> Görev 2 Ajanı çalışıyor... (Mock Veri Döndürülüyor)")
    
    # Arkadaşlarınızla hazırladığınız GÖREV 2 Sokak Köpekleri Çıktısı
    mock_gorev2 = {
      "yonlendirme_karari": {
        "geregi_icin_yonlendirilecek_birim": "Veteriner İşleri Müdürlüğü",
      },
      "resmi_yazi_taslagi": {
        "yazi_turu": "Eksik Bilge/Belge Talebi",
        "govde_metni": "İlgide kayıtlı başvurunuz incelenmiştir. Yeşiltepe Mahallesi Gül Sokak'taki başıboş köpeklerle ilgili... bilgilerinizi tamamlamanız rica olunur."
      },
      "kullanici_bilgilendirme": {
        "kullaniciya_gosterilecek_mesaj": "Şikayetiniz sistemimize ulaşmış olup... lütfen eksik olan bilgilerinizi güncelleyiniz.",
        "sistem_aksiyon_durumu": "Kullanıcı Bekleniyor"
      }
    }
    return {"gorev2_ciktisi": mock_gorev2}

# ---------------------------------------------------------
# 3. LangGraph Akışını (State Machine) Kurma
# ---------------------------------------------------------
graph_builder = StateGraph(EvrakState)

# Düğümleri ağa ekle
graph_builder.add_node("gorev_1_dugumu", gorev1_ajani)
graph_builder.add_node("gorev_2_dugumu", gorev2_ajani)

# Akış yönünü (Edge) belirle: BAŞLANGIÇ -> Görev 1 -> Görev 2 -> BİTİŞ
graph_builder.add_edge(START, "gorev_1_dugumu")
graph_builder.add_edge("gorev_1_dugumu", "gorev_2_dugumu")
graph_builder.add_edge("gorev_2_dugumu", END)

# Grafı derleyerek çalıştırılabilir bir uygulamaya dönüştür
ajan_uygulamasi = graph_builder.compile()