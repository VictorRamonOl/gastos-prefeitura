"""
app/ui.py
Tema executive dark — CSS + helpers (hero, section title, page header).
Reusa a linguagem visual do Dash_APMC para consistência entre dashboards.
"""
from __future__ import annotations

import streamlit as st


# Paleta executiva — cores contrastantes para uso em gráficos categóricos.
PALETA_EXEC = [
    "#2563eb", "#16a34a", "#f59e0b", "#9333ea", "#db2777",
    "#0891b2", "#65a30d", "#ea580c", "#7c3aed", "#6b7280",
    "#0ea5e9", "#84cc16", "#f97316", "#a855f7", "#ec4899",
]


@st.cache_resource(show_spinner=False)
def _build_css() -> str:
    return _CSS_RAW


def inject_css() -> None:
    """Injeta o tema executive dark. Chame uma vez no início do render()."""
    st.markdown(_build_css(), unsafe_allow_html=True)


def force_sidebar_open() -> None:
    """Força a sidebar a abrir (vence o localStorage que o Streamlit guarda
    do estado anterior). Chame após inject_css() — usa components.html para
    rodar JS no iframe pai."""
    import streamlit.components.v1 as components
    components.html(_FORCE_SIDEBAR_JS, height=0)


_FORCE_SIDEBAR_JS = """
<script>
(function() {
  const win = window.parent;
  const doc = win.document;
  let attempts = 0;
  const MAX = 40;

  function isCollapsed(sb) {
    if (!sb) return true;
    if (sb.getAttribute('aria-expanded') === 'false') return true;
    if (sb.offsetWidth < 100) return true;
    const cs = win.getComputedStyle(sb);
    if (cs.display === 'none' || cs.visibility === 'hidden') return true;
    if (parseFloat(cs.transform.split(',')[4] || '0') < -100) return true;
    return false;
  }

  function findExpandButton() {
    const candidates = [
      '[data-testid="stSidebarCollapsedControl"] button',
      '[data-testid="stSidebarCollapseButton"] button',
      'button[data-testid="stExpandSidebarButton"]',
      'button[kind="headerNoPadding"]',
      'section[data-testid="stSidebar"] button[kind="header"]',
    ];
    for (const sel of candidates) {
      const b = doc.querySelector(sel);
      if (b) return b;
    }
    return null;
  }

  function tryExpand() {
    attempts++;
    if (attempts > MAX) return;

    const sb = doc.querySelector('section[data-testid="stSidebar"]');
    if (!sb) { setTimeout(tryExpand, 150); return; }

    if (!isCollapsed(sb)) {
      // já está aberta — só garante que o conteúdo seja visível
      sb.style.display = 'block';
      sb.style.visibility = 'visible';
      return;
    }

    const btn = findExpandButton();
    if (btn) {
      try { btn.click(); } catch(e) {}
    }
    setTimeout(tryExpand, 200);
  }

  // Também limpa qualquer flag de "collapsed" salva pelo portal
  try { win.localStorage.removeItem('apmc_sb_collapsed'); } catch(e) {}
  try { win.localStorage.removeItem('sidebarState'); } catch(e) {}

  setTimeout(tryExpand, 100);
})();
</script>
"""


