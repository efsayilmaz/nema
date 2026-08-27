from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, START, END

from gorev1.agent import calistir_gorev1
from gorev2.agent import calistir_gorev2

# ---------------------------------------------------------
# 1. State (Durum) Tanımı
# Ajanlar arasında taşınacak verilerin tutulduğu depo
# ---------------------------------------------------------
class EvrakState(TypedDict, total=False):
    ham_metin: str
    gorev1_ciktisi: Dict[str, Any]
    gorev2_ciktisi: Dict[str, Any]
    ek_bilgi: str

# ---------------------------------------------------------
# 2. Düğüm (Node) Fonksiyonları
# ---------------------------------------------------------
def gorev1_ajani(state: EvrakState):
    print("-> Görev 1 Ajanı çalışıyor...")
    sonuc = calistir_gorev1(state["ham_metin"])
    return {"gorev1_ciktisi": sonuc.model_dump(mode="json")}

def gorev2_ajani(state: EvrakState):
    print("-> Görev 2 Ajanı çalışıyor...")
    girdi = state.get("gorev1_ciktisi", {})
    ek_bilgi = state.get("ek_bilgi")

    if ek_bilgi:
        girdi["sistem_mesaji"] = f"Eksik bilgi geldi, artık üst yazı yazabilirsin. Gelen bilgi: {ek_bilgi}"
        if "eksik_bilgiler" in girdi:
            girdi["eksik_bilgiler"] = []

    sonuc = calistir_gorev2(girdi)
    return {"gorev2_ciktisi": sonuc.model_dump(mode="json")}

def route_start(state: EvrakState):
    if state.get("gorev1_ciktisi"):
        return "gorev_2_dugumu"
    return "gorev_1_dugumu"

def check_gorev2_gecis_uygunlugu(state: EvrakState):
    """
    Mevzuata göre Görev 2'ye geçiş kontrolü:
    Eğer evrakta 3071 m.4/6 veya 4982 m.6 uyarınca kritik engelleyici eksiklik varsa
    ve ek_bilgi ile tamamlanmamışsa Görev 2'ye geçilmez, akış sonlandırılır.
    """
    g1 = state.get("gorev1_ciktisi", {})
    ek_bilgi = state.get("ek_bilgi")

    # Eğer kullanıcı ek bilgi girmişse devam edebilir
    if ek_bilgi and ek_bilgi.strip():
        return "gorev_2_dugumu"

    # Görev 1'den gelen taslak_olusturulabilir_mi kontrolü
    if g1.get("taslak_olusturulabilir_mi") is False:
        print("-> [Mevzuat Engeli] Kritik eksiklik nedeniyle resmi taslak üretilemez, Görev 2'ye geçilmiyor.")
        return END

    return "gorev_2_dugumu"

# ---------------------------------------------------------
# 3. LangGraph Akışını (State Machine) Kurma
# ---------------------------------------------------------
graph_builder = StateGraph(EvrakState)

# Düğümleri ağa ekle
graph_builder.add_node("gorev_1_dugumu", gorev1_ajani)
graph_builder.add_node("gorev_2_dugumu", gorev2_ajani)

# Akış yönünü (Edge) belirle
graph_builder.add_conditional_edges(START, route_start)
graph_builder.add_conditional_edges(
    "gorev_1_dugumu",
    check_gorev2_gecis_uygunlugu,
    {"gorev_2_dugumu": "gorev_2_dugumu", END: END}
)
graph_builder.add_edge("gorev_2_dugumu", END)

# Grafı derleyerek çalıştırılabilir bir uygulamaya dönüştür
ajan_uygulamasi = graph_builder.compile()