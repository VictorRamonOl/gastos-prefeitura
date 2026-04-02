"""
app/views/admin.py
Aba "Admin" — logs de importação, usuários e totais anuais.
Restrito a perfil admin.
"""
import streamlit as st

from app.auth import is_admin
from app.db import query_df


def render():
    if not is_admin():
        st.warning("Acesso restrito a administradores.")
        return

    col_a1, col_a2 = st.columns(2)

    with col_a1:
        st.subheader("Últimas importações")
        try:
            logs = query_df("""
                SELECT nome_arquivo, total_linhas, linhas_inseridas,
                       linhas_duplicadas, status,
                       DATE_FORMAT(importado_em, '%d/%m/%Y %H:%i') AS importado_em
                FROM arquivos_importados
                ORDER BY importado_em DESC
                LIMIT 20
            """)
            st.dataframe(logs, hide_index=True, use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao carregar logs: {e}")

    with col_a2:
        st.subheader("Usuários")
        try:
            usuarios_df = query_df("""
                SELECT username, nome, perfil,
                       IF(ativo, 'Ativo', 'Inativo') AS status,
                       DATE_FORMAT(criado_em, '%d/%m/%Y') AS criado_em,
                       DATE_FORMAT(ultimo_acesso, '%d/%m/%Y %H:%i') AS ultimo_acesso
                FROM usuarios
                ORDER BY criado_em DESC
            """)
            st.dataframe(usuarios_df, hide_index=True, use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao carregar usuários: {e}")

    st.markdown("---")
    st.subheader("Totais por ano")
    try:
        tot_ano = query_df("""
            SELECT ano,
                   COUNT(*) AS lancamentos,
                   COUNT(DISTINCT favorecido) AS favorecidos,
                   ROUND(SUM(valor), 2) AS total_gasto
            FROM pagamentos
            GROUP BY ano
            ORDER BY ano
        """)
        st.dataframe(tot_ano, hide_index=True, use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao carregar totais: {e}")
