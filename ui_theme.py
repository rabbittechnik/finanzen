"""Globale Dark-UI Styles für Streamlit (ruhiger Fokus, dezente Akzente)."""
from __future__ import annotations

import streamlit as st


def inject_neon_styles() -> None:
    st.markdown(
        """
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,600;0,9..40,700;1,9..40,400&display=swap');

  html, body, [data-testid="stAppViewContainer"] {
    font-family: "DM Sans", system-ui, sans-serif !important;
  }

  [data-testid="stAppViewContainer"] {
    background:
      radial-gradient(1200px 600px at 12% -10%, rgba(0, 245, 212, 0.05), transparent 55%),
      radial-gradient(900px 500px at 88% 0%, rgba(183, 148, 246, 0.04), transparent 50%),
      linear-gradient(180deg, #070a12 0%, #0a0f18 100%) !important;
  }

  [data-testid="stHeader"] {
    background: #0a0f18 !important;
    border-bottom: 1px solid rgba(100, 116, 139, 0.2) !important;
    backdrop-filter: blur(8px);
  }
  [data-testid="stHeader"] [data-testid="stToolbar"] {
    background: transparent !important;
  }

  [data-testid="stSidebar"] {
    background: linear-gradient(175deg, #0c101a 0%, #0a0e14 100%) !important;
    border-right: 1px solid rgba(100, 116, 139, 0.22) !important;
    box-shadow: 2px 0 20px rgba(0, 0, 0, 0.25);
  }
  [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #b8c5d6 !important;
  }

  h1 {
    font-weight: 700 !important;
    letter-spacing: -0.03em !important;
    font-size: 1.95rem !important;
    color: #e8edf5 !important;
    -webkit-text-fill-color: #e8edf5 !important;
    background: none !important;
    filter: none !important;
  }

  h2, h3, h4 { color: #f0f4fa !important; font-weight: 600 !important; }

  [data-testid="stTabs"] [role="tab"] {
    color: #8b9cb3 !important;
    font-weight: 600 !important;
  }
  [data-testid="stTabs"] [aria-selected="true"] {
    color: #5eead4 !important;
    border-bottom-color: rgba(94, 234, 212, 0.85) !important;
    text-shadow: none !important;
  }

  div[data-testid="stExpander"] details {
    border: 1px solid rgba(0, 245, 212, 0.15) !important;
    border-radius: 10px !important;
    background: rgba(15, 20, 30, 0.55) !important;
  }

  .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #0d9488 0%, #14b8a6 55%, #2dd4bf 100%) !important;
    color: #041016 !important;
    font-weight: 600 !important;
    border: none !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.28) !important;
    transition: box-shadow 0.12s ease, filter 0.12s ease !important;
  }
  .stButton > button[kind="primary"]:hover {
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35) !important;
    filter: brightness(1.06);
    transform: none;
  }

  .stButton > button[kind="secondary"] {
    border-color: rgba(100, 116, 139, 0.45) !important;
    color: #cbd5e1 !important;
    background: rgba(15, 23, 42, 0.5) !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    min-height: 2.1rem !important;
    padding-top: 0.25rem !important;
    padding-bottom: 0.25rem !important;
  }
  .stButton > button[kind="secondary"]:hover {
    border-color: rgba(94, 234, 212, 0.35) !important;
    color: #e2e8f0 !important;
  }

  div[data-baseweb="select"] > div {
    border-color: rgba(0, 245, 212, 0.2) !important;
  }

  .neon-card {
    border: 1px solid rgba(100, 116, 139, 0.22);
    border-radius: 14px;
    padding: 1rem 1.15rem;
    background: rgba(12, 16, 26, 0.65);
    margin-bottom: 0.75rem;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
  }
  .sidebar-brand {
    font-size: 1.05rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: #5eead4;
    text-shadow: none;
    margin-bottom: 0.35rem;
  }
  .sidebar-muted {
    font-size: 0.88rem;
    color: #94a3b8;
    line-height: 1.45;
  }
  .pill-ok {
    display: inline-block;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
    background: rgba(0, 245, 212, 0.12);
    color: #5eead4;
    font-weight: 600;
    font-size: 0.85rem;
    border: 1px solid rgba(0, 245, 212, 0.35);
  }
  .pill-warn {
    display: inline-block;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
    background: rgba(251, 191, 36, 0.1);
    color: #fcd34d;
    font-weight: 600;
    font-size: 0.85rem;
    border: 1px solid rgba(251, 191, 36, 0.35);
  }

  .neon-kpi-row {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    margin: 0.5rem 0 1.25rem 0;
  }
  .neon-kpi {
    flex: 1 1 220px;
    min-width: 200px;
    border-radius: 16px;
    padding: 1.1rem 1.25rem;
    border: 1px solid rgba(100, 116, 139, 0.28);
    background: linear-gradient(155deg, rgba(18, 26, 42, 0.92) 0%, rgba(10, 14, 24, 0.88) 100%);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
  }
  .neon-kpi.magenta {
    border-color: rgba(148, 163, 184, 0.3);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
  }
  .neon-kpi.gold {
    border-color: rgba(148, 163, 184, 0.3);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
  }
  .neon-kpi-label {
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #94a3b8;
    margin-bottom: 0.35rem;
  }
  .neon-kpi-value {
    font-size: 1.75rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #5eead4 !important;
    -webkit-text-fill-color: #5eead4 !important;
    background: none !important;
    filter: none !important;
  }
  .neon-kpi.magenta .neon-kpi-value {
    color: #f9a8d4 !important;
    -webkit-text-fill-color: #f9a8d4 !important;
    background: none !important;
    filter: none !important;
  }
  .neon-kpi.gold .neon-kpi-value {
    color: #fcd34d !important;
    -webkit-text-fill-color: #fcd34d !important;
    background: none !important;
    filter: none !important;
  }
  .neon-kpi-sub {
    font-size: 0.82rem;
    color: #8b9cb3;
    margin-top: 0.4rem;
    line-height: 1.35;
  }

  .neon-chat-panel {
    border: 1px solid rgba(100, 116, 139, 0.25);
    border-radius: 14px;
    padding: 0.75rem 0.9rem;
    background: rgba(12, 18, 30, 0.75);
    margin-bottom: 0.75rem;
  }

  /* Haupt-Layout: Marker in der Mittelspalte (Chat an/aus), nicht von stChatInput abhängig */
  div[data-testid="stHorizontalBlock"]:has([data-docu-main-chat-layout]) > div[data-testid="column"]:first-child {
    max-height: calc(100dvh - 5rem);
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 0.35rem;
    scrollbar-gutter: stable;
  }
  div[data-testid="stHorizontalBlock"]:has([data-docu-main-chat-layout]) > div[data-testid="column"]:last-child {
    max-height: calc(100dvh - 5rem);
    overflow: hidden;
    align-self: flex-start;
  }
  div[data-testid="stHorizontalBlock"]:has([data-docu-main-single-col]) > div[data-testid="column"]:first-child {
    max-height: calc(100dvh - 5rem);
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 0.35rem;
    scrollbar-gutter: stable;
  }

  /* Quick-Leiste oben in der Mittelspalte (Update / Testmail / KI) */
  div[data-testid="stHorizontalBlock"]:has([data-docu-quick-actions="1"]) {
    position: sticky;
    top: 2.75rem;
    z-index: 50;
    background: rgba(7, 10, 18, 0.96);
    backdrop-filter: blur(8px);
    padding: 0.35rem 0 0.5rem;
    margin: 0 0 0.35rem 0;
    border-bottom: 1px solid rgba(100, 116, 139, 0.28);
  }

  .dash-main-title {
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    margin: 0.15rem 0 1rem 0 !important;
    color: #e2e8f0 !important;
    -webkit-text-fill-color: #e2e8f0 !important;
    background: none !important;
    filter: none !important;
  }
  .dash-section-label {
    font-size: 0.82rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #64748b;
    margin: 1.25rem 0 0.5rem 0;
  }
  .dash-tile-inner {
    border-radius: 16px;
    padding: 1rem 1.1rem 1.15rem;
    min-height: 9.5rem;
    transition: border-color 0.14s ease, box-shadow 0.14s ease;
    border: 1px solid rgba(100, 116, 139, 0.32);
    background: linear-gradient(165deg, rgba(18, 28, 48, 0.96) 0%, rgba(10, 14, 24, 0.94) 100%);
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.04);
  }
  .dash-tile-inner:hover {
    border-color: rgba(148, 163, 184, 0.45);
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.05);
  }

  /* Eine ruhige Basis; Saldo als leichter Fokus (linker Akzent) */
  .dash-tile--saldo {
    border-left: 3px solid rgba(45, 212, 191, 0.65);
  }
  .dash-tile--saldo .dash-tile-title { color: #99f6e4; }

  .dash-tile--fixkosten .dash-tile-title { color: #fcd34d; }
  .dash-tile--income .dash-tile-title { color: #86efac; }
  .dash-tile--expense .dash-tile-title { color: #fca5a5; }
  .dash-tile--debt .dash-tile-title { color: #fdba74; }
  .dash-tile--strom .dash-tile-title { color: #7dd3fc; }
  .dash-tile--haus .dash-tile-title { color: #c4b5fd; }
  .dash-tile--handy .dash-tile-title { color: #f9a8d4; }
  .dash-tile--vers .dash-tile-title { color: #d8b4fe; }
  .dash-tile--oepnv .dash-tile-title { color: #93c5fd; }

  .dash-tile-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: #e2e8f0;
    margin-bottom: 0.55rem;
    letter-spacing: 0.02em;
  }
  .dash-tile-body p {
    margin: 0.2rem 0;
    font-size: 0.92rem;
    color: #cbd5e1;
    line-height: 1.35;
  }
  /* Tabellenzeilen: Details-Spalte oben bündig mit Kachel */
  div[data-testid="stHorizontalBlock"]:has(.dash-tile-inner) div[data-testid="column"] {
    align-self: start;
  }
  .dash-tile-note {
    font-size: 0.75rem !important;
    color: #64748b !important;
    margin-top: 0.45rem !important;
  }
  .dash-money-pos { color: #5eead4 !important; font-weight: 600; }
  .dash-money-neg { color: #fca5a5 !important; font-weight: 600; }
  .dash-money-zero { color: #94a3b8 !important; }
  .dash-grid-1 {
    max-width: 420px;
    margin-top: 0.5rem;
  }
  @media (max-width: 900px) {
    .dash-tile-inner { min-height: auto; }
  }
</style>
        """,
        unsafe_allow_html=True,
    )
