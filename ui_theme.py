"""Globale Neon-Dark Styles (Streamlit + config.toml)."""
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
      radial-gradient(1200px 600px at 12% -10%, rgba(0, 245, 212, 0.12), transparent 55%),
      radial-gradient(900px 500px at 88% 0%, rgba(183, 148, 246, 0.1), transparent 50%),
      linear-gradient(180deg, #070a12 0%, #0a0f18 100%) !important;
  }

  [data-testid="stHeader"] { background: rgba(7, 10, 18, 0.85) !important; backdrop-filter: blur(8px); }

  [data-testid="stSidebar"] {
    background: linear-gradient(175deg, #0c101a 0%, #0a0e14 100%) !important;
    border-right: 1px solid rgba(0, 245, 212, 0.18) !important;
    box-shadow: 4px 0 32px rgba(0, 0, 0, 0.35);
  }
  [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #b8c5d6 !important;
  }

  h1 {
    font-weight: 700 !important;
    letter-spacing: -0.03em !important;
    font-size: 2.1rem !important;
    background: linear-gradient(110deg, #00f5d4 0%, #6ee7ff 42%, #c4b5fd 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 0 24px rgba(0, 245, 212, 0.25));
  }

  h2, h3, h4 { color: #f0f4fa !important; font-weight: 600 !important; }

  [data-testid="stTabs"] [role="tab"] {
    color: #8b9cb3 !important;
    font-weight: 600 !important;
  }
  [data-testid="stTabs"] [aria-selected="true"] {
    color: #00f5d4 !important;
    border-bottom-color: #00f5d4 !important;
    text-shadow: 0 0 18px rgba(0, 245, 212, 0.45);
  }

  div[data-testid="stExpander"] details {
    border: 1px solid rgba(0, 245, 212, 0.15) !important;
    border-radius: 10px !important;
    background: rgba(15, 20, 30, 0.55) !important;
  }

  .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #00c9aa 0%, #00f5d4 50%, #5eead4 100%) !important;
    color: #041016 !important;
    font-weight: 700 !important;
    border: none !important;
    box-shadow: 0 0 20px rgba(0, 245, 212, 0.35), 0 4px 14px rgba(0, 0, 0, 0.35) !important;
    transition: transform 0.12s ease, box-shadow 0.12s ease !important;
  }
  .stButton > button[kind="primary"]:hover {
    box-shadow: 0 0 28px rgba(0, 245, 212, 0.55), 0 6px 20px rgba(0, 0, 0, 0.4) !important;
    transform: translateY(-1px);
  }

  .stButton > button[kind="secondary"] {
    border-color: rgba(0, 245, 212, 0.35) !important;
    color: #b8fff4 !important;
  }

  div[data-baseweb="select"] > div {
    border-color: rgba(0, 245, 212, 0.2) !important;
  }

  .neon-card {
    border: 1px solid rgba(0, 245, 212, 0.12);
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
    color: #00f5d4;
    text-shadow: 0 0 20px rgba(0, 245, 212, 0.5);
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
    border: 1px solid rgba(0, 245, 212, 0.22);
    background: linear-gradient(155deg, rgba(18, 26, 42, 0.92) 0%, rgba(10, 14, 24, 0.88) 100%);
    box-shadow:
      0 0 32px rgba(0, 245, 212, 0.08),
      inset 0 1px 0 rgba(255,255,255,0.05);
  }
  .neon-kpi.magenta {
    border-color: rgba(244, 114, 182, 0.35);
    box-shadow:
      0 0 36px rgba(244, 114, 182, 0.12),
      inset 0 1px 0 rgba(255,255,255,0.05);
  }
  .neon-kpi.gold {
    border-color: rgba(251, 191, 36, 0.28);
    box-shadow:
      0 0 28px rgba(251, 191, 36, 0.1),
      inset 0 1px 0 rgba(255,255,255,0.05);
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
    background: linear-gradient(100deg, #5eead4 0%, #67e8f9 50%, #a5f3fc 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 0 12px rgba(0, 245, 212, 0.35));
  }
  .neon-kpi.magenta .neon-kpi-value {
    background: linear-gradient(100deg, #fda4af 0%, #f472b6 45%, #e879f9 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 0 14px rgba(244, 114, 182, 0.4));
  }
  .neon-kpi.gold .neon-kpi-value {
    background: linear-gradient(100deg, #fde68a 0%, #fcd34d 50%, #fbbf24 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 0 12px rgba(251, 191, 36, 0.35));
  }
  .neon-kpi-sub {
    font-size: 0.82rem;
    color: #8b9cb3;
    margin-top: 0.4rem;
    line-height: 1.35;
  }

  .neon-chat-panel {
    border: 1px solid rgba(0, 245, 212, 0.2);
    border-radius: 14px;
    padding: 0.75rem 0.9rem;
    background: rgba(12, 18, 30, 0.75);
    margin-bottom: 0.75rem;
  }

  /* Haupt-Layout: linke Spalte scrollt intern; Chat-Spalte bleibt im sichtbaren Bereich */
  div[data-testid="stHorizontalBlock"]:has([data-testid="stChatInput"]) > div[data-testid="column"]:first-child {
    max-height: calc(100dvh - 5rem);
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 0.35rem;
    scrollbar-gutter: stable;
  }
  div[data-testid="stHorizontalBlock"]:has([data-testid="stChatInput"]) > div[data-testid="column"]:last-child {
    max-height: calc(100dvh - 5rem);
    overflow: hidden;
    align-self: flex-start;
  }

  .dash-main-title {
    font-size: 1.55rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    margin: 0.15rem 0 1rem 0 !important;
    background: linear-gradient(110deg, #00f5d4 0%, #6ee7ff 45%, #c4b5fd 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 0 18px rgba(0, 245, 212, 0.35));
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
    border: 1px solid rgba(0, 245, 212, 0.22);
    border-radius: 16px;
    padding: 1rem 1.1rem 1.15rem;
    min-height: 9.5rem;
    background: linear-gradient(165deg, rgba(18, 28, 48, 0.95) 0%, rgba(10, 14, 24, 0.92) 100%);
    box-shadow:
      0 0 28px rgba(0, 245, 212, 0.12),
      inset 0 1px 0 rgba(255, 255, 255, 0.05);
    transition: transform 0.14s ease, box-shadow 0.14s ease, border-color 0.14s ease;
  }
  .dash-tile-inner:hover {
    transform: translateY(-2px) scale(1.01);
    border-color: rgba(0, 245, 212, 0.45);
    box-shadow:
      0 0 36px rgba(0, 245, 212, 0.28),
      0 10px 28px rgba(0, 0, 0, 0.35),
      inset 0 1px 0 rgba(255, 255, 255, 0.06);
  }
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
