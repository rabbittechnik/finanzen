"""Neues Finanz-UI: einheitliches Dark-Theme (nur fin-* Klassen, kein Legacy-CSS)."""
from __future__ import annotations

import streamlit as st


def inject_fin_ui_styles() -> None:
    st.markdown(
        """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

  html, body, [data-testid="stAppViewContainer"] {
    font-family: "Inter", "Segoe UI", system-ui, sans-serif !important;
  }

  [data-testid="stAppViewContainer"] {
    background:
      radial-gradient(1000px 520px at 8% -8%, rgba(34, 211, 238, 0.07), transparent 50%),
      radial-gradient(800px 480px at 92% 4%, rgba(45, 212, 191, 0.05), transparent 48%),
      linear-gradient(165deg, #05070d 0%, #0a0f18 45%, #070a12 100%) !important;
  }

  [data-testid="stHeader"] {
    background: rgba(7, 10, 18, 0.92) !important;
    border-bottom: 1px solid rgba(94, 234, 212, 0.12) !important;
  }

  /* Native Sidebar aus — Layout ist app-intern (eigene Spalten) */
  section[data-testid="stSidebar"] {
    display: none !important;
  }
  [data-testid="stToolbar"] {
    background: transparent !important;
  }

  h1, h2, h3 {
    color: #f1f5f9 !important;
    font-weight: 600 !important;
  }

  .fin-app-wrap {
    padding: 0.25rem 0.5rem 1.25rem 0.25rem;
  }

  .fin-brand-title {
    font-size: 0.95rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #f8fafc;
    line-height: 1.3;
    margin: 0 0 0.75rem 0;
    text-shadow: 0 0 24px rgba(45, 212, 191, 0.25);
  }

  .fin-nav-heading {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #64748b;
    margin: 0.5rem 0 0.35rem 0;
  }

  .fin-col-scroll {
    max-height: calc(100dvh - 4.5rem);
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 0.25rem;
    scrollbar-gutter: stable;
  }

  .fin-lumo-head {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    margin-bottom: 0.65rem;
    padding-bottom: 0.55rem;
    border-bottom: 1px solid rgba(94, 234, 212, 0.15);
  }
  .fin-lumo-avatar-wrap {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    border: 2px solid rgba(45, 212, 191, 0.65);
    box-shadow: 0 0 20px rgba(34, 211, 238, 0.35);
    overflow: hidden;
    flex-shrink: 0;
    background: linear-gradient(145deg, rgba(15, 23, 42, 0.9), rgba(8, 12, 22, 0.95));
  }
  .fin-lumo-title {
    font-size: 1rem;
    font-weight: 700;
    color: #e2e8f0;
    margin: 0;
  }
  .fin-lumo-greet {
    font-size: 0.82rem;
    color: #94a3b8;
    margin: 0.25rem 0 0 0;
    line-height: 1.35;
  }

  .fin-card {
    border-radius: 14px;
    border: 1px solid rgba(148, 163, 184, 0.18);
    background: linear-gradient(155deg, rgba(17, 24, 39, 0.92) 0%, rgba(10, 14, 24, 0.94) 100%);
    box-shadow:
      0 4px 18px rgba(0, 0, 0, 0.35),
      0 0 0 1px rgba(34, 211, 238, 0.06),
      inset 0 1px 0 rgba(255, 255, 255, 0.04);
    padding: 1rem 1.1rem;
    margin-bottom: 0.65rem;
  }

  .fin-pill-ok {
    display: inline-block;
    padding: 0.28rem 0.7rem;
    border-radius: 999px;
    background: rgba(34, 197, 94, 0.14);
    color: #4ade80;
    font-weight: 600;
    font-size: 0.8rem;
    border: 1px solid rgba(74, 222, 128, 0.4);
  }
  .fin-pill-warn {
    display: inline-block;
    padding: 0.28rem 0.7rem;
    border-radius: 999px;
    background: rgba(251, 191, 36, 0.1);
    color: #fcd34d;
    font-weight: 600;
    font-size: 0.8rem;
    border: 1px solid rgba(251, 191, 36, 0.35);
  }

  .fin-muted {
    color: #94a3b8;
    font-size: 0.82rem;
    line-height: 1.45;
  }

  .fin-top-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    gap: 0.75rem 1rem;
    padding: 0.65rem 0.85rem;
    margin-bottom: 1rem;
    border-radius: 14px;
    border: 1px solid rgba(94, 234, 212, 0.14);
    background: rgba(12, 18, 30, 0.72);
    box-shadow: 0 0 28px rgba(34, 211, 238, 0.06);
  }

  .fin-section-title {
    font-size: 1.35rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #e2e8f0;
    margin: 0.35rem 0 1rem 0;
  }
  .fin-section-kicker {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #64748b;
    margin: 1.35rem 0 0.65rem 0;
  }

  .fin-metric-card {
    border-radius: 14px;
    border: 1px solid rgba(148, 163, 184, 0.2);
    background: linear-gradient(160deg, rgba(20, 28, 48, 0.95) 0%, rgba(10, 14, 24, 0.92) 100%);
    box-shadow:
      0 6px 20px rgba(0, 0, 0, 0.32),
      0 0 24px rgba(34, 211, 238, 0.05);
    padding: 1.05rem 1.1rem 0.85rem;
    min-height: 10rem;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
  }
  .fin-metric-link {
    display: block;
    text-decoration: none !important;
    color: inherit !important;
    cursor: pointer;
  }
  .fin-metric-card:hover {
    border-color: rgba(94, 234, 212, 0.28);
    box-shadow: 0 8px 26px rgba(0, 0, 0, 0.38), 0 0 32px rgba(34, 211, 238, 0.1);
  }
  .fin-metric-link:focus-visible .fin-metric-card {
    outline: 2px solid rgba(94, 234, 212, 0.6);
    outline-offset: 2px;
  }
  .fin-metric-title {
    font-size: 0.92rem;
    font-weight: 700;
    color: #a5f3fc;
    margin-bottom: 0.5rem;
    letter-spacing: 0.02em;
  }
  .fin-metric-body p {
    margin: 0.18rem 0;
    font-size: 0.88rem;
    color: #cbd5e1;
    line-height: 1.4;
  }
  .fin-num-lg {
    font-size: 1.45rem;
    font-weight: 700;
    color: #f1f5f9;
    margin: 0.2rem 0 0.35rem 0 !important;
  }
  .fin-num-pos { color: #5eead4 !important; font-weight: 600; }
  .fin-num-neg { color: #fca5a5 !important; font-weight: 600; }
  .fin-num-zero { color: #94a3b8 !important; }
  .fin-note {
    font-size: 0.72rem !important;
    color: #64748b !important;
    margin-top: 0.4rem !important;
  }

  .stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #22d3ee 0%, #14b8a6 50%, #0d9488 100%) !important;
    color: #041016 !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 12px !important;
    box-shadow: 0 0 18px rgba(34, 211, 238, 0.25) !important;
  }
  .stButton > button[kind="secondary"] {
    border-radius: 10px !important;
    border-color: rgba(148, 163, 184, 0.35) !important;
    color: #e2e8f0 !important;
    background: rgba(15, 23, 42, 0.55) !important;
  }

  [data-testid="stSidebar"] ~ div [data-testid="stRadio"] label,
  .fin-nav-radio [data-testid="stRadio"] label {
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
    margin: 0 0 0.28rem 0 !important;
    padding: 0.4rem 0.6rem !important;
    border-radius: 10px !important;
    border: 1px solid rgba(100, 116, 139, 0.22) !important;
    border-left: 3px solid transparent !important;
    background: rgba(15, 23, 42, 0.45) !important;
    font-weight: 600 !important;
    font-size: 0.84rem !important;
    color: #cbd5e1 !important;
  }
  .fin-nav-radio [data-testid="stRadio"] label:has(input:checked) {
    border-left-color: #2dd4bf !important;
    background: rgba(13, 148, 136, 0.12) !important;
    box-shadow: 0 0 16px rgba(45, 212, 191, 0.12) !important;
    color: #f1f5f9 !important;
  }

  div[data-testid="stHorizontalBlock"]:has(.fin-metric-card) div[data-testid="column"] {
    align-self: start;
  }

  .fin-callout-warn {
    border-radius: 12px;
    border: 1px solid rgba(251, 191, 36, 0.35);
    background: rgba(30, 24, 12, 0.55);
    padding: 0.85rem 1rem;
    margin-bottom: 0.85rem;
    color: #fcd34d;
  }
  .fin-callout-info {
    border-radius: 12px;
    border: 1px solid rgba(125, 211, 252, 0.3);
    background: rgba(12, 20, 35, 0.65);
    padding: 0.85rem 1rem;
    margin-bottom: 0.85rem;
    color: #7dd3fc;
  }

  /* KI-Chat kompakter in linker Sidebar */
  .fin-lumo-title {
    margin-top: 0.15rem !important;
  }
  div[data-testid="stVerticalBlock"] div[data-testid="stChatMessage"] {
    background: rgba(15, 23, 42, 0.55);
    border: 1px solid rgba(100, 116, 139, 0.22);
    border-radius: 10px;
    padding: 0.3rem 0.5rem;
  }
  div[data-testid="stVerticalBlock"] div[data-testid="stChatInput"] textarea {
    min-height: 2.25rem !important;
  }
</style>
        """,
        unsafe_allow_html=True,
    )
