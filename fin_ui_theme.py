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

  section.main [data-testid="stMain"] .block-container {
    padding-top: 0.35rem !important;
    padding-bottom: 1rem !important;
  }

  h1, h2, h3 {
    color: #f1f5f9 !important;
    font-weight: 600 !important;
  }

  .fin-app-wrap {
    padding: 0.15rem 0.35rem 0.75rem 0.15rem;
  }

  /* Erste Spalte (Navigation): scrollbar, Inhalt bleibt nutzbar */
  div[data-testid="stHorizontalBlock"]:has(.fin-nav-radio) > div[data-testid="column"]:first-child {
    max-height: calc(100dvh - 5.25rem);
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 0.28rem;
    scrollbar-gutter: stable;
    align-self: start;
  }

  .fin-nav-heading {
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #64748b;
    margin: 0.35rem 0 0.28rem 0;
  }
  .fin-nav-heading-spaced {
    margin-top: 0.55rem !important;
    padding-top: 0.45rem;
    border-top: 1px solid rgba(94, 234, 212, 0.12);
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
    font-size: 0.78rem;
    font-weight: 700;
    color: #a5f3fc;
    margin: 0 0 0.35rem 0;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }
  .fin-lumo-greet {
    font-size: 0.72rem;
    color: #94a3b8;
    margin: 0;
    line-height: 1.3;
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
    font-size: 1.12rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #e2e8f0;
    margin: 0.2rem 0 0.65rem 0;
  }
  .fin-section-kicker {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #64748b;
    margin: 0.85rem 0 0.45rem 0;
  }

  .fin-metric-card {
    border-radius: 12px;
    border: 1px solid rgba(148, 163, 184, 0.2);
    background: linear-gradient(160deg, rgba(20, 28, 48, 0.95) 0%, rgba(10, 14, 24, 0.92) 100%);
    box-shadow:
      0 6px 20px rgba(0, 0, 0, 0.32),
      0 0 24px rgba(34, 211, 238, 0.05);
    padding: 0.72rem 0.8rem 0.6rem;
    min-height: 7.5rem;
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
    font-size: 0.8rem;
    font-weight: 700;
    color: #a5f3fc;
    margin-bottom: 0.35rem;
    letter-spacing: 0.02em;
  }
  .fin-metric-body p {
    margin: 0.12rem 0;
    font-size: 0.78rem;
    color: #cbd5e1;
    line-height: 1.35;
  }
  .fin-num-lg {
    font-size: 1.15rem;
    font-weight: 700;
    color: #f1f5f9;
    margin: 0.12rem 0 0.25rem 0 !important;
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
    margin: 0 0 0.2rem 0 !important;
    padding: 0.28rem 0.45rem !important;
    border-radius: 8px !important;
    border: 1px solid rgba(100, 116, 139, 0.22) !important;
    border-left: 3px solid transparent !important;
    background: rgba(15, 23, 42, 0.45) !important;
    font-weight: 600 !important;
    font-size: 0.74rem !important;
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

  /* Kopfzeile: gebündelter Block (st.container border=True) */
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.fin-header-title) {
    border-color: rgba(94, 234, 212, 0.16) !important;
    background: rgba(12, 18, 30, 0.55) !important;
    border-radius: 12px !important;
    padding: 0.35rem 0.55rem 0.45rem !important;
    margin-bottom: 0.55rem !important;
  }
  .fin-header-title {
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #f8fafc;
    margin: 0;
    line-height: 1.25;
    text-shadow: 0 0 14px rgba(45, 212, 191, 0.18);
  }
  .fin-header-title-gap {
    display: block;
    min-height: 0.25rem;
  }
  .fin-header-assign-hint {
    display: block;
    height: 0;
    margin: 0.2rem 0 0.05rem 0;
    border-top: 1px solid rgba(94, 234, 212, 0.1);
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.fin-header-title) [data-testid="stCheckbox"] label p {
    font-size: 0.74rem !important;
    margin: 0 !important;
  }
  .fin-top-field-label {
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #64748b;
    margin: 0 0 0.2rem 0;
    line-height: 1.2;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.fin-header-title) [data-testid="stVerticalBlock"] {
    gap: 0.2rem !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.fin-header-title) .stButton > button {
    padding: 0.32rem 0.48rem !important;
    font-size: 0.76rem !important;
    min-height: 2rem !important;
  }

  /* PDF-Upload in Kopfzeile: flach, Hinweis 200 MB seitlich */
  .fin-header-pdf-meta {
    margin: 0;
    padding: 0 0 0 0.15rem;
    font-size: 0.72rem;
    line-height: 1.25;
    color: #94a3b8;
    white-space: nowrap;
  }
  .fin-header-pdf-meta strong {
    color: #cbd5e1;
    font-weight: 600;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.fin-header-title) [data-testid="stFileUploader"] {
    margin-bottom: 0 !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.fin-header-title) [data-testid="stFileUploader"] section {
    min-height: 2.15rem !important;
    max-height: 3.25rem !important;
    padding: 0.2rem 0.45rem !important;
    border-radius: 8px !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.fin-header-title) [data-testid="stFileUploader"] section > div {
    min-height: 0 !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.fin-header-title) [data-testid="stFileUploader"] small,
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.fin-header-title) [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] p {
    display: none !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.fin-header-title) [data-testid="stFileUploader"] button {
    padding: 0.22rem 0.5rem !important;
    font-size: 0.74rem !important;
    min-height: 1.75rem !important;
  }
  /* KI-Chat kompakt unter Navigation */
  .fin-sidebar-lumo {
    margin: 0 0 0.35rem 0;
    padding: 0.35rem 0.4rem 0.45rem;
    border-radius: 10px;
    border: 1px solid rgba(94, 234, 212, 0.1);
    background: rgba(8, 12, 22, 0.45);
  }
  .fin-sidebar-lumo div[data-testid="stChatMessage"] {
    background: rgba(15, 23, 42, 0.45);
    border: 1px solid rgba(100, 116, 139, 0.18);
    border-radius: 8px;
    padding: 0.2rem 0.35rem;
    font-size: 0.78rem;
  }
  .fin-sidebar-lumo div[data-testid="stChatInput"] textarea {
    min-height: 2rem !important;
    font-size: 0.8rem !important;
  }
  .fin-sidebar-lumo .stButton > button {
    padding: 0.3rem 0.45rem !important;
    font-size: 0.74rem !important;
  }
</style>
        """,
        unsafe_allow_html=True,
    )