def hero(title: str, subtitle: str | None = None,
         eyebrow: str | None = None, pills: list[str] | None = None) -> None:
    """Header hero com gradiente, eyebrow opcional e pills de metadata."""
    eb = f'<div class="eyebrow">{eyebrow}</div>' if eyebrow else ""
    sub = f'<div class="subtitle">{subtitle}</div>' if subtitle else ""
    pp = ""
    if pills:
        items = "".join(f'<span class="pill">{p}</span>' for p in pills)
        pp = f'<div class="meta">{items}</div>'
    st.markdown(
        f'<div class="exec-hero">{eb}<h1>{title}</h1>{sub}{pp}</div>',
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str | None = None) -> None:
    """Cabeçalho enxuto para abas/views: título + linha curta ao lado."""
    sub_html = f'<span class="ph-sub">{subtitle}</span>' if subtitle else ""
    st.markdown(
        f'<div class="page-header"><h1 class="ph-title">{title}</h1>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def section_title(text: str) -> None:
    """Título de seção com linha divisória sutil que cresce ao lado."""
    st.markdown(
        f'<div class="exec-section-title">{text}</div>',
        unsafe_allow_html=True,
    )


_CSS_RAW = """\
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  --bg-0: #0b0e14;
  --bg-1: #111827;
  --bg-2: #161d2b;
  --surface: #1a1f2b;
  --surface-2: #212838;
  --border: rgba(255,255,255,0.06);
  --border-strong: rgba(255,255,255,0.10);
  --text-1: #e6edf6;
  --text-2: #aab4c4;
  --text-3: #6b7689;
  --accent: #1e5b9e;
  --accent-2: #4a90d4;
  --accent-3: #2a6cb3;
  --ok: #22c55e;
  --warn: #f59e0b;
  --err: #ef4444;
  --shadow-md: 0 4px 14px rgba(0,0,0,0.35), 0 1px 2px rgba(0,0,0,0.4);
  --shadow-lg: 0 10px 30px rgba(0,0,0,0.45), 0 2px 6px rgba(0,0,0,0.35);
  --radius: 14px;
  --radius-sm: 10px;
}

html, body, [class*="css"], .stApp, .stMarkdown, .stMetric,
[data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
  font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif !important;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

.stApp {
  background:
    radial-gradient(1200px 600px at 0% -10%, rgba(30,91,158,0.10), transparent 60%),
    radial-gradient(900px 500px at 100% 0%, rgba(74,144,212,0.06), transparent 55%),
    var(--bg-0);
  color: var(--text-1);
}

/* Wide mode */
.block-container {
  padding-top: 1rem !important;
  padding-bottom: 4rem !important;
  padding-left: 2.2rem !important;
  padding-right: 2.2rem !important;
  max-width: 100% !important;
}

/* Tipografia */
h1, h2, h3, h4 { letter-spacing: -0.01em; color: var(--text-1); }
h1 { font-weight: 800 !important; font-size: 2rem !important; }
h2 { font-weight: 700 !important; }
h3 { font-weight: 600 !important; }
.stCaption, [data-testid="stCaptionContainer"] { color: var(--text-2) !important; }

/* HERO */
.exec-hero {
  position: relative;
  background: linear-gradient(135deg, rgba(30,91,158,0.18), rgba(42,108,179,0.10) 60%, rgba(255,255,255,0.02));
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  padding: 22px 26px;
  margin: 6px 0 22px 0;
  box-shadow: var(--shadow-md);
  overflow: hidden;
}
.exec-hero::before {
  content: ""; position: absolute; inset: 0;
  background: radial-gradient(600px 200px at 90% -20%, rgba(74,144,212,0.22), transparent 60%);
  pointer-events: none;
}
.exec-hero .eyebrow {
  font-size: 0.72rem; font-weight: 600; letter-spacing: 0.14em;
  text-transform: uppercase; color: var(--accent-2);
  display: inline-flex; align-items: center; gap: 8px;
}
.exec-hero .eyebrow::before {
  content: ""; width: 6px; height: 6px; border-radius: 50%;
  background: var(--accent-2); box-shadow: 0 0 10px var(--accent-2);
}
.exec-hero h1 {
  font-size: 1.9rem !important; margin: 8px 0 6px 0 !important;
  font-weight: 800 !important;
  background: linear-gradient(180deg, #ffffff 0%, #c8d4e6 100%);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
}
.exec-hero .subtitle { color: var(--text-2); font-size: 0.97rem; max-width: 820px; line-height: 1.55; }
.exec-hero .meta { margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap; }
.exec-hero .pill {
  display: inline-flex; align-items: center; gap: 6px;
  background: rgba(255,255,255,0.04); border: 1px solid var(--border-strong);
  padding: 4px 10px; border-radius: 999px;
  font-size: 0.78rem; color: var(--text-2); font-weight: 500;
}
.exec-hero .pill b { color: var(--text-1); font-weight: 600; }

/* PAGE HEADER */
.page-header {
  display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap;
  padding: 4px 0 18px 0;
  margin-bottom: 6px;
  border-bottom: 1px solid var(--border);
}
.page-header .ph-title {
  font-size: 1.6rem !important; font-weight: 700 !important;
  margin: 0 !important; letter-spacing: -0.01em;
  position: relative; padding-left: 14px;
}
.page-header .ph-title::before {
  content: ""; position: absolute; left: 0; top: 8px; bottom: 8px;
  width: 3px; border-radius: 2px;
  background: linear-gradient(180deg, #1e5b9e, #4a90d4);
}
.page-header .ph-sub {
  color: var(--text-3); font-size: 0.92rem; font-weight: 400;
  border-left: 1px solid var(--border-strong);
  padding-left: 14px;
}

/* MÉTRICAS */
[data-testid="stMetric"] {
  background: linear-gradient(180deg, var(--surface), var(--bg-2));
  border: 1px solid var(--border);
  padding: 16px 18px 18px;
  border-radius: var(--radius);
  box-shadow: var(--shadow-md);
  transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
  position: relative; overflow: hidden;
}
[data-testid="stMetric"]::before {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
  background: linear-gradient(180deg, var(--accent), transparent);
  opacity: 0.7;
}
[data-testid="stMetric"]:hover {
  transform: translateY(-1px);
  border-color: var(--border-strong);
  box-shadow: var(--shadow-lg);
}
[data-testid="stMetricValue"] {
  font-size: 1.85rem !important; font-weight: 700 !important;
  letter-spacing: -0.02em; color: var(--text-1) !important;
}
[data-testid="stMetricLabel"] {
  font-size: 0.78rem !important; font-weight: 500 !important;
  color: var(--text-2) !important; text-transform: uppercase; letter-spacing: 0.06em;
}
[data-testid="stMetricDelta"] { font-size: 0.78rem !important; font-weight: 600 !important; }

/* SECTION TITLE */
.exec-section-title {
  font-size: 1.05rem; font-weight: 600; color: var(--text-1);
  margin: 22px 0 12px 0;
  display: flex; align-items: center; gap: 10px;
}
.exec-section-title::after {
  content: ""; flex: 1; height: 1px;
  background: linear-gradient(90deg, var(--border-strong), transparent);
}

/* CARD */
.exec-card {
  background: linear-gradient(180deg, var(--surface), var(--bg-2));
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px 22px;
  box-shadow: var(--shadow-md);
  transition: border-color .2s ease, box-shadow .2s ease;
}
.exec-card:hover { border-color: var(--border-strong); box-shadow: var(--shadow-lg); }

/* DIVIDER */
hr, [data-testid="stDivider"] {
  border-color: var(--border) !important;
  opacity: 0.6 !important;
  margin: 1.4rem 0 !important;
}

/* ============ MULTISELECT — pills coloridas, mais largas ============ */
[data-baseweb="tag"] {
  background: linear-gradient(135deg, rgba(30,91,158,0.65), rgba(42,108,179,0.45)) !important;
  border: 1px solid rgba(74,144,212,0.55) !important;
  border-radius: 7px !important;
  color: #ffffff !important;
  font-weight: 500 !important;
  font-size: 0.82rem !important;
  padding: 2px 4px !important;
  box-shadow: 0 2px 6px rgba(30,91,158,0.25) !important;
}
[data-baseweb="tag"] svg { color: #c8d4e6 !important; }
[data-baseweb="tag"]:hover {
  background: linear-gradient(135deg, rgba(30,91,158,0.85), rgba(42,108,179,0.65)) !important;
}

/* Dropdown items */
li[role="option"] {
  background: var(--surface) !important;
  color: var(--text-1) !important;
  font-size: 0.88rem !important;
  padding: 8px 12px !important;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
li[role="option"]:hover {
  background: rgba(30,91,158,0.20) !important;
  color: #ffffff !important;
}
li[role="option"][aria-selected="true"] {
  background: rgba(30,91,158,0.35) !important;
  color: #ffffff !important;
  font-weight: 600;
}

/* ============ TOOLTIPS / HELP TEXT ============ */
[data-testid="stTooltipIcon"] {
  color: var(--accent-2) !important;
  opacity: 0.65;
  transition: opacity .15s ease;
}
[data-testid="stTooltipIcon"]:hover { opacity: 1; }

/* ============ STATUS NA SIDEBAR ============ */
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] .stTextInput > div > div {
  background: rgba(255,255,255,0.025) !important;
  border-color: rgba(255,255,255,0.08) !important;
}

/* Selectbox single — placeholder mais visível */
[data-baseweb="select"] div[role="combobox"] {
  font-size: 0.92rem !important;
}

/* SIDEBAR — força visibilidade (o portal.py esconde-a no hub, precisamos reabrir aqui) */
section[data-testid="stSidebar"],
[data-testid="stSidebar"] {
  display: block !important;
  visibility: visible !important;
  background: linear-gradient(180deg, #0d121c 0%, #0a0e16 100%) !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"],
button[kind="headerNoPadding"] {
  display: flex !important;
  visibility: visible !important;
  opacity: 1 !important;
}
[data-testid="stSidebar"] h2 {
  font-size: 0.78rem !important; font-weight: 700 !important;
  text-transform: uppercase; letter-spacing: 0.12em;
  color: var(--text-3) !important; margin-bottom: 4px !important;
}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
  color: var(--text-3) !important; font-size: 0.74rem !important;
}
[data-testid="stSidebarNav"] { display: none !important; }

/* INPUTS */
[data-baseweb="select"] > div, .stTextInput > div > div, .stNumberInput > div > div {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
  transition: border-color .15s ease;
}
[data-baseweb="select"] > div:hover, .stTextInput > div > div:hover {
  border-color: var(--border-strong) !important;
}
[data-baseweb="select"] > div:focus-within, .stTextInput > div > div:focus-within {
  border-color: var(--accent-2) !important;
  box-shadow: 0 0 0 3px rgba(74,144,212,0.22) !important;
}
label, [data-testid="stWidgetLabel"] p {
  font-size: 0.78rem !important; font-weight: 500 !important;
  color: var(--text-2) !important; letter-spacing: 0.02em;
}

/* TABS */
[data-baseweb="tab-list"] {
  gap: 4px !important;
  background: transparent !important;
  border-bottom: 1px solid var(--border) !important;
}
[data-baseweb="tab"] {
  background: transparent !important;
  border: none !important;
  color: var(--text-2) !important;
  font-weight: 500 !important;
  padding: 10px 18px !important;
  border-bottom: 3px solid transparent !important;
  transition: all .15s ease;
}
[data-baseweb="tab"]:hover {
  color: var(--text-1) !important;
  background: rgba(74,144,212,0.06) !important;
}
[data-baseweb="tab"][aria-selected="true"] {
  color: #ffffff !important;
  border-bottom: 3px solid var(--accent-2) !important;
  background: rgba(30,91,158,0.10) !important;
  font-weight: 700 !important;
}
[data-baseweb="tab-highlight"] { display: none !important; }

/* DATAFRAME */
[data-testid="stDataFrame"] {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow-md);
}
[data-testid="stDataFrame"] [role="row"]:hover {
  background: rgba(30,91,158,0.10) !important;
}

/* EXPANDER */
[data-testid="stExpander"] {
  background: linear-gradient(180deg, var(--surface), var(--bg-2));
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow-md);
  margin-bottom: 10px;
}
[data-testid="stExpander"] summary {
  font-weight: 600 !important;
  color: var(--text-1) !important;
}

/* BOTÕES */
.stButton > button, .stDownloadButton > button {
  background: linear-gradient(135deg, rgba(30,91,158,0.55), rgba(42,108,179,0.32)) !important;
  border: 1px solid rgba(74,144,212,0.50) !important;
  color: #ffffff !important;
  border-radius: var(--radius-sm) !important;
  font-weight: 600 !important;
  padding: 8px 16px !important;
  box-shadow: 0 4px 12px rgba(30,91,158,0.30) !important;
  transition: all .15s ease !important;
}
.stButton > button:hover, .stDownloadButton > button:hover {
  background: linear-gradient(135deg, rgba(30,91,158,0.70), rgba(42,108,179,0.45)) !important;
  border-color: rgba(74,144,212,0.70) !important;
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(30,91,158,0.40) !important;
}

/* ALERTS */
[data-testid="stAlert"] {
  border-radius: var(--radius);
  border: 1px solid var(--border-strong);
  background: var(--surface) !important;
}

/* PLOTLY — container card */
[data-testid="stPlotlyChart"] {
  background: linear-gradient(180deg, var(--surface), var(--bg-2));
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px 12px 8px 12px;
  box-shadow: var(--shadow-md);
  overflow: hidden;
  transition: border-color .2s ease, box-shadow .2s ease;
}
[data-testid="stPlotlyChart"]:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow-lg);
}
[data-testid="stPlotlyChart"] .js-plotly-plot,
[data-testid="stPlotlyChart"] .plotly,
[data-testid="stPlotlyChart"] .main-svg { background: transparent !important; }

/* PROGRESS */
[data-testid="stProgress"] > div > div > div {
  background: linear-gradient(90deg, var(--accent), var(--accent-2)) !important;
}

/* SCROLLBAR */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: var(--bg-0); }
::-webkit-scrollbar-thumb { background: #2a3344; border-radius: 8px; border: 2px solid var(--bg-0); }
::-webkit-scrollbar-thumb:hover { background: #3a455a; }

/* Footer */
footer, [data-testid="stToolbar"] { visibility: hidden; height: 0; }
</style>
"""
