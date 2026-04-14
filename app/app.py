"""
app/app.py
Ponto de entrada do dashboard — orquestrador fino.

Rodar com:
    streamlit run app/app.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from app.auth import login_requerido, usuario_atual, is_admin, logout
from app.helpers import (
    MESES_FULL, MESES_NOMES,
    carregar_dados, aplicar_filtros,
    build_color_map, formatar_brl, formatar_mi,
)
from app.views import geral, secretaria, fornecedor, rankings, base_detalhada, admin


# -----------------------------------------------------------------
# render() — ponto de entrada chamado pelo Portal Central
# Não inclui set_page_config nem login_requerido (ambos ficam
# exclusivamente no bloco __main__ abaixo).
# -----------------------------------------------------------------
def render():
    """Renderiza o dashboard de Despesas. Chamado pelo Portal Central."""
    # Header
    usuario = usuario_atual()
    col_h1, col_h2 = st.columns([7, 1])
    with col_h1:
        st.title("🏛️ Despesas da Prefeitura")
    with col_h2:
        st.markdown(f"**{usuario.get('nome') or usuario.get('username')}**")
        if st.button("Sair", use_container_width=True):
            logout()

    # Carga de dados
    try:
        df_full = carregar_dados()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        st.stop()

    if df_full.empty:
        st.warning("Nenhum dado no banco. Execute: `python etl/run_etl.py`")
        st.stop()

    # Sidebar — Filtros
    st.sidebar.header("🔎 Filtros")

    anos_disp     = sorted(df_full["ano"].dropna().unique().astype(int).tolist())
    meses_disp    = sorted(df_full["mes"].dropna().unique().astype(int).tolist())
    secs_disp     = sorted(x for x in df_full["secretaria"].dropna().unique() if x.strip())
    recursos_disp = sorted(x for x in df_full["recurso"].dropna().unique() if x.strip())
    favs_disp     = sorted(x for x in df_full["favorecido"].dropna().unique() if x.strip())

    anos_sel     = st.sidebar.multiselect("Ano", anos_disp, default=anos_disp)
    meses_sel    = st.sidebar.multiselect(
        "Mês", meses_disp, default=[],
        format_func=lambda x: MESES_FULL.get(x, str(x)),
    )
    secs_sel     = st.sidebar.multiselect("Secretaria", secs_disp, default=[])
    recursos_sel = st.sidebar.multiselect("Recurso (fonte)", recursos_disp, default=[])
    favs_sel     = st.sidebar.multiselect("Favorecido", favs_disp, default=[])
    busca        = st.sidebar.text_input("Buscar texto")

    base = aplicar_filtros(df_full, anos_sel, meses_sel, secs_sel, recursos_sel, favs_sel, busca)

    if base.empty:
        st.warning("Nenhum dado com os filtros selecionados.")
        st.stop()

    # KPIs gerais
    total    = base["valor"].sum()
    qtd      = len(base)
    qtd_favs = base["favorecido"].nunique()
    media    = base["valor"].mean()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💰 Total gasto",        formatar_mi(total))
    k2.metric("📋 Lançamentos",        f"{qtd:,}".replace(",", "."))
    k3.metric("🏢 Favorecidos únicos", f"{qtd_favs:,}".replace(",", "."))
    k4.metric("📊 Valor médio",        formatar_brl(media))

    st.markdown("---")

    # Abas principais
    cores_map = build_color_map(df_full)

    tab_geral, tab_sec, tab_forn, tab_ranking, tab_detalhe, tab_admin = st.tabs([
        "📊 Visão Geral",
        "🏛️ Por Secretaria",
        "🏢 Por Fornecedor",
        "🏆 Rankings",
        "📋 Base Detalhada",
        "⚙️ Admin" if is_admin() else "⚙️ Admin (restrito)",
    ])

    with tab_geral:
        geral.render(base, cores_map)

    with tab_sec:
        secretaria.render(base, cores_map)

    with tab_forn:
        fornecedor.render(base)

    with tab_ranking:
        rankings.render(base)

    with tab_detalhe:
        base_detalhada.render(base)

    with tab_admin:
        admin.render()


# -----------------------------------------------------------------
# Execução standalone (streamlit run app/app.py)
# -----------------------------------------------------------------
if __name__ == "__main__":
    st.set_page_config(
        page_title="Gastos Prefeitura",
        page_icon="🏛️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    login_requerido()
    render()
