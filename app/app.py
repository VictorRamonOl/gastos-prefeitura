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
from app.ui import inject_css, hero, force_sidebar_open
from app.views import geral, secretaria, fornecedor, rankings, base_detalhada, admin


# -----------------------------------------------------------------
# render() — ponto de entrada chamado pelo Portal Central
# Não inclui set_page_config nem login_requerido (ambos ficam
# exclusivamente no bloco __main__ abaixo).
# -----------------------------------------------------------------
def render():
    """Renderiza o dashboard de Despesas. Chamado pelo Portal Central."""
    inject_css()
    force_sidebar_open()

    # Carga de dados (antes do hero — precisamos do período pra pills)
    try:
        df_full = carregar_dados()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        st.stop()

    if df_full.empty:
        st.warning("Nenhum dado no banco. Execute: `python etl/run_etl.py`")
        st.stop()

    # Hero
    usuario = usuario_atual()
    anos_disponiveis = sorted(df_full["ano"].dropna().unique().astype(int).tolist())
    periodo_pill = (
        f"Período <b>{anos_disponiveis[0]}–{anos_disponiveis[-1]}</b>"
        if anos_disponiveis else "Período <b>—</b>"
    )
    n_secs = df_full["secretaria"].nunique()
    n_favs = df_full["favorecido"].nunique()

    col_hero, col_user = st.columns([5, 1])
    with col_hero:
        hero(
            title="Despesas da Prefeitura",
            eyebrow="Maués · AM",
            subtitle="Painel executivo de gastos municipais — secretarias, fornecedores e fontes de recurso.",
            pills=[
                periodo_pill,
                f"<b>{n_secs}</b> secretarias",
                f"<b>{n_favs:,}".replace(",", ".") + "</b> favorecidos",
            ],
        )
    with col_user:
        st.markdown(
            f"<div style='text-align:right;padding-top:18px;font-size:0.85rem;color:#aab4c4'>"
            f"👤 <b style='color:#e6edf6'>{usuario.get('nome') or usuario.get('username')}</b>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button("Sair", use_container_width=True):
            logout()

    # Sidebar — Filtros
    st.sidebar.header("🔎 Filtros")
    st.sidebar.caption(
        "Escolha um ou mais valores em cada filtro. "
        "Deixar em branco mostra TUDO daquele campo."
    )

    anos_disp     = sorted(df_full["ano"].dropna().unique().astype(int).tolist())
    meses_disp    = sorted(df_full["mes"].dropna().unique().astype(int).tolist())
    secs_disp     = sorted(x for x in df_full["secretaria"].dropna().unique() if x.strip())
    recursos_disp = sorted(x for x in df_full["recurso"].dropna().unique() if x.strip())
    favs_disp     = sorted(x for x in df_full["favorecido"].dropna().unique() if x.strip())

    # Botão pra limpar filtros — reseta chaves de session_state
    if st.sidebar.button("↺ Limpar todos os filtros", use_container_width=True):
        for k in ("flt_ano", "flt_mes", "flt_sec", "flt_rec", "flt_fav", "flt_busca"):
            st.session_state.pop(k, None)
        st.rerun()

    anos_sel     = st.sidebar.multiselect("Ano", anos_disp, default=anos_disp, key="flt_ano")
    meses_sel    = st.sidebar.multiselect(
        "Mês", meses_disp, default=[],
        format_func=lambda x: MESES_FULL.get(x, str(x)),
        key="flt_mes",
    )
    secs_sel     = st.sidebar.multiselect("Secretaria", secs_disp, default=[], key="flt_sec")
    recursos_sel = st.sidebar.multiselect("Recurso (fonte)", recursos_disp, default=[], key="flt_rec")
    favs_sel     = st.sidebar.multiselect("Favorecido", favs_disp, default=[], key="flt_fav")
    busca        = st.sidebar.text_input(
        "Buscar texto",
        placeholder="ex: medicamento, transporte…",
        help="Busca dentro de favorecido, descrição e recurso.",
        key="flt_busca",
    )

    base = aplicar_filtros(df_full, anos_sel, meses_sel, secs_sel, recursos_sel, favs_sel, busca)

    if base.empty:
        st.warning(
            "Nenhum lançamento bate com os filtros. Tente clicar em "
            "**↺ Limpar todos os filtros** na barra lateral."
        )
        st.stop()

    # KPIs gerais
    total    = base["valor"].sum()
    qtd      = len(base)
    qtd_favs = base["favorecido"].nunique()
    media    = base["valor"].mean()
    n_secs_b = base["secretaria"].nunique()
    pct_total = (total / df_full["valor"].sum() * 100) if df_full["valor"].sum() else 100

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("💰 Total gasto",        formatar_mi(total),
              delta=f"{pct_total:.1f}% da base", delta_color="off")
    k2.metric("📋 Lançamentos",        f"{qtd:,}".replace(",", "."))
    k3.metric("🏢 Favorecidos únicos", f"{qtd_favs:,}".replace(",", "."))
    k4.metric("🏛️ Secretarias",       f"{n_secs_b:,}".replace(",", "."))
    k5.metric("📊 Valor médio",        formatar_brl(media))

    st.markdown("")

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
    # inject_css() é chamado dentro de render() — não duplicar aqui.
    login_requerido()
    render()
