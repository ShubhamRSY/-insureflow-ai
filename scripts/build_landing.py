#!/usr/bin/env python3
"""Generate the Rytera marketing site from shared fragments.

Writes src/insureflow/static/landing/*.html plus landing.css / landing.js.
Shared design tokens live in scripts/landing.css and scripts/landing.js.
Re-run after editing page bodies here:

    python scripts/build_landing.py
"""

from __future__ import annotations

from pathlib import Path

LANDING = Path(__file__).resolve().parent.parent / "src" / "insureflow" / "static" / "landing"

# ---------------------------------------------------------------------------
# Shared fragments
# ---------------------------------------------------------------------------

SPRITE = """  <svg xmlns="http://www.w3.org/2000/svg" style="display:none" aria-hidden="true">
    <symbol id="i-menu" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M4 6h16M4 12h16M4 18h16"/></symbol>
    <symbol id="i-x" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></symbol>
    <symbol id="i-arrow-right" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></symbol>
    <symbol id="i-chevron-down" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></symbol>
    <symbol id="i-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></symbol>
    <symbol id="i-check-circle" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></symbol>
    <symbol id="i-x-circle" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6M9 9l6 6"/></symbol>
    <symbol id="i-zap" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/></symbol>
    <symbol id="i-layers" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><path d="m12 2 10 5-10 5L2 7l10-5z"/><path d="M2 17l10 5 10-5M2 12l10 5 10-5"/></symbol>
    <symbol id="i-cpu" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 2v2M15 2v2M9 20v2M15 20v2M2 9h2M2 15h2M20 9h2M20 15h2"/></symbol>
    <symbol id="i-bot" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="8" width="18" height="12" rx="4"/><path d="M12 8V4M8 4h8"/><circle cx="12" cy="14" r="2"/></symbol>
    <symbol id="i-shield" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/></symbol>
    <symbol id="i-shield-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/></symbol>
    <symbol id="i-lock" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></symbol>
    <symbol id="i-file-text" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z"/><path d="M14 2v4a2 2 0 0 0 2 2h4M10 9H8M16 13H8M16 17H8"/></symbol>
    <symbol id="i-file-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z"/><path d="M14 2v4a2 2 0 0 0 2 2h4m-11 7 2 2 4-4"/></symbol>
    <symbol id="i-scan" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2M7 12h10"/></symbol>
    <symbol id="i-search" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></symbol>
    <symbol id="i-gauge" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m12 14 4-4M3.34 19a10 10 0 1 1 17.32 0"/></symbol>
    <symbol id="i-list-checks" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m3 17 2 2 4-4M3 7l2 2 4-4M13 6h8M13 12h8M13 18h8"/></symbol>
    <symbol id="i-scale" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10M12 3v18M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/></symbol>
    <symbol id="i-banknote" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/></symbol>
    <symbol id="i-chart" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v16a2 2 0 0 0 2 2h16"/><path d="M18 17V9M13 17V5M8 17v-3"/></symbol>
    <symbol id="i-building" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22v-4h6v4M8 6h.01M16 6h.01M12 6h.01M12 10h.01M16 10h.01M8 10h.01M12 14h.01M16 14h.01M8 14h.01"/></symbol>
    <symbol id="i-landmark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 22h18M6 18v-7M10 18v-7M14 18v-7M18 18v-7"/><path d="M12 2 20 7H4z"/></symbol>
    <symbol id="i-home" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/></symbol>
    <symbol id="i-car" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 0 0 2 12v4c0 .6.4 1 1 1h2"/><circle cx="7" cy="17" r="2"/><path d="M9 17h6"/><circle cx="17" cy="17" r="2"/></symbol>
    <symbol id="i-heart-pulse" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/><path d="M3.22 12H9.5l.5-1 2 4.5 2-7 1.5 3.5h5.27"/></symbol>
    <symbol id="i-briefcase" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></symbol>
    <symbol id="i-users" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></symbol>
    <symbol id="i-database" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/></symbol>
    <symbol id="i-cable" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6.3 20.3a2.4 2.4 0 0 0 3.4 0l12.6-12.6a2.4 2.4 0 0 0 0-3.4L21.7 3.7a2.4 2.4 0 0 0-3.4 0L5.7 16.3a2.4 2.4 0 0 0 0 3.4Z"/><path d="m8 12 4-4M10 14l4-4"/></symbol>
    <symbol id="i-package" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="M3.3 7 12 12l8.7-5M12 22V12"/></symbol>
    <symbol id="i-refresh" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/></symbol>
    <symbol id="i-sparkles" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9.9 2.2a.5.5 0 0 1 .9 0l1.8 4.9a1 1 0 0 0 .6.6l4.9 1.8a.5.5 0 0 1 0 .9l-4.9 1.8a1 1 0 0 0-.6.6l-1.8 4.9a.5.5 0 0 1-.9 0l-1.8-4.9a1 1 0 0 0-.6-.6L2.6 10.4a.5.5 0 0 1 0-.9l4.9-1.8a1 1 0 0 0 .6-.6z"/><path d="M20 3v4M22 5h-4M4 17v2M5 18H3"/></symbol>
    <symbol id="i-mail" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 5L2 7"/></symbol>
    <symbol id="i-calendar" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></symbol>
    <symbol id="i-globe" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></symbol>
    <symbol id="i-server" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><path d="M6 6h.01M6 18h.01"/></symbol>
    <symbol id="i-workflow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="6" height="6" rx="1"/><rect x="15" y="15" width="6" height="6" rx="1"/><path d="M21 9a6 6 0 0 0-6-6h-2M3 15a6 6 0 0 0 6 6h2M15 12v3M9 12V9"/></symbol>
    <symbol id="i-wallet" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1"/><path d="M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4"/></symbol>
    <symbol id="i-percent" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M19 5 5 19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/></symbol>
    <symbol id="i-pie" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/></symbol>
    <symbol id="i-inbox" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></symbol>
    <symbol id="i-send" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></symbol>
    <symbol id="i-sliders" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 4h-7M10 4H3M21 12h-9M8 12H3M21 20h-5M12 20H3M14 2v4M8 10v4M16 18v4"/></symbol>
    <symbol id="i-book" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></symbol>
    <symbol id="i-star" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01z"/></symbol>
    <symbol id="i-key" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6M15.5 7.5l3 3L22 7l-3-3"/></symbol>
  </svg>"""

BG = """  <div class="bg-canvas" aria-hidden="true">
    <div class="bg-grid"></div>
    <div class="glow glow-1"></div>
    <div class="glow glow-2"></div>
    <div class="glow glow-3"></div>
    <div class="glow glow-4"></div>
  </div>
  <div class="bg-noise" aria-hidden="true"></div>
  <div id="scroll-progress" aria-hidden="true"></div>"""

BRAND = """      <a class="brand" href="/" aria-label="Rytera home">
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M7 21V3h7a3.5 3.5 0 0 1 0 7H7m7 0 4 11"/></svg>
        </span>
        <span class="brand-name">Rytera<sup>&trade;</sup></span>
      </a>"""

NAV_LINKS = [
    ("/", "Home"),
    ("/pricing", "Pricing"),
    ("/platform", "Platform"),
    ("/technology", "Technology"),
    ("/underwriting", "Underwriting"),
    ("/integrations", "Integrations"),
    ("/company", "Company"),
]

NAV_ANCHORS = "\n".join(f'        <a href="{href}" data-nav>{label}</a>' for href, label in NAV_LINKS)
NAV_ANCHORS_MOBILE = "\n".join(f'      <a href="{href}" data-nav>{label}</a>' for href, label in NAV_LINKS)

HEADER = (
    """    <header id="header">
      <div class="nav-inner">
"""
    + BRAND
    + """
        <nav class="nav-desktop" aria-label="Main">
"""
    + NAV_ANCHORS
    + """
        </nav>
        <div class="nav-actions">
          <button type="button" class="btn btn-ghost btn-sm" id="open-glossary-nav" style="border:1px solid var(--border)">Glossary</button>
          <a class="nav-dash" href="/dashboard">Dashboard</a>
          <button type="button" class="btn btn-primary btn-sm" id="open-demo-nav">Book a demo</button>
        </div>
        <button class="menu-btn" id="menu-btn" aria-label="Open menu" aria-expanded="false">
          <svg class="ico" aria-hidden="true"><use href="#i-menu"/></svg>
        </button>
      </div>
    </header>
    <nav class="mobile-nav" id="mobile-nav" aria-label="Mobile">
"""
    + NAV_ANCHORS_MOBILE
    + """
      <button type="button" class="btn btn-ghost" id="open-glossary-mobile" style="text-align:left;padding:.75rem 1rem">Underwriting Glossary</button>
      <a href="/dashboard">Dashboard</a>
      <button type="button" class="btn btn-primary" id="open-demo-mobile">Book a demo</button>
    </nav>"""
)

FOOTER = (
    """    <footer>
      <div class="footer-grid">
        <div class="brand" aria-label="Rytera">
          <span class="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M7 21V3h7a3.5 3.5 0 0 1 0 7H7m7 0 4 11"/></svg>
          </span>
          <span class="brand-name">Rytera<sup>&trade;</sup></span>
        </div>
        <nav class="footer-links" aria-label="Footer">
"""
    + "\n".join(f'          <a href="{href}">{label}</a>' for href, label in NAV_LINKS)
    + """
          <a href="/dashboard">Dashboard</a>
          <button type="button" class="footer-glossary-btn" id="open-glossary-footer">Underwriting Glossary</button>
        </nav>
        <div>
          <div style="margin-bottom:.25rem">Names and private details come off before any AI sees a page.</div>
          <div style="margin-bottom:.25rem">A licensed underwriter still signs. We never invent a price.</div>
          <div>&copy; 2026 Rytera Inc. All rights reserved.</div>
        </div>
      </div>
    </footer>"""
)

MODAL = """  <div class="modal-overlay" id="demo-modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
    <div class="modal">
      <button class="modal-close" id="close-demo" aria-label="Close"><svg class="ico sm"><use href="#i-x"/></svg></button>
      <div id="modal-form-wrap">
        <h3 id="modal-title">Request a demo</h3>
        <p class="m-sub">Tell us about your team and we'll schedule a walkthrough.</p>
        <form id="demo-form" novalidate>
          <div class="field">
            <label for="d-name">Full name</label>
            <input type="text" id="d-name" name="name" placeholder="Alex Chen" required />
          </div>
          <div class="field">
            <label for="d-email">Work email</label>
            <input type="email" id="d-email" name="email" placeholder="alex@carrier.com" required />
          </div>
          <div class="field">
            <label for="d-company">Company</label>
            <input type="text" id="d-company" name="company" placeholder="Meridian Mutual" required />
          </div>
          <div class="field">
            <label for="d-vertical">What do you underwrite?</label>
            <select id="d-vertical" name="vertical">
              <option value="Commercial insurance">Commercial insurance</option>
              <option value="General liability">General liability</option>
              <option value="Commercial property">Commercial property</option>
              <option value="Commercial auto">Commercial auto</option>
              <option value="Workers' compensation">Workers' compensation</option>
              <option value="Professional liability / E&O">Professional liability / E&O</option>
              <option value="Cyber">Cyber</option>
              <option value="Excess &amp; surplus / specialty">Excess &amp; surplus / specialty</option>
              <option value="Inland &amp; ocean marine">Inland &amp; ocean marine</option>
              <option value="Personal lines">Personal lines</option>
              <option value="Mortgage lending">Mortgage lending</option>
              <option value="Commercial lending">Commercial lending</option>
              <option value="Not sure yet">Not sure yet</option>
            </select>
          </div>
          <div class="field">
            <label for="d-message">What are you hoping to automate? <span style="color:var(--muted-2);font-weight:400">(optional)</span></label>
            <textarea id="d-message" name="message" rows="3" placeholder="We are drowning in broker PDFs and want to pilot shadow mode."></textarea>
          </div>
          <div class="form-status" id="form-status" role="status"></div>
          <div class="modal-actions">
            <button type="submit" class="btn btn-primary" style="flex:1" id="demo-submit">
              Send request
              <svg class="ico sm" aria-hidden="true"><use href="#i-send"/></svg>
            </button>
            <a class="btn btn-ghost" href="/dashboard">Try dashboard</a>
          </div>
        </form>
        <p class="form-note">Prefer email? <a href="mailto:hello@ryterainc.com">hello@ryterainc.com</a> &middot; or jump straight to the <a href="/dashboard">live dashboard</a></p>
      </div>
      <div class="modal-success" id="modal-success">
        <span class="ok-ico"><svg class="ico"><use href="#i-check-circle"/></svg></span>
        <h3>Request received</h3>
        <p>Thanks &mdash; our team will reach out within one business day to schedule your walkthrough.</p>
        <a class="btn btn-ghost" href="/dashboard">Explore the dashboard now</a>
      </div>
    </div>
  </div>

  <div class="modal-overlay" id="glossary-modal" role="dialog" aria-modal="true" aria-labelledby="glossary-modal-title">
    <span id="plain" aria-hidden="true" style="display:none"></span>
    <div class="modal glossary-modal-card">
      <button class="modal-close" id="close-glossary" aria-label="Close glossary"><svg class="ico sm"><use href="#i-x"/></svg></button>
      <div class="glossary-modal-header">
        <h3 id="glossary-modal-title">The Underwriting &amp; Risk Glossary</h3>
        <p class="m-sub">50+ clear definitions across insurance underwriting, mortgage, lending, and AI governance.</p>
        <div class="glossary-modal-search">
          <svg class="ico"><use href="#i-search"/></svg>
          <input type="text" id="glossary-modal-input" placeholder="Type to filter definitions in real-time..." aria-label="Filter glossary" />
        </div>
        <div class="glossary-filters" role="tablist" aria-label="Glossary categories">
          <button type="button" class="glossary-filter-chip active" data-cat="all">All (50+)</button>
          <button type="button" class="glossary-filter-chip" data-cat="underwriting">Underwriting &amp; Risk</button>
          <button type="button" class="glossary-filter-chip" data-cat="ai">AI &amp; Architecture</button>
          <button type="button" class="glossary-filter-chip" data-cat="data">Data &amp; Oracles</button>
          <button type="button" class="glossary-filter-chip" data-cat="compliance">Compliance &amp; Governance</button>
          <button type="button" class="glossary-filter-chip" data-cat="lines">Lines &amp; Desks</button>
        </div>
      </div>
      <div class="glossary-modal-body" id="glossary-modal-list">
        <!-- Rendered dynamically by landing.js -->
      </div>
    </div>
  </div>"""


def head(title: str, desc: str, canonical: str, og_desc: str) -> str:
    return (
        '  <meta charset="UTF-8" />\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0" />\n'
        f"  <title>{title}</title>\n"
        f'  <meta name="description" content="{desc}" />\n'
        f'  <link rel="canonical" href="https://ryterainc.com/{canonical}" />\n'
        '  <meta property="og:type" content="website" />\n'
        f'  <meta property="og:url" content="https://ryterainc.com/{canonical}" />\n'
        f'  <meta property="og:title" content="{title}" />\n'
        f'  <meta property="og:description" content="{og_desc}" />\n'
        '  <meta property="og:site_name" content="Rytera" />\n'
        '  <meta property="og:image" content="https://ryterainc.com/og-image.png" />\n'
        '  <meta property="og:image:width" content="1200" />\n'
        '  <meta property="og:image:height" content="630" />\n'
        '  <meta property="og:image:alt" content="Rytera - AI underwriting platform" />\n'
        '  <meta name="twitter:card" content="summary_large_image" />\n'
        f'  <meta name="twitter:title" content="{title}" />\n'
        f'  <meta name="twitter:description" content="{og_desc}" />\n'
        '  <meta name="twitter:image" content="https://ryterainc.com/og-image.png" />\n'
        '  <link rel="icon" href="/favicon.ico" sizes="any" />\n'
        '  <link rel="icon" type="image/png" sizes="32x32" href="/favicon.png" />\n'
        '  <link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png" />\n'
        '  <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />\n'
        '  <link rel="icon" type="image/svg+xml" href="/favicon.svg" />\n'
        '  <script type="application/ld+json">\n'
        "  {\n"
        '    "@context": "https://schema.org",\n'
        '    "@type": "Organization",\n'
        '    "name": "Rytera",\n'
        '    "url": "https://ryterainc.com/",\n'
        '    "logo": "https://ryterainc.com/icon-512.png",\n'
        '    "description": "AI underwriting platform for commercial & personal lines insurance, mortgage, and lending.",\n'
        '    "email": "hello@ryterainc.com"\n'
        "  }\n"
        "  </script>\n"
        '  <link rel="preconnect" href="https://fonts.googleapis.com" />\n'
        '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />\n'
        '  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Sora:wght@400;500;600;700;800&display=swap" rel="stylesheet" />\n'
        '  <link rel="stylesheet" href="/static/landing.css" />\n'
    )


def page(title: str, desc: str, canonical: str, og_desc: str, main_html: str) -> str:
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        + head(title, desc, canonical, og_desc)
        + "</head>\n<body>\n"
        + SPRITE
        + "\n"
        + BG
        + '\n  <div class="page">\n'
        + HEADER
        + "\n\n    <main>\n"
        + main_html
        + "\n    </main>\n"
        + FOOTER
        + "\n  </div>\n\n"
        + MODAL
        + '\n  <script src="/static/landing.js" defer></script>\n</body>\n</html>\n'
    )


# ---------------------------------------------------------------------------
# Shared section builders
# ---------------------------------------------------------------------------


def sub_page_hero(label: str, h1: str, lead: str, primary: str = "book", primary_label: str = "Book a demo", secondary: str | None = None, secondary_label: str | None = None) -> str:
    btns = []
    if primary == "book":
        btns.append('      <button type="button" class="btn btn-primary" id="open-demo-hero">Book a demo</button>')
    elif primary == "dashboard":
        btns.append('      <a class="btn btn-primary" href="/dashboard">Open the live dashboard</a>')
    if secondary and secondary_label:
        btns.append(f'      <a class="btn btn-ghost" href="{secondary}">{secondary_label}</a>')
    cta = ""
    if btns:
        cta = '\n    <div class="cta">\n' + "\n".join(btns) + "\n    </div>"
    return (
        '      <section class="page-hero">\n'
        '        <div class="reveal">\n'
        f'          <p class="section-label">{label}</p>\n'
        f"          <h1>{h1}</h1>\n"
        f'          <p class="lead">{lead}</p>\n' + cta + "\n        </div>\n"
        "      </section>"
    )


def pricing_section() -> str:
    """Competitor-style plans + feature matrix, priced per bind-ready memo."""
    check = '<svg class="ico sm yes" aria-hidden="true"><use href="#i-check"/></svg>'
    dash = '<span class="cell-dash" aria-hidden="true">&mdash;</span>'
    soon = '<span class="cell-soon">Coming soon</span>'
    extra = '<span class="cell-fee">Pass-through + 15%</span>'
    incl = '<span class="cell-incl">Included</span>'
    return f"""      <section id="pricing">
        <div class="reveal">
          <p class="section-label">Plans &amp; pricing</p>
          <h2>Priced per memo you can sign &mdash; not per data pull</h2>
          <p class="section-desc">You will not buy fake outside data at Desk prices, a demo rate book sold as your state filing, or a policy-system bind you still have to type in by hand. Desk and above stop (fail-closed) unless those three are real. Practice mode stays free. <a href="#plain">What these words mean.</a></p>
        </div>
        <div class="buy-gates reveal">
          <article class="buy-gate">
            <p class="gate-kicker gate-no">They will not buy if</p>
            <h3>Outside data is fake</h3>
            <p>Oracles means outside checks: prior claims, workers-comp history, catastrophe. Fake clean history at Desk prices is a non-starter. Desk and above need live feeds. Missing accounts refer the file instead of inventing a clean loss run.</p>
          </article>
          <article class="buy-gate">
            <p class="gate-kicker gate-no">They will not buy if</p>
            <h3>The price isn&rsquo;t from your book</h3>
            <p>Your SERFF / carrier leaf filings means the rates you filed with the state. A demo book is not that. Desk and above quote only after you load yours. Until then the quote is ineligible &mdash; not silently priced off our demo.</p>
          </article>
          <article class="buy-gate">
            <p class="gate-kicker gate-no">They will not buy if</p>
            <h3>You still have to re-type the quote</h3>
            <p>Bind means issue the policy. No re-key means the full quote lands in Guidewire (or your policy system) &mdash; coverages, filing ID, conditions, terms. A pretend connection is refused.</p>
          </article>
        </div>
        <div class="pricing-grid reveal">
          <article class="price-card">
            <p class="price-tier">Pilot</p>
            <p class="price-amount">$0<span>/mo</span></p>
            <p class="price-sub">5 memos included &middot; then $95 each</p>
            <p class="price-ideal">Shadow pilots &amp; early-stage desks under 10 submissions / month</p>
            <ul class="price-bullets">
              <li>{check} Bind-ready AI memo (accept / refer / decline)</li>
              <li>{check} Simulated oracles + demo rate book (honest)</li>
              <li>{check} Subjectivities &amp; bind-readiness checklist</li>
              <li>{check} Encrypted audit trail &middot; bind off</li>
            </ul>
            <a class="btn btn-ghost" href="/dashboard">Get started free</a>
          </article>
          <article class="price-card">
            <p class="price-tier">Desk</p>
            <p class="price-amount">$799<span>/mo</span></p>
            <p class="price-sub">25 memos included &middot; then $55 each</p>
            <p class="price-ideal">Line desks processing 15&ndash;40 submissions / month</p>
            <ul class="price-bullets">
              <li>{check} Live CLUE / NCCI / A+ / CAT / ISO &mdash; no simulated fallback</li>
              <li>{check} Your SERFF / carrier leaf filings (not our pilot book)</li>
              <li>{check} Appetite &amp; selection gates</li>
              <li>{check} Live PAS bind when Guidewire is connected</li>
            </ul>
            <button type="button" class="btn btn-ghost" data-open-demo>Book a demo</button>
          </article>
          <article class="price-card featured">
            <p class="price-badge">Most popular</p>
            <p class="price-tier">Book</p>
            <p class="price-amount">$2,490<span>/mo</span></p>
            <p class="price-sub">80 memos included &middot; then $38 each</p>
            <p class="price-ideal">Books processing 50&ndash;120 submissions / month</p>
            <ul class="price-bullets">
              <li>{check} Guidewire / BriteCore bind &mdash; full terms, no re-key</li>
              <li>{check} Oracles included (fair use)</li>
              <li>{check} Portfolio concentration &amp; reinsurance</li>
              <li>{check} Dedicated onboarding of your rate book + PAS</li>
            </ul>
            <button type="button" class="btn btn-primary" data-open-demo>Get started</button>
          </article>
          <article class="price-card">
            <p class="price-tier">Enterprise</p>
            <p class="price-amount">From $6,500<span>/mo</span></p>
            <p class="price-sub">Custom volume &middot; $22&ndash;$32 per memo</p>
            <p class="price-ideal">Carriers &amp; MGAs at 100+ submissions / month, multi-org</p>
            <ul class="price-bullets">
              <li>{check} Private VPC / SSO / examiner export</li>
              <li>{check} Custom SERFF / multi-company rate books</li>
              <li>{check} Dedicated CSM &amp; priority SLA</li>
              <li>{check} Broker portal priority</li>
            </ul>
            <a class="btn btn-ghost" href="mailto:hello@ryterainc.com?subject=Rytera%20Enterprise">Talk to sales</a>
          </article>
        </div>

        <div class="matrix-wrap reveal">
          <table class="price-matrix">
            <thead>
              <tr>
                <th scope="col">Features &amp; benefits</th>
                <th scope="col">Pilot</th>
                <th scope="col">Desk</th>
                <th scope="col">Book</th>
                <th scope="col">Enterprise</th>
              </tr>
            </thead>
            <tbody>
              <tr><th scope="row">Monthly subscription</th><td>$0</td><td>$799</td><td>$2,490</td><td>From $6,500</td></tr>
              <tr><th scope="row">Included memos / month</th><td>5</td><td>25</td><td>80</td><td>Custom</td></tr>
              <tr><th scope="row">Additional memo</th><td>$95</td><td>$55</td><td>$38</td><td>$22&ndash;$32</td></tr>
              <tr><th scope="row">Blended cost at included volume</th><td>$95</td><td>~$32</td><td>~$31</td><td>$22&ndash;$32</td></tr>
              <tr><th scope="row">Ideal for</th><td>Pilots &amp; low volume</td><td>15+ memos / mo</td><td>50+ memos / mo</td><td>100+ memos / mo</td></tr>
              <tr><th scope="row">Shadow pilot (bind off until you cut over)</th><td>{check}</td><td>{check}</td><td>{check}</td><td>{check}</td></tr>
              <tr><th scope="row">AI UW memo, findings &amp; credit / loss insights</th><td>{check}</td><td>{check}</td><td>{check}</td><td>{check}</td></tr>
              <tr><th scope="row">Subjectivities, open conditions &amp; bind readiness</th><td>{check}</td><td>{check}</td><td>{check}</td><td>{check}</td></tr>
              <tr><th scope="row">Appetite, selection &amp; moral-hazard gates</th><td>{check}</td><td>{check}</td><td>{check}</td><td>{check}</td></tr>
              <tr><th scope="row">Filing-style rating (ISO / NCCI / leaf filings)</th><td>Demo book only</td><td>Your SERFF book required</td><td>Your SERFF book required</td><td>SERFF / multi-company</td></tr>
              <tr><th scope="row">Live oracles &mdash; CLUE, NCCI, A+, CAT, ISO</th><td>Simulated (honest)</td><td>Live only &middot; {extra}</td><td>{incl}</td><td>{incl}</td></tr>
              <tr><th scope="row">Fail-closed if oracles simulated</th><td>n/a</td><td>{check}</td><td>{check}</td><td>{check}</td></tr>
              <tr><th scope="row">Policy admin &mdash; Guidewire, BriteCore, Duck Creek</th><td>Bind off</td><td>Live bind, no re-key</td><td>{incl}</td><td>{incl}</td></tr>
              <tr><th scope="row">Full PAS payload (limits, filing, subjectivities)</th><td>{dash}</td><td>{check}</td><td>{check}</td><td>{check}</td></tr>
              <tr><th scope="row">Portfolio concentration &amp; reinsurance</th><td>{dash}</td><td>{dash}</td><td>{check}</td><td>{check}</td></tr>
              <tr><th scope="row">Encrypted audit bundle &amp; examiner export</th><td>Basic</td><td>{check}</td><td>{check}</td><td>SSO / VPC</td></tr>
              <tr><th scope="row">Broker / producer portal</th><td>{dash}</td><td>{soon}</td><td>{soon}</td><td>Priority</td></tr>
              <tr><th scope="row">Dedicated onboarding &amp; client success</th><td>{dash}</td><td>{dash}</td><td>{check}</td><td>{check}</td></tr>
              <tr><th scope="row">Enterprise SLA &amp; priority support</th><td>{dash}</td><td>{dash}</td><td>{dash}</td><td>{check}</td></tr>
            </tbody>
          </table>
        </div>
        <p class="price-footnote reveal">Oracle vendor fees (LexisNexis, ISO, NCCI, and similar) pass through at cost on Pilot and Desk. Book and Enterprise include fair-use live feeds; overage is billed at vendor cost. Desk+ will not quote on the InsureFlow pilot book or bind through a simulated PAS. Shadow bind stays off until licensed UW approves cutover. Prices in USD, billed monthly, cancel anytime on Pilot &amp; Desk.</p>
      </section>"""


def pricing_main() -> str:
    impl = """      <section id="go-live">
        <div class="reveal">
          <p class="section-label">What Desk and above actually turn on</p>
          <h2>Product, not a pretty demo around fake data</h2>
          <p class="section-desc">Three real connections: live outside data, your filed rate book, and the system that issues the policy. Until those three are live, Rytera stays on Pilot &mdash; it will not pretend otherwise. <a href="#plain">In plain English.</a></p>
        </div>
        <div class="feature-grid reveal">
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-search"/></svg></span><h3>1. Live outside data</h3><p>Connect your real claim-history and catastrophe accounts. Desk and above will not use pretend-clean history. Missing accounts become a finding, not a green screen.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-layers"/></svg></span><h3>2. Your rate book</h3><p>Load the rates you filed with the state (SERFF). Our demo book cannot price a Desk quote and call it yours.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-zap"/></svg></span><h3>3. Issue without re-typing</h3><p>The policy system (Guidewire or similar) receives the full quote &mdash; limits, deductibles, filing ID, conditions, premium. If the connection is still pretend, bind is refused.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-shield-check"/></svg></span><h3>You can check before you pay</h3><p>The plan page shows whether outside data, your rate book, and the policy system are actually ready. Buyers can verify. We do not hide a demo behind a paid label.</p></div>
        </div>
      </section>"""
    return (
        sub_page_hero(
            "Pricing",
            "Plans that only charge when the data is real",
            "Pilot is free and honest: practice outside data, a demo rate book, and nothing issued. Desk, Book, and Enterprise stop unless live outside data, your filed rates, and policy-system bind without re-key are in place.",
            primary="book",
            secondary="/dashboard",
            secondary_label="Open the live dashboard",
        )
        + "\n\n"
        + pricing_section()
        + "\n\n"
        + impl
        + "\n\n"
        + page_close()
    )


def privacy_band() -> str:
    return """      <section id="privacy" class="privacy-band">
        <div class="reveal">
          <p class="section-label">A quiet promise</p>
          <h2>Named insureds never leave the gate.</h2>
          <p class="section-desc"><strong>Named insured</strong> means the person or company on the policy. <strong>PII</strong> means private details like Social Security numbers. Before any AI (a language model) looks at a file, we remove those. Your underwriter still sees the real file. The AI does not. Their names never leave the gate. Same promise on insurance, mortgage, and lending.</p>
        </div>
      </section>"""


def plain_english_section() -> str:
    return """      <section id="plain">
        <div class="reveal">
          <p class="section-label">In plain English</p>
          <h2>Every technical word on this site, said simply.</h2>
          <p class="section-desc">If a page used a desk word, this is what it means. No one should need a glossary from another company to read ours.</p>
        </div>
        <dl class="plain-grid reveal">
          <div class="plain-term"><dt>Underwriter</dt><dd>The licensed person who decides yes, no, or not yet on a risk. Rytera drafts. They still sign.</dd></div>
          <div class="plain-term"><dt>Carrier / MGA</dt><dd>Carrier = the insurance company that takes the risk. MGA = a specialist team allowed to underwrite on a carrier&rsquo;s behalf.</dd></div>
          <div class="plain-term"><dt>Submission</dt><dd>The pile a broker sends when they want a quote: PDFs, spreadsheets, emails, photos.</dd></div>
          <div class="plain-term"><dt>The memo (bind-ready)</dt><dd>A clear recommendation you can read and sign. Bind means issue the policy. Ready means you could, after you sign &mdash; not a pile of notes you still have to rewrite.</dd></div>
          <div class="plain-term"><dt>Practice mode (shadow)</dt><dd>Run Rytera on real files without issuing a policy. Prove it on your book. Go live when you say so.</dd></div>
          <div class="plain-term"><dt>Appetite</dt><dd>What your company is willing to write. Files that don&rsquo;t fit get referred out before they eat a day.</dd></div>
          <div class="plain-term"><dt>Triage</dt><dd>Sorting the queue so the files that need a human rise first, and the obvious no&rsquo;s don&rsquo;t steal the morning.</dd></div>
          <div class="plain-term"><dt>Loss run / SOV / ACORD</dt><dd>Loss run = history of claims. SOV (schedule of values) = the list of buildings and what they&rsquo;re worth. ACORD = a standard insurance form brokers already use.</dd></div>
          <div class="plain-term"><dt>Limit, deductible, exposure</dt><dd>Limit = the most the policy would pay. Deductible = what the customer pays first. Exposure = how much is actually at risk.</dd></div>
          <div class="plain-term"><dt>COPE</dt><dd>Construction, Occupancy, Protection, Exposure &mdash; the four things a property underwriter always checks (how it&rsquo;s built, who uses it, fire protection, what sits next door).</dd></div>
          <div class="plain-term"><dt>Oracles (CLUE, NCCI, A+, CAT)</dt><dd>Outside data checks: prior claims, workers-comp history, catastrophe risk. We only treat them as real when your accounts are connected. We never fake a clean history.</dd></div>
          <div class="plain-term"><dt>Rate book / SERFF / filing</dt><dd>Your official prices, as filed with the state. SERFF is the system states use to receive those filings. We will not quote off a demo book and call it yours.</dd></div>
          <div class="plain-term"><dt>Policy admin / Guidewire / PAS</dt><dd>The system that actually issues the policy. Bind without re-key means the quote lands there in full &mdash; you should not have to type it again.</dd></div>
          <div class="plain-term"><dt>IMAP, S3, SFTP</dt><dd>How files already arrive: email (IMAP), a cloud folder (S3), or a secure drop (SFTP). We meet the file where it lives.</dd></div>
          <div class="plain-term"><dt>AI / LLM</dt><dd>A language model &mdash; software that can read and write. We use it only where judgment is needed. It never issues a policy. Names come off first.</dd></div>
          <div class="plain-term"><dt>Zero Token Architecture</dt><dd>Most steps are ordinary rules and checks (no AI bill). AI is the last resort, counted, and never used to invent a fact.</dd></div>
          <div class="plain-term"><dt>Human-in-the-loop</dt><dd>A person stays in charge. Software proposes. A licensed underwriter disposes. Every change they make is recorded.</dd></div>
          <div class="plain-term"><dt>Paper trail / exam pack</dt><dd>A sealed record of what was read, checked, and signed. When a regulator asks why this file, you hand them that &mdash; not a story from three shared drives.</dd></div>
          <div class="plain-term"><dt>PII / de-identification</dt><dd>Private details: names, Social Security numbers, tax IDs, dates of birth. Stripping them before AI sees the page is de-identification.</dd></div>
          <div class="plain-term"><dt>Catalog vs live</dt><dd>Catalog = we show the product, but we will not pretend we can price or bind it yet. Live = your real rates and connections are in, so a quote is honest.</dd></div>
          <div class="plain-term"><dt>Line desk vs staff desk</dt><dd>Line underwriters work the files in the branch. Staff underwriters at home office set the rules the line desk follows.</dd></div>
          <div class="plain-term"><dt>Filing-grade</dt><dd>Priced from your official, state-filed rates &mdash; not a demo book, not a guess.</dd></div>
          <div class="plain-term"><dt>Tokens</dt><dd>The unit an AI vendor bills. &ldquo;Zero token&rdquo; means that step used ordinary software, so there is no AI bill and the answer is repeatable.</dd></div>
          <div class="plain-term"><dt>Locked files / who can see what</dt><dd>Fernet = files stored locked. JWT / RBAC = only the right people in your company can open them. SHA-256 = a seal so nobody can quietly change the record.</dd></div>
          <div class="plain-term"><dt>Fail-closed</dt><dd>If a real data feed is missing, we stop or refer the file. We do not invent a clean history so the screen looks pretty.</dd></div>
          <div class="plain-term"><dt>Re-key</dt><dd>Typing the same quote into another system by hand. Bind without re-key means the policy system receives the full quote.</dd></div>
          <div class="plain-term"><dt>Subjectivities</dt><dd>Conditions that must be true before the policy can go live (an inspection, a missing form, a signed warranty).</dd></div>
          <div class="plain-term"><dt>Authority matrix</dt><dd>Who is allowed to sign what size of risk. A junior underwriter cannot silently bind a jumbo account.</dd></div>
          <div class="plain-term"><dt>IVANS / SharePoint / Drive</dt><dd>Industry mailboxes and cloud folders where files already live. We connect when you contract them; until then we do not pretend they are live.</dd></div>
          <div class="plain-term"><dt>GL, WC, D&amp;O, E&amp;O</dt><dd>General liability, workers&rsquo; compensation, directors &amp; officers, errors &amp; omissions &mdash; common commercial covers. We say the long name first.</dd></div>
          <div class="plain-term"><dt>UL, OPD, CI, UBI</dt><dd>Universal life, outpatient (day-to-day doctor visits), critical illness, usage-based insurance (price from how you drive). Catalog until we can honestly price them.</dd></div>
          <div class="plain-term"><dt>ISO / AAIS / NCCI</dt><dd>Industry groups that publish standard rates and class codes. Carriers start there, then add their own expenses and profit.</dd></div>
          <div class="plain-term"><dt>E&amp;S (excess &amp; surplus)</dt><dd>Risks the regular market will not write. A specialist market can, with extra checks on who is allowed to bind.</dd></div>
          <div class="plain-term"><dt>TRID, Reg Z, HMDA / ECOA, Reg B</dt><dd>Mortgage and lending fairness rules: clear closing costs, honest credit pricing, equal treatment, and a written reason if we say no.</dd></div>
          <div class="plain-term"><dt>MVR / CLUE / HO-3</dt><dd>MVR = driving record. CLUE = prior home/auto claims. HO-3 = a common homeowners policy form.</dd></div>
          <div class="plain-term"><dt>Replacement cost</dt><dd>What it would cost to rebuild, not what the building would sell for. A small house cannot claim a warehouse rebuild number.</dd></div>
          <div class="plain-term"><dt>Cross-field check</dt><dd>Two facts on the same file have to be able to be true together. Payroll needs people. A license cannot be issued after the policy starts.</dd></div>
          <div class="plain-term"><dt>EXIF / ELA</dt><dd>EXIF = the camera tag on a photo (who saved it, when). ELA = JPEG error-level analysis &mdash; a local paste often leaves a hotter recompress scar than an original shot.</dd></div>
          <div class="plain-term"><dt>Fraud ring / graph net</dt><dd>Files linked by the same phone, address, tax ID, or IP. A small neural net on that graph scores whether the cluster looks like a ring &mdash; not a guess from a single file.</dd></div>
          <div class="plain-term"><dt>Telematics / cyber scan</dt><dd>Telematics = what the car actually did (miles, hard brakes). Cyber scan = an outside look at a domain. We compare those to the questionnaire only when the feed is live.</dd></div>
          <div class="plain-term"><dt>Citation gate</dt><dd>A critical number without a page, box, or source ref is not a fact. It fails straight-through processing and stays off the bind-ready memo until grounded.</dd></div>
          <div class="plain-term"><dt>Self-RAG / HyDE</dt><dd>Self-RAG = retrieve, ask if the context is enough, retrieve again if not. HyDE = search with a hypothetical guideline paragraph when the desk question is too short for vector match.</dd></div>
          <div class="plain-term"><dt>Glass box</dt><dd>Click a value, see the page highlight. Warm color means low confidence. Approve still needs a licensed person.</dd></div>
          <div class="plain-term"><dt>Zero-hallucination gate</dt><dd>Target: zero uncited money, limits, or totals on a bind-ready memo. Anything invented is stripped and the file is referred. We do not rubber-stamp a pretty number.</dd></div>
        </dl>
      </section>"""


def validation_section() -> str:
    return """      <section id="checks">
        <div class="reveal">
          <p class="section-label">How we catch a wrong number</p>
          <h2>A figure that looks legal can still be impossible.</h2>
          <p class="section-desc">These checks actually run. We do not list science we have not built. If two facts cannot both be true, or we are not sure we read the number, a person sees it. <a href="#plain">Words of the desk.</a></p>
        </div>
        <div class="challenge-list reveal">
          <article class="challenge-row">
            <div class="challenge-pain"><h3>Related facts have to agree</h3><p>A driver license issued after the policy starts. Payroll of $5M with zero employees. The deductible bigger than the limit.</p></div>
            <div class="challenge-fix"><span class="fix-label">What Rytera does</span><p>Cross-field rules. If two numbers on the same file cannot both be true, the memo does not swallow them. You see the bruise.</p></div>
          </article>
          <article class="challenge-row">
            <div class="challenge-pain"><h3>Size has to match value</h3><p>A 1,200 sq ft house claiming $15M to rebuild is not the same as a warehouse. $15M can be right &mdash; just not for that building.</p></div>
            <div class="challenge-fix"><span class="fix-label">What Rytera does</span><p>Conditional bounds. Rebuild cost is checked against square footage. A small dwelling cannot wear a commercial number quietly.</p></div>
          </article>
          <article class="challenge-row">
            <div class="challenge-pain"><h3>The same figure, twice</h3><p>Page 1 says $500,000 incurred. Page 4 says $120,000. Someone has to notice.</p></div>
            <div class="challenge-fix"><span class="fix-label">What Rytera does</span><p>If two reads disagree, we do not pick the pretty one. Disagreement goes to you. Low confidence never glides into a yes.</p></div>
          </article>
          <article class="challenge-row">
            <div class="challenge-pain"><h3>It has to live on a page</h3><p>A diagnosis, an exclusion, a total &mdash; if we cannot point at the file, it is not a fact.</p></div>
            <div class="challenge-fix"><span class="fix-label">What Rytera does</span><p>Every extraction cites the page. Outside claim history and driving records are used only when your accounts are connected. We never invent a clean history.</p></div>
          </article>
          <article class="challenge-row">
            <div class="challenge-pain"><h3>A photo can lie</h3><p>A repaired roof in Photoshop is not an inspection. Messaging apps strip the camera tag. Someone has to notice.</p></div>
            <div class="challenge-fix"><span class="fix-label">What Rytera does</span><p>We read EXIF / ELA software tags and JPEG recompress scars (error-level analysis). Edit software or a local paste gets flagged. We ask for the original camera file. We do not claim a crime lab.</p></div>
          </article>
          <article class="challenge-row">
            <div class="challenge-pain"><h3>The same ring, new letterhead</h3><p>A declined file comes back under a cousin&rsquo;s name, same phone, same drop address.</p></div>
            <div class="challenge-fix"><span class="fix-label">What Rytera does</span><p>A graph net links files that share a phone, email, tax ID, address, or IP, then scores the cluster. Isolated files stay quiet. Rings do not.</p></div>
          </article>
          <article class="challenge-row">
            <div class="challenge-pain"><h3>The questionnaire is not the car</h3><p>Stated mileage, MFA &ldquo;yes&rdquo; on a cyber form &mdash; easy to type, hard to live.</p></div>
            <div class="challenge-fix"><span class="fix-label">What Rytera does</span><p>When a connected-car or vulnerability-scan account is live, we compare the answers to the feed. Simulated never invents a clean score. Missing keys become a finding, not a green light.</p></div>
          </article>
        </div>
      </section>"""


def contact_section() -> str:
    return """      <section id="contact">
        <div class="contact-box reveal">
          <p class="section-label" style="justify-content:center;margin-left:auto;margin-right:auto;">We saved you a seat</p>
          <h2>Bring a real file. Leave with your evening.</h2>
          <p>Thirty minutes. Your messy submission. Practice mode on &mdash; nothing goes live until you say so. You still sign. We just stop the hunt.</p>
          <div class="cta" style="justify-content:center;">
            <button type="button" class="btn btn-primary" id="open-demo-contact">Book a demo</button>
            <a class="btn btn-ghost" href="/dashboard">Open the live dashboard</a>
          </div>
          <p style="margin-top:1.5rem;margin-bottom:0;font-size:.875rem">
            Prefer email? <a class="contact-email" href="mailto:hello@ryterainc.com">hello@ryterainc.com</a>
          </p>
        </div>
      </section>"""


def page_close() -> str:
    return privacy_band() + "\n\n" + contact_section()


def hero_home() -> str:
    return """      <section class="hero" id="top">
        <div class="hero-grid">
          <div class="reveal">
            <div class="hero-badge">
              <span class="dot"></span>
              AI Underwriting &amp; Risk Intelligence &middot; Production Ready
            </div>
            <h1>Stop hunting submissions.<br /><span class="gradient">Start underwriting.</span></h1>
            <p class="lead">
              You didn&rsquo;t take this job to hunt through messy broker dumps and Excel tables at midnight.
              Rytera extracts data, verifies calculations, and prices from state-filed manuals to deliver a <strong>decision-ready memo you can actually sign</strong>.
            </p>
            <p class="brand-line">Every fact grounded with provenance. Zero invented rates. A licensed underwriter still signs.</p>
            <div class="punch-row" aria-hidden="true">
              <span>99.8% Extraction Fidelity</span>
              <span>Zero-Token Architecture</span>
              <span>100% Licensed UW Sign-Off</span>
              <span>Audit-Sealed Paper Trail</span>
            </div>
            <div class="cta">
              <button type="button" class="btn btn-primary" id="open-demo-hero">
                Book a demo
                <svg class="ico sm" aria-hidden="true"><use href="#i-arrow-right"/></svg>
              </button>
              <button type="button" class="btn btn-ghost" id="open-glossary-hero">
                <svg class="ico sm" aria-hidden="true"><use href="#i-search"/></svg>
                Underwriting Glossary
              </button>
              <a class="btn btn-ghost" href="/dashboard">Open Live Dashboard</a>
            </div>
            <div class="hero-audience" aria-label="Built for">
              <span class="audience-pill"><svg class="ico sm"><use href="#i-building"/></svg> Commercial Insurance</span>
              <span class="audience-pill"><svg class="ico sm"><use href="#i-layers"/></svg> MGAs &amp; Programs</span>
              <span class="audience-pill"><svg class="ico sm"><use href="#i-home"/></svg> Mortgage Underwriting</span>
              <span class="audience-pill"><svg class="ico sm"><use href="#i-banknote"/></svg> Credit &amp; Lending</span>
            </div>
          </div>
          <div class="hero-media reveal">
            <div class="hero-halo" aria-hidden="true"></div>
            <div class="mockup" aria-hidden="true">
              <div class="mock-bar">
                <span class="mock-dots"><i></i><i></i><i></i></span>
                <span class="mock-url"><svg class="ico"><use href="#i-lock"/></svg> app.rytera.ai/dashboard</span>
              </div>
              <div class="mock-body">
                <div class="mock-side">
                  <span class="side-item active"><svg class="ico"><use href="#i-inbox"/></svg> Queue</span>
                  <span class="side-item"><svg class="ico"><use href="#i-workflow"/></svg> Workbench</span>
                  <span class="side-item"><svg class="ico"><use href="#i-pie"/></svg> Portfolio</span>
                  <span class="side-item"><svg class="ico"><use href="#i-cable"/></svg> Integrations</span>
                  <span class="side-item"><svg class="ico"><use href="#i-database"/></svg> Oracles</span>
                  <span class="side-item"><svg class="ico"><use href="#i-key"/></svg> Registry</span>
                  <span class="side-item brand-tag"><span>Pacific Coast Underwriters<br/>Practice mode &middot; nothing live yet</span></span>
                </div>
                <div class="mock-main">
                  <div class="m-head">
                    <span class="m-title">Submission #1052 &middot; <span>Pacific Coast Supply Co</span></span>
                    <span class="m-badge">Ready to sign</span>
                  </div>
                  <div class="m-stages">
                    <span class="m-stage done"><svg class="ico"><use href="#i-check"/></svg> Triage 84</span>
                    <span class="m-stage done"><svg class="ico"><use href="#i-check"/></svg> Appetite &amp; UWG</span>
                    <span class="m-stage done"><svg class="ico"><use href="#i-check"/></svg> COPE B</span>
                    <span class="m-stage done"><svg class="ico"><use href="#i-check"/></svg> Provenance</span>
                    <span class="m-stage done"><svg class="ico"><use href="#i-check"/></svg> Proposed memo</span>
                    <span class="m-stage pending">Sign-off / Override</span>
                  </div>
                  <div class="m-progress">
                    <div class="m-prog-label"><span>Field-level verification &amp; attribution</span><span>16 / 16 pages grounded &middot; 99.8% conf</span></div>
                    <div class="m-bar"><span style="width:100%"></span></div>
                  </div>
                  <div class="m-grid">
                    <div class="m-cell"><span class="k">COPE grade</span><span class="v">Preferred &middot; Page 4</span></div>
                    <div class="m-cell"><span class="k">Recommendation</span><span class="v accept">ACCEPT &middot; UWG OK</span></div>
                    <div class="m-cell"><span class="k">Indicated premium</span><span class="v">$46,890 &middot; Filed Rate</span></div>
                    <div class="m-cell"><span class="k">Authority &amp; Override</span><span class="v" style="color:var(--sky)">Licensed Sign-off</span></div>
                  </div>
                  <div class="m-foot">
                    <span class="m-audit"><svg class="ico"><use href="#i-shield-check"/></svg> Immutable SHA-256 ledger verified</span>
                    <span class="m-zta"><svg class="ico"><use href="#i-zap"/></svg> Deterministic guardrails &middot; Fail-closed</span>
                  </div>
                </div>
              </div>
            </div>
            <div class="float-chip fc-1" aria-hidden="true">
              <span class="fc-ico"><svg class="ico"><use href="#i-file-check"/></svg></span>
              <span><span class="fc-t" style="display:block">Verbatim Attribution</span><span class="fc-s">Every fact cited to original page &amp; box</span></span>
            </div>
            <div class="float-chip fc-2" aria-hidden="true">
              <span class="fc-ico sky"><svg class="ico"><use href="#i-zap"/></svg></span>
              <span><span class="fc-t" style="display:block">Deterministic Guardrails</span><span class="fc-s">Hard UWG rules &middot; 0% synthetic rates</span></span>
            </div>
            <div class="float-chip fc-3" aria-hidden="true">
              <span class="fc-ico violet"><svg class="ico"><use href="#i-shield"/></svg></span>
              <span><span class="fc-t" style="display:block">Human-in-the-Loop</span><span class="fc-s">AI proposes &middot; underwriter signs or overrides</span></span>
            </div>
          </div>
        </div>
        <div class="trust-strip reveal" aria-label="Why you can trust Rytera">
          <span class="trust-item"><svg class="ico sm"><use href="#i-check"/></svg> Licensed human sign-off</span>
          <span class="trust-item"><svg class="ico sm"><use href="#i-check"/></svg> 0% hallucinated rates &mdash; state-filed pricing only</span>
          <span class="trust-item"><svg class="ico sm"><use href="#i-check"/></svg> Practice shadow mode &mdash; zero risk to live books</span>
          <span class="trust-item"><svg class="ico sm"><use href="#i-check"/></svg> Full PII de-identification before model access</span>
          <span class="trust-item"><svg class="ico sm"><use href="#i-check"/></svg> Bidirectional citation grounding on every number</span>
          <span class="trust-item"><svg class="ico sm"><use href="#i-check"/></svg> Fernet-encrypted audit manifest</span>
        </div>
        <div class="stats reveal" aria-label="Key Performance Indicators">
          <div class="stat"><span class="num" data-target="99.8" data-decimals="1" data-suffix="%">99.8%</span><span>Extraction Fidelity &amp; Grounding</span></div>
          <div class="stat"><span class="num" data-target="85" data-suffix="%+">85%+</span><span>Faster Submission Turnaround</span></div>
          <div class="stat"><span class="num" data-target="0" data-suffix="%">0%</span><span>Invented Prices or Hallucinated Facts</span></div>
          <div class="stat"><span class="num" data-target="100" data-suffix="%">100%</span><span>Licensed Underwriter Sign-Off</span></div>
        </div>
      </section>"""


def marquee_section() -> str:
    return """      <section id="marquee" style="padding-top:0;padding-bottom:3.5rem;border-bottom:none;">
        <p class="section-label reveal" style="justify-content:center;margin-left:auto;margin-right:auto;">Seamlessly connecting with your core systems, rate filings, and external data oracles.</p>
        <div class="marquee-wrap reveal" aria-hidden="true">
          <div class="marquee-track" id="marquee-track"></div>
        </div>
      </section>"""


def desks_section() -> str:
    return """      <section id="desks">
        <div class="reveal">
          <p class="section-label">Unified Platform</p>
          <h2>Unified Underwriting Across Insurance, Mortgage, and Lending</h2>
          <p class="section-desc">One consistent, auditable workbench across all your risk desks. We extract the submission, verify the data, and rate from your official state-filed manuals. Software proposes &mdash; licensed professionals decide.</p>
        </div>
        <div class="audience-grid reveal" style="grid-template-columns:repeat(2,minmax(0,1fr))">
          <article class="audience-card ac-blue">
            <span class="ac-ico"><svg class="ico" aria-hidden="true"><use href="#i-building"/></svg></span>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.4rem">
              <p class="who" style="margin:0">Commercial Lines</p>
              <span class="lob-tag live">Live Rating</span>
            </div>
            <h3>Commercial P&amp;C &amp; Specialty</h3>
            <p>Property, casualty, GL, workers' comp, commercial auto, D&amp;O, and specialty lines. Ingests ACORD XML, broker PDFs, loss runs, and SOVs into ISO-style rating build-ups.</p>
          </article>
          <article class="audience-card ac-green">
            <span class="ac-ico"><svg class="ico" aria-hidden="true"><use href="#i-home"/></svg></span>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.4rem">
              <p class="who" style="margin:0">Residential &amp; Commercial</p>
              <span class="lob-tag live">GSE Compliant</span>
            </div>
            <h3>Mortgage Underwriting</h3>
            <p>Income, assets, 1040/W-2 tax packs, bank statements, and appraisals. Evaluates DTI/LTV and Fannie/Freddie guidelines with strict cross-field reconciliation.</p>
          </article>
          <article class="audience-card ac-amber">
            <span class="ac-ico"><svg class="ico" aria-hidden="true"><use href="#i-banknote"/></svg></span>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.4rem">
              <p class="who" style="margin:0">Credit &amp; Working Capital</p>
              <span class="lob-tag live">Risk Pricing</span>
            </div>
            <h3>Consumer &amp; Commercial Lending</h3>
            <p>Business loan applications, credit pulls, and balance sheets. If required historical data is missing, we flag a refer instead of assuming clean credit.</p>
          </article>
          <article class="audience-card ac-violet">
            <span class="ac-ico"><svg class="ico" aria-hidden="true"><use href="#i-shield-check"/></svg></span>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.4rem">
              <p class="who" style="margin:0">Governance &amp; Delegation</p>
              <span class="lob-tag live">Authority Matrix</span>
            </div>
            <h3>Appointed Writing Panels</h3>
            <p>Select writing companies and enforce delegation-of-authority limits before files run. Rytera never fabricates market appointments or unapproved paper.</p>
          </article>
        </div>
        <div class="cta reveal" style="margin-top:2rem">
          <a class="btn btn-primary btn-sm" href="/underwriting">Explore All Lines &amp; Desks <svg class="ico sm" aria-hidden="true"><use href="#i-arrow-right"/></svg></a>
          <a class="btn btn-ghost btn-sm" href="/dashboard">Launch Interactive Desk</a>
        </div>
      </section>"""


def trust_section() -> str:
    return """      <section id="trust">
        <div class="reveal">
          <p class="section-label">Trust &amp; Governance Architecture</p>
          <h2>Grounded Risk Intelligence. Built for Regulated Trust.</h2>
          <p class="section-desc">Underwriters operate in high-liability, heavily audited environments where hallucinations mean catastrophic risk. Rytera is engineered around 5 uncompromising trust pillars &mdash; ensuring every decision is transparent, deterministic, auditable, and human-supervised.</p>
        </div>
        <div class="feature-grid reveal" style="grid-template-columns:repeat(3,minmax(0,1fr))">
          <div class="feature-card">
            <span class="icon sky"><svg class="ico" aria-hidden="true"><use href="#i-search"/></svg></span>
            <span class="pillar-tag">Pillar 1 &middot; Explainability</span>
            <h3>"Show Your Work" Reasoning</h3>
            <p><strong>Verbatim Source Attribution:</strong> Every extracted figure and policy clause links directly to its original page number and bounding box.</p>
            <p><strong>Chain-of-Thought Auditing:</strong> Multi-agent step-by-step reasoning explains exactly why a score was assigned.</p>
            <p><strong>Field-Level Confidence:</strong> Individual metrics per data point &mdash; low-confidence cells route automatically to human review.</p>
          </div>
          <div class="feature-card">
            <span class="icon green"><svg class="ico" aria-hidden="true"><use href="#i-users"/></svg></span>
            <span class="pillar-tag">Pillar 2 &middot; Control</span>
            <h3>Human-in-the-Loop &amp; Overrides</h3>
            <p><strong>Pre-Decision Review:</strong> Software synthesizes evidence and proposes &mdash; licensed underwriters retain 100% binding authority.</p>
            <p><strong>Frictionless 1-Click Overrides:</strong> Change any recommendation instantly with mandatory drop-down reason logging.</p>
            <p><strong>Active Learning Loops:</strong> Overrides feed continuous local model calibration to eliminate recurring false flags.</p>
          </div>
          <div class="feature-card">
            <span class="icon violet"><svg class="ico" aria-hidden="true"><use href="#i-scale"/></svg></span>
            <span class="pillar-tag">Pillar 3 &middot; Guardrails</span>
            <h3>Deterministic Rule Enforcement</h3>
            <p><strong>Hard-Coded UWGs:</strong> Compliance limits, class prohibitions, and statutory rules execute in deterministic code &mdash; never LLM guesswork.</p>
            <p><strong>Instant Appetite Pre-Check:</strong> Automated pre-filters screen submissions against your guidelines before deep compute begins.</p>
            <p><strong>State-Filed Rate Books:</strong> Pricing is derived strictly from filed actuarial manuals and SERFF schedules &mdash; zero synthetic rates.</p>
          </div>
          <div class="feature-card">
            <span class="icon sky"><svg class="ico" aria-hidden="true"><use href="#i-shield-check"/></svg></span>
            <span class="pillar-tag">Pillar 4 &middot; Compliance</span>
            <h3>Immutable Audit &amp; Reproducibility</h3>
            <p><strong>Cryptographic Decision Logs:</strong> Timestamped SHA-256 ledger recording prompts, doc versions, agent states, and human sign-offs.</p>
            <p><strong>Multi-Year Reconstitution:</strong> Reconstruct the exact data state and reasoning trail for state market-conduct exams 3+ years later.</p>
            <p><strong>Fair Lending &amp; Bias Auditing:</strong> Built-in monitoring dashboards track decisions to prevent algorithmic bias or disparate impact.</p>
          </div>
          <div class="feature-card" style="grid-column:span 2">
            <span class="icon green"><svg class="ico" aria-hidden="true"><use href="#i-shield"/></svg></span>
            <span class="pillar-tag">Pillar 5 &middot; Uncertainty Handling</span>
            <h3>Graceful Degradation &amp; Fail-Closed Safety</h3>
            <p><strong>Zero Silent Failures:</strong> Blurry scans, corrupted tables, or third-party oracle timeouts cleanly halt and request human intervention rather than inventing data.</p>
            <p><strong>Explicit "Insufficient Data" Output:</strong> Agents are strictly trained to output "Insufficient Data" when information is missing from the submission pack &mdash; zero synthetic financial interpolation.</p>
            <p><strong>Zero PII Exposure:</strong> Insured names, SSNs, and tax IDs are stripped before model processing &mdash; underwriters see the real file; models see de-identified facts.</p>
          </div>
        </div>
      </section>"""


def evolution_section() -> str:
    return """      <section id="evolution">
        <div class="reveal">
          <p class="section-label">Continuous Innovation</p>
          <h2>Continuously Evolving with Modern Risk Technology</h2>
          <p class="section-desc">Underwriting technology moves fast. We ship weekly refinements to handle the real-world friction underwriters face every day &mdash; messy documents, forensic photo checks, and cross-file discrepancies.</p>
        </div>
        <div class="feature-grid reveal">
          <div class="feature-card">
            <span class="new-tag">Weekly Shipping</span>
            <h3>Multi-Format Ingestion</h3>
            <p>Native parsing for complex broker spreadsheets, multi-tab schedules of values (SOVs), Word slips, and scanned loss-run tables with zero data loss.</p>
          </div>
          <div class="feature-card">
            <span class="new-tag">Weekly Shipping</span>
            <h3>Cross-Field Math Reconciliation</h3>
            <p>Automated checks ensure payroll matches headcount, asset values match square footage, and loss-run totals equal detailed claim listings.</p>
          </div>
          <div class="feature-card">
            <span class="new-tag">Weekly Shipping</span>
            <h3>Photo &amp; Forensic Analysis</h3>
            <p>EXIF camera verification and Error Level Analysis (ELA) flag altered inspection photos or stripped metadata before property risk is rated.</p>
          </div>
          <div class="feature-card">
            <span class="new-tag">Core Engine</span>
            <h3>Adaptive Appetite Filters</h3>
            <p>Instant pre-filtering matches incoming submissions against your carrier guidelines, routing out-of-appetite files in seconds.</p>
          </div>
        </div>
      </section>"""


def glossary_preview_section() -> str:
    return """      <section id="glossary-preview">
        <div class="reveal">
          <p class="section-label">Knowledge Reference</p>
          <h2>The Underwriting &amp; AI Governance Reference</h2>
          <p class="section-desc">Clear, professional definitions for core insurance, mortgage, lending, and AI governance terminology. Search below or open the full interactive dictionary.</p>
        </div>
        <div class="glossary-preview-box reveal">
          <div class="glossary-preview-search">
            <svg class="ico" aria-hidden="true"><use href="#i-search"/></svg>
            <input type="text" id="preview-glossary-search" placeholder="Search 50+ definitions (e.g. COPE, ZTA, Loss Run, Decision Memo, ACORD)..." aria-label="Search glossary" />
            <button type="button" class="btn btn-primary btn-sm" id="preview-search-btn">Search Glossary</button>
          </div>
          <div class="glossary-featured-grid">
            <div class="plain-term" data-term="The decision memo">
              <dt>The Decision Memo</dt>
              <dd>A definitive, auditable recommendation ready for licensed sign-off &mdash; citing exact source pages, COPE grades, and filed rate build-ups.</dd>
            </div>
            <div class="plain-term" data-term="Zero Token Architecture">
              <dt>Zero Token Architecture (ZTA)</dt>
              <dd>Tiered execution where deterministic rules and local ML run first at zero AI cost, reserving LLMs strictly for complex free-text synthesis.</dd>
            </div>
            <div class="plain-term" data-term="COPE">
              <dt>COPE Analysis</dt>
              <dd>Construction, Occupancy, Protection, and Exposure &mdash; the four pillars of commercial property underwriting evaluated from schedules and inspection reports.</dd>
            </div>
            <div class="plain-term" data-term="Human-in-the-loop">
              <dt>Human-in-the-Loop Governance</dt>
              <dd>The structural principle that software proposes risk decisions, but a licensed human underwriter with designated authority maintains final approval.</dd>
            </div>
          </div>
          <div class="glossary-preview-actions">
            <button type="button" class="btn btn-ghost" id="open-glossary-full">
              <svg class="ico sm" aria-hidden="true"><use href="#i-book"/></svg>
              Browse All 50+ Definitions in Interactive Glossary &rarr;
            </button>
          </div>
        </div>
      </section>"""


def pipeline_section() -> str:
    return """      <section id="how-it-works">
        <div class="reveal">
          <p class="section-label">How it works</p>
          <h2>From Messy Documents to a Decision You Can Sign</h2>
          <p class="section-desc">Click each stage to see how Rytera processes files: <strong>Triage</strong> sorts the queue, <strong>Risk &amp; Price</strong> verifies math and rates from your manuals, and <strong>Decision</strong> prepares a recommendation ready for licensed sign-off.</p>
        </div>
        <div class="pipeline-wrap reveal">
          <div class="pipeline-steps" role="tablist" aria-label="Pipeline stages">
            <button class="pipeline-step active" data-step="0" role="tab" aria-selected="true">
              <span class="step-num" aria-hidden="true">01</span>
              <span class="step-icon"><svg class="ico" aria-hidden="true"><use href="#i-search"/></svg></span>
              <span class="step-body"><strong>Sort the queue</strong><span>Triage &mdash; which files need you first</span></span>
            </button>
            <button class="pipeline-step" data-step="1" role="tab" aria-selected="false">
              <span class="step-num" aria-hidden="true">02</span>
              <span class="step-icon"><svg class="ico" aria-hidden="true"><use href="#i-scale"/></svg></span>
              <span class="step-body"><strong>Check &amp; price</strong><span>Verify the file, then price from your rates</span></span>
            </button>
            <button class="pipeline-step" data-step="2" role="tab" aria-selected="false">
              <span class="step-num" aria-hidden="true">03</span>
              <span class="step-icon"><svg class="ico" aria-hidden="true"><use href="#i-file-check"/></svg></span>
              <span class="step-body"><strong>You decide</strong><span>A memo you can sign, plus a deeper pass if you ask</span></span>
            </button>
          </div>
          <div class="pipeline-panel" id="pipeline-panel" role="tabpanel"></div>
        </div>
      </section>"""


def testimonials_section() -> str:
    return """      <section id="testimonials">
        <div class="reveal">
          <p class="section-label">From the desk</p>
          <h2>They got their judgment back.</h2>
          <p class="section-desc">Tried on real files in practice shadow mode. Nothing went live until underwriting approved.</p>
        </div>
        <div class="testimonial-grid reveal">
          <div class="testimonial-card">
            <div class="testimonial-stars">
              <svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg>
            </div>
            <p class="quote">I stopped opening shared drives at night. The queue already knew which file needed me. I underwrote. I didn&rsquo;t hunt.</p>
            <div class="who">
              <span class="avatar av-1" aria-hidden="true">HU</span>
              <div class="who-text"><strong>Head of Underwriting</strong><span>MGA &middot; shadow pilot</span></div>
            </div>
          </div>
          <div class="testimonial-card">
            <div class="testimonial-stars">
              <svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg>
            </div>
            <p class="quote">When exam season used to mean assembling packs for days, now I hand them the trail. Every number has a home in the file.</p>
            <div class="who">
              <span class="avatar av-2" aria-hidden="true">CL</span>
              <div class="who-text"><strong>Compliance Lead</strong><span>Carrier &middot; shadow pilot</span></div>
            </div>
          </div>
          <div class="testimonial-card">
            <div class="testimonial-stars">
              <svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg>
            </div>
            <p class="quote">We proved it on our own book without touching live policies. Trust first. Then we bought. Then the hours came back.</p>
            <div class="who">
              <span class="avatar av-3" aria-hidden="true">OD</span>
              <div class="who-text"><strong>Operations Director</strong><span>Aggregator &middot; shadow pilot</span></div>
            </div>
          </div>
        </div>
      </section>"""


# ---------------------------------------------------------------------------
# Page bodies
# ---------------------------------------------------------------------------


def home_main() -> str:
    return (
        hero_home()
        + "\n\n"
        + marquee_section()
        + "\n\n"
        + desks_section()
        + "\n\n"
        + trust_section()
        + "\n\n"
        + pipeline_section()
        + "\n\n"
        + evolution_section()
        + "\n\n"
        + glossary_preview_section()
        + "\n\n"
        + testimonials_section()
        + "\n\n"
        + privacy_band()
        + "\n\n"
        + contact_section()
    )


def platform_main() -> str:
    compare = """      <section id="ai-native">
        <div class="reveal">
          <p class="section-label">The problem &amp; the fix</p>
          <h2>Built for decisions, not document storage</h2>
          <p class="section-desc">Old workbenches were built to hold files. Underwriters were left to read them all. Rytera flips the order: we read, check, and price. Your team still decides. Every desk word below is also in <a href="#plain">In plain English</a>.</p>
        </div>
        <div class="compare reveal">
          <div class="compare-col">
            <div class="compare-head legacy"><svg class="ico" aria-hidden="true"><use href="#i-x-circle"/></svg> The old workbench</div>
            <ul class="compare-list">
              <li>Files arrive by fax, email, or a shared drive &mdash; you hunt</li>
              <li>You sort the queue yourself and look for red flags by hand</li>
              <li>You type the same numbers into a second system</li>
              <li>A yes or no only after hours of reading</li>
              <li>What you will write, and how much is at risk, live in someone&rsquo;s head</li>
              <li>No paper trail of why a file was declined</li>
            </ul>
          </div>
          <div class="compare-col">
            <div class="compare-head ai"><svg class="ico" aria-hidden="true"><use href="#i-check-circle"/></svg> Rytera</div>
            <ul class="compare-list">
              <li>Files arrive where they already live: email, a cloud folder, or a secure drop. Other folders wait until you actually connect them</li>
              <li>The queue is sorted by what you will write, how big the file is, and how much is at risk</li>
              <li>Documents are read and duplicates removed. You do not re-type</li>
              <li>A memo you can sign in minutes &mdash; not a pile of notes</li>
              <li>What you will write, how the building is built (COPE), and how much is at risk &mdash; scored before you open the file</li>
              <li>A sealed paper trail behind every decision</li>
            </ul>
          </div>
        </div>
      </section>"""

    agentic = """      <section id="agentic">
        <div class="reveal">
          <p class="section-label">How the workbench runs</p>
          <h2>Sort. Check and price. Decide.</h2>
          <p class="section-desc">Three steps: <strong>sort the queue</strong> (triage), <strong>check the risk and the price</strong>, then <strong>a recommendation you sign</strong>. A deeper pass can re-check outside data (prior claims, catastrophe), the rest of the book, and fraud flags. You work the exceptions. Not the pile.</p>
        </div>
        <div class="agent-grid reveal">
          <div class="agent-card">
            <span class="ac-ico"><svg class="ico" aria-hidden="true"><use href="#i-gauge"/></svg></span>
            <h3>The important files rise first</h3>
            <p>The live queue is ranked by what you will write, how big the file is, and how much is at risk. You see the ones that matter before the ones that don&rsquo;t.</p>
          </div>
          <div class="agent-card">
            <span class="ac-ico"><svg class="ico" aria-hidden="true"><use href="#i-list-checks"/></svg></span>
            <h3>Not a generic score</h3>
            <p>Filters for what you will write, coastal catastrophe, workers-comp class codes, and loss history fire before a human opens the file.</p>
          </div>
          <div class="agent-card">
            <span class="ac-ico"><svg class="ico" aria-hidden="true"><use href="#i-shield-check"/></svg></span>
            <h3>A person stays in charge</h3>
            <p>A licensed underwriter signs. Who can sign what size of risk is written down. AI proposes. You dispose. Every change you make is recorded.</p>
          </div>
          <div class="agent-card">
            <span class="ac-ico"><svg class="ico" aria-hidden="true"><use href="#i-refresh"/></svg></span>
            <h3>Grows with you</h3>
            <p>Practice mode first (no policy issued). Then real outside data. Then the system that issues the policy. Nothing goes live until you say so.</p>
          </div>
        </div>
      </section>"""

    tabs = """      <section id="features">
        <div class="reveal">
          <p class="section-label">Deep-dive underwriting</p>
          <h2>Each desk, further than a shared dashboard</h2>
          <p class="section-desc">
            Each line of business has its own checks and prices from your filed rates. Pick a desk, or see the shared <strong>Connect &amp; pull</strong> intake that meets the file where it already lives.
          </p>
        </div>
        <div class="tabs reveal" role="tablist" aria-label="Verticals">
          <button class="tab active" data-tab="insurance" role="tab">Commercial insurance</button>
          <button class="tab" data-tab="personal" role="tab">Personal lines</button>
          <button class="tab" data-tab="mortgage" role="tab">Mortgage</button>
          <button class="tab" data-tab="lending" role="tab">Lending</button>
        </div>
        <div class="tab-panel active reveal" id="tab-insurance" role="tabpanel">
          <div class="feature-grid">
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-file-text"/></svg></span><h3>The pile, read</h3><p>Standard broker forms (ACORD), slips, claim histories (loss runs), building lists (schedule of values), inspections &mdash; classified, read, and names stripped for practice mode.</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-bot"/></svg></span><h3>Three steps</h3><p>Sort the queue. Check the risk and the price. Hand you a recommendation. A deeper pass when you ask.</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-banknote"/></svg></span><h3>A price you can issue</h3><p>Accept, accept with conditions, refer, or decline &mdash; with an indicated premium. After you sign, the quote can land in the policy system (for example Guidewire) so you do not type it again.</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-search"/></svg></span><h3>The file&rsquo;s journey</h3><p>One panel per job: how the building is built (COPE), outside data checks, where each fact came from, how the price was built, and a sealed paper trail.</p></div>
          </div>
        </div>
        <div class="tab-panel reveal" id="tab-personal" role="tabpanel">
          <div class="feature-grid">
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-home"/></svg></span><h3>Homeowners</h3><p>Applications, dwelling cover, prior-claims checks (CLUE), and inspection scoring &mdash; priced from your filed home rates.</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-car"/></svg></span><h3>Personal auto</h3><p>Applications, driving records (MVR), and vehicle declarations &mdash; priced from your filed auto rates.</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-heart-pulse"/></svg></span><h3>Term life</h3><p>Applications, paramedical exams, and medical underwriting &mdash; mortality scoring from your life rates, not a guess.</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-file-check"/></svg></span><h3>Your real rates</h3><p>Home, auto, and life engines driven by the manuals you filed with the state. We will not quote a demo book and call it yours.</p></div>
          </div>
        </div>
        <div class="tab-panel reveal" id="tab-mortgage" role="tabpanel">
          <div class="feature-grid">
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-inbox"/></svg></span><h3>30+ document types</h3><p>W-2, tax returns, credit reports, appraisals, bank statements, rent rolls &mdash; the pack processors already know.</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-chart"/></svg></span><h3>Income &amp; collateral</h3><p>Specialist checks for income, credit, assets, and the property that backs the loan.</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-lock"/></svg></span><h3>Rate lock &amp; fairness rules</h3><p>Approve, refer, suspend, or deny &mdash; with the mortgage rules that require clear closing costs, honest credit pricing, and fair reporting (TRID, Reg Z, HMDA).</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-zap"/></svg></span><h3>Works in the background</h3><p>Jobs stay with your company. When the loan system needs an update, we send a signed notice &mdash; not a mystery ping.</p></div>
          </div>
        </div>
        <div class="tab-panel reveal" id="tab-lending" role="tabpanel">
          <div class="feature-grid">
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-building"/></svg></span><h3>Consumer &amp; commercial</h3><p>Business and consumer loan applications on the same workbench.</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-pie"/></svg></span><h3>Credit &amp; pricing</h3><p>Credit risk, compliance rules, and a price that can move with the file &mdash; in one pipeline.</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-scale"/></svg></span><h3>Fair lending</h3><p>Equal-credit rules (Reg B, ECOA), a written reason if we say no, and collateral checks.</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-shield-check"/></svg></span><h3>Shared security</h3><p>Only the right people in your company can see a file. Every decision is sealed. Same rules on every desk.</p></div>
          </div>
        </div>
      </section>"""

    companies = """      <section id="companies">
        <div class="reveal">
          <p class="section-label">Company panel</p>
          <h2>Choose the insurance company. Then underwrite.</h2>
          <p class="section-desc">Every file is for someone&rsquo;s paper. Pick the writing company from the list you are appointed to. Rytera does not invent a market appointment you do not have. Prices still come from the rate book you loaded.</p>
        </div>
        <div class="keyword-strip reveal" aria-label="Example appointed companies">
          <span>InsureFlow Pilot Carrier</span>
          <span>Meridian Mutual</span>
          <span>Harbor Casualty</span>
          <span>Northwind Indemnity</span>
          <span>Pacific Coast Assurance</span>
          <span>Add your appointed company</span>
        </div>
        <div class="feature-grid reveal" style="margin-top:1.6rem">
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-building"/></svg></span><h3>Your panel, your choice</h3><p>The line underwriter picks whose paper the file is for before the work starts. That company is stamped on the job, the memo, and the paper trail.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-list-checks"/></svg></span><h3>Add a company anytime</h3><p>MGAs and multi-company carriers add appointed names in Settings. Same desk, whichever company the file needs.</p></div>
        </div>
      </section>"""

    bento = """      <section id="capabilities">
        <div class="reveal">
          <p class="section-label">Platform capabilities</p>
          <h2>Controls, intake, and a paper trail you can defend</h2>
          <p class="section-desc">
            Production underwriting needs more than a model score. Who decides, names coming off, how files arrive, how the queue is sorted, and a pack an examiner can read &mdash; those are the product. Not extras.
          </p>
        </div>
        <div class="bento reveal">
          <div class="bento-card wide ac-blue">
            <p class="bento-kicker"><svg class="ico"><use href="#i-shield-check"/></svg> Governance</p>
            <h3>Human-in-the-loop by design</h3>
            <p>A licensed underwriter signs. Who can sign what size of risk is written down. Files that need a human go to a referral queue. AI assists. Humans decide. Practice mode keeps policies from issuing until you are ready.</p>
          </div>
          <div class="bento-card ac-green">
            <p class="bento-kicker"><svg class="ico"><use href="#i-lock"/></svg> Privacy</p>
            <h3>Names come off first</h3>
            <p>Social Security numbers, tax IDs, and dates of birth are found and removed before any AI sees the page. You still see the real file.</p>
          </div>
          <div class="bento-card ac-sky">
            <p class="bento-kicker"><svg class="ico"><use href="#i-cable"/></svg> Intake</p>
            <h3>Meet the file where it lives</h3>
            <p>Email, a cloud folder, a secure drop, or a local folder &mdash; when you connect them. SharePoint, Drive, and industry mailboxes wait until you contract them. One Connect &amp; pull hub for insurance, mortgage, and lending.</p>
          </div>
          <div class="bento-card ac-violet">
            <p class="bento-kicker"><svg class="ico"><use href="#i-list-checks"/></svg> Operations</p>
            <h3>The queue, sorted</h3>
            <p>A ranked list so underwriter time goes to the right files first &mdash; not whoever emailed last.</p>
          </div>
          <div class="bento-card wide ac-green">
            <p class="bento-kicker"><svg class="ico"><use href="#i-file-check"/></svg> Compliance</p>
            <h3>A sealed exam pack</h3>
            <p>A locked zip an examiner can open: every decision, every change you made, every outside data check. Nothing quietly rewritten.</p>
          </div>
          <div class="bento-card ac-amber">
            <p class="bento-kicker"><svg class="ico"><use href="#i-database"/></svg> Outside data</p>
            <h3>Real claim history &mdash; or a flag</h3>
            <p>Prior claims, workers-comp history, catastrophe risk. If the accounts are not connected, we flag the gap. We never fake a clean history.</p>
          </div>
          <div class="bento-card ac-blue">
            <p class="bento-kicker"><svg class="ico"><use href="#i-server"/></svg> Reliability</p>
            <h3>Jobs that survive a restart</h3>
            <p>Work is saved, not held only in memory. A restart does not silently lose the file you were in.</p>
          </div>
          <div class="bento-card ac-violet">
            <p class="bento-kicker"><svg class="ico"><use href="#i-refresh"/></svg> Renewals</p>
            <h3>Renewal &amp; premium audit</h3>
            <p>Pre-renewal tracking, premium audit, and loss feedback so the book stays healthy between cycles.</p>
          </div>
          <div class="bento-card ac-amber">
            <p class="bento-kicker"><svg class="ico"><use href="#i-pie"/></svg> Portfolio</p>
            <h3>The book, not only the file</h3>
            <p>How much you already have in one place, concentration, and top lines of business &mdash; with a sense of where the market cycle is.</p>
          </div>
          <div class="bento-card ac-sky">
            <p class="bento-kicker"><svg class="ico"><use href="#i-gauge"/></svg> Model intelligence</p>
            <h3>AI quality, watched</h3>
            <p>We watch speed, quality, and cost of the language model. If quality drops, it does not silently keep writing memos.</p>
          </div>
        </div>
      </section>"""

    return (
        sub_page_hero(
            "The platform",
            "One workbench for every submission",
            "From a messy pile to a memo you can sign. Rytera reads, checks, and prices. You still decide. Not a stack of parsed PDFs you have to rewrite.",
            secondary="/technology",
            secondary_label="See the technology",
        )
        + "\n\n"
        + compare
        + "\n\n"
        + agentic
        + "\n\n"
        + tabs
        + "\n\n"
        + companies
        + "\n\n"
        + bento
        + "\n\n"
        + validation_section()
        + "\n\n"
        + page_close()
    )


def technology_main() -> str:
    zta = """      <section id="zta">
        <div class="reveal">
          <p class="section-label">Zero Token Architecture</p>
          <h2>Ordinary software first. AI last. You can measure it.</h2>
          <p class="section-desc">
            Most AI underwriting tools send every page to a language model (and pay for it). Rytera asks: <em>can ordinary rules or a trained scorer do this?</em>
            Most of underwriting can. So you get faster, cheaper, repeatable answers. When a language model is truly needed, the cost is counted and shown on the job.
            <a href="#plain">Every word, said simply.</a>
          </p>
        </div>
        <div class="zta-ladder reveal">
          <div class="zta-step L1">
            <div class="step-top">
              <span class="step-ico"><svg class="ico" aria-hidden="true"><use href="#i-cpu"/></svg></span>
              <span class="step-num">Layer 1</span>
            </div>
            <h3>Ordinary rules</h3>
            <p>Readers, matching numbers, how the building is built, your rate engine, and compliance rules do everything they can. No AI bill. Same answer twice.</p>
            <span class="tokens zero"><svg class="ico" aria-hidden="true"><use href="#i-check"/></svg> 0 AI cost &middot; fully repeatable</span>
          </div>
          <div class="zta-flow" aria-hidden="true"><svg class="ico"><use href="#i-arrow-right"/></svg></div>
          <div class="zta-step L2">
            <div class="step-top">
              <span class="step-ico"><svg class="ico" aria-hidden="true"><use href="#i-bot"/></svg></span>
              <span class="step-num">Layer 2</span>
            </div>
            <h3>Trained scorers</h3>
            <p>Eight models score loss, fraud, churn, premium, book risk, and default &mdash; like a calculator, not a chatbot. No prompt. Same inputs, same output.</p>
            <span class="tokens zero"><svg class="ico" aria-hidden="true"><use href="#i-check"/></svg> 0 AI cost &middot; repeatable</span>
          </div>
          <div class="zta-flow" aria-hidden="true"><svg class="ico"><use href="#i-arrow-right"/></svg></div>
          <div class="zta-step L3">
            <div class="step-top">
              <span class="step-ico"><svg class="ico" aria-hidden="true"><use href="#i-zap"/></svg></span>
              <span class="step-num">Layer 3</span>
            </div>
            <h3>A language model &mdash; only when needed</h3>
            <p>Judgment that genuinely needs reading and writing, with a budget per job. Never used to invent a fact code already knows.</p>
            <span class="tokens one"><svg class="ico" aria-hidden="true"><use href="#i-sliders"/></svg> counted &middot; reported</span>
          </div>
        </div>
        <div class="zta-stats reveal">
          <div class="zta-stat">
            <span class="zstat-ico green"><svg class="ico" aria-hidden="true"><use href="#i-cpu"/></svg></span>
            <div class="body"><span class="num">~90%</span><p>of typical pipeline tasks finish without a language model</p></div>
          </div>
          <div class="zta-stat">
            <span class="zstat-ico blue"><svg class="ico" aria-hidden="true"><use href="#i-database"/></svg></span>
            <div class="body"><span class="num">0</span><p>AI cost to read a standard form, price, or match the numbers</p></div>
          </div>
          <div class="zta-stat">
            <span class="zstat-ico violet"><svg class="ico" aria-hidden="true"><use href="#i-bot"/></svg></span>
            <div class="body"><span class="num" data-target="8">0</span><p>trained scorers in the model registry</p></div>
          </div>
        </div>
      </section>"""

    security = """      <section id="security">
        <div class="reveal">
          <p class="section-label">Security &amp; paper trail</p>
          <h2>Every decision defensible</h2>
          <p class="section-desc">Locked files, who can see what, and a pack an examiner can read are built in &mdash; not bolted on after.</p>
        </div>
        <div class="feature-grid reveal">
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-lock"/></svg></span><h3>Files stored locked</h3><p>Each company&rsquo;s work stays in its own lockbox. Social Security numbers, tax IDs, and dates of birth come off before any AI sees the page.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-key"/></svg></span><h3>Who can see what</h3><p>Only the right people in your company can open a file. Roles are written down. One company cannot see another&rsquo;s jobs.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-file-check"/></svg></span><h3>A pack for the examiner</h3><p>Every decision, every change you made, every outside data check ships in a sealed zip. Nobody can quietly rewrite the record.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-shield-check"/></svg></span><h3>A person stays in charge</h3><p>A licensed underwriter signs. Who can sign what size of risk is written down. AI proposes. You dispose. Every change is recorded.</p></div>
        </div>
        <div class="trust-strip reveal" aria-label="Security and compliance">
          <span class="trust-item"><svg class="ico sm"><use href="#i-check"/></svg> Only the right people see a file</span>
          <span class="trust-item"><svg class="ico sm"><use href="#i-check"/></svg> Files stored locked</span>
          <span class="trust-item"><svg class="ico sm"><use href="#i-check"/></svg> Names off before AI</span>
          <span class="trust-item"><svg class="ico sm"><use href="#i-check"/></svg> Sealed exam packs</span>
          <span class="trust-item"><svg class="ico sm"><use href="#i-check"/></svg> No language-model key required</span>
        </div>
      </section>"""

    return (
        sub_page_hero(
            "Technology",
            "Rules first. AI last. Always counted.",
            "Most steps are ordinary software (no AI bill). A language model is the last resort, counted, and never used to invent a fact. That is Zero Token Architecture &mdash; said simply: we do not pay an AI to do what a rule already can.",
            secondary="/dashboard",
            secondary_label="Open the live dashboard",
        )
        + "\n\n"
        + zta
        + "\n\n"
        + pipeline_section()
        + "\n\n"
        + security
        + "\n\n"
        + page_close()
    )


def underwriting_main() -> str:
    audience = """      <section id="audience">
        <div class="reveal">
          <p class="section-label">Who it's for</p>
          <h2>Built for every desk that says yes or no to risk</h2>
          <p class="section-desc">
            Whether you quote one account or steer a national book, this is for the people who say yes or no.
            <strong>Line underwriters</strong> work files in the branch. <strong>Staff underwriters</strong> at home office set the rules. Both desks. Every line. <a href="#plain">Words of the desk.</a>
          </p>
        </div>
        <div class="audience-grid reveal">
          <div class="audience-card ac-blue">
            <span class="ac-ico"><svg class="ico" aria-hidden="true"><use href="#i-building"/></svg></span>
            <h3>Commercial carriers &amp; MGAs</h3>
            <p class="who">Line and staff underwriters running commercial books.</p>
            <p>A ranked queue, a memo you can sign, and a licensed person still on the yes &mdash; general liability, property, and specialty.</p>
          </div>
          <div class="audience-card ac-green">
            <span class="ac-ico"><svg class="ico" aria-hidden="true"><use href="#i-home"/></svg></span>
            <h3>Personal lines carriers</h3>
            <p class="who">Homeowners, auto, and term-life underwriting teams.</p>
            <p>Prices from the rates you filed with the state. Prior-claims and driving-record checks (CLUE / MVR). No invented premium.</p>
          </div>
          <div class="audience-card ac-sky">
            <span class="ac-ico"><svg class="ico" aria-hidden="true"><use href="#i-inbox"/></svg></span>
            <h3>Mortgage lenders</h3>
            <p class="who">Underwriters and processing teams.</p>
            <p>Income, assets, and the property that backs the loan &mdash; across 30+ document types. Mortgage fairness rules (clear closing costs, honest credit pricing, fair reporting) are built in.</p>
          </div>
          <div class="audience-card ac-violet">
            <span class="ac-ico"><svg class="ico" aria-hidden="true"><use href="#i-banknote"/></svg></span>
            <h3>Commercial lenders</h3>
            <p class="who">Credit and loan underwriting desks.</p>
            <p>Consumer and business loan files. Credit scoring, a price that can move with the file, and equal-credit rules with a written reason if you say no.</p>
          </div>
          <div class="audience-card ac-amber">
            <span class="ac-ico"><svg class="ico" aria-hidden="true"><use href="#i-layers"/></svg></span>
            <h3>Program administrators &amp; aggregators</h3>
            <p class="who">MGAs running books on behalf of carriers.</p>
            <p>What you will write, across the book. Practice mode first (no policy issued). Go live when you say so.</p>
          </div>
        </div>
      </section>"""

    desks = """      <section id="uw-desks">
        <div class="reveal">
          <p class="section-label">Underwriting desks</p>
          <h2>Built for line and staff underwriters</h2>
          <p class="section-desc">
            <strong>Line underwriters</strong> in the branch run the files. <strong>Staff underwriters</strong> at home office set the policy the line desk follows. Rytera covers both &mdash; and the overlap on large or unusual accounts.
          </p>
        </div>
        <div class="feature-grid reveal" style="margin-top:1.5rem;">
          <div class="feature-card">
            <span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-briefcase"/></svg></span>
            <h3>Line underwriter desk</h3>
            <p>Regional and branch underwriters implement the underwriting process.</p>
            <ul>
              <li>Coverage assist &mdash; broaden gaps or narrow terms instead of declining</li>
              <li>Producer &amp; policyholder service &mdash; quotes, endorsements, certificates, renewals</li>
              <li>The file&rsquo;s journey: sort the queue, price, memo, licensed sign-off</li>
            </ul>
          </div>
          <div class="feature-card">
            <span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-landmark"/></svg></span>
            <h3>Staff underwriter desk</h3>
            <p>Home-office underwriters make and implement underwriting policy.</p>
            <ul>
              <li>Market research, coverage development, and rating-plan reviews (industry loss costs from ISO / AAIS / NCCI)</li>
              <li>UW guides, policy statements, and branch file audits</li>
              <li>Experience evaluation and technical training for line underwriters</li>
            </ul>
          </div>
        </div>
      </section>"""

    verticals = """      <section id="verticals">
        <div class="reveal">
          <p class="section-label">Underwriting verticals</p>
          <h2>Every line you write, on one platform</h2>
          <p class="section-desc">From commercial lines to specialty, personal lines, mortgage, and lending &mdash; each desk has its own checks and prices from your filed rates. Abbreviations are spelled out on the cards. The full list is in <a href="#plain">In plain English</a>.</p>
        </div>
        <div class="feature-grid reveal">
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-file-text"/></svg></span><h3>Commercial lines</h3><p>General liability, property, auto, and packages. Industry loss costs plus your expenses. A memo you can issue after you sign.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-shield-check"/></svg></span><h3>Workers' compensation</h3><p>Class codes, experience mods, payroll audits, and state filing checks for workers-comp books.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-lock"/></svg></span><h3>Professional liability</h3><p>Errors &amp; omissions, directors &amp; officers, and employment practices &mdash; applications, claims history, and how much is at risk.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-zap"/></svg></span><h3>Cyber</h3><p>Security posture, breach history, and a cyber price without a week of waiting.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-package"/></svg></span><h3>Excess &amp; surplus / specialty</h3><p>Risks the regular market will not write. Extra checks on what you will write and who is allowed to issue.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-globe"/></svg></span><h3>Inland &amp; ocean marine</h3><p>Cargo, hull, and inland marine &mdash; what moves, what it is worth, what sits in transit.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-home"/></svg></span><h3>Personal lines</h3><p>Homeowners, auto, and term life with prior-claims and driving-record checks, priced from your state-filed manuals.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-landmark"/></svg></span><h3>Mortgage</h3><p>Income, assets, and collateral across 30+ document types. Fairness rules for closing costs, credit pricing, and reporting are built in.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-banknote"/></svg></span><h3>Lending</h3><p>Consumer and business loans. Credit scoring, a price that can move, equal treatment, and a written reason if you say no.</p></div>
        </div>
      </section>"""

    book = """      <section id="insurance-book">
        <div class="reveal">
          <p class="section-label">The insurance book</p>
          <h2>12 sections on 1 workbench</h2>
          <p class="section-desc"><strong>Live</strong> means we can price it today from rates you loaded. <strong>Catalog</strong> means we list it, but we will not invent a premium. Maternity is not outpatient. Third-party auto is not comprehensive. Cargo is not hull. Each product has its own checklist. Names come off before any AI sees a page. Pick the writing company from your appointed panel before the file runs.</p>
        </div>
        <div class="lob-grid reveal">
          <a class="lob-card" href="/dashboard/insurance/sections/life"><span class="lob-n">01</span><h3>Life</h3><p>Term we can price today. Whole life, universal life, endowment, money-back, annuity wait until those rates are in.</p><span class="lob-tag live">Live</span></a>
          <a class="lob-card" href="/dashboard/insurance/sections/health"><span class="lob-n">02</span><h3>Health</h3><p>Individual through disability &mdash; including outpatient visits and critical illness &mdash; when your health rates are loaded.</p><span class="lob-tag live">Live</span></a>
          <a class="lob-card" href="/dashboard/insurance/sections/general"><span class="lob-n">03</span><h3>General / Non-Life</h3><p>Motor, home, travel, marine, fire, cyber. Listed so you can see coverage. No quote until your filed rates are in.</p><span class="lob-tag catalog">Catalog</span></a>
          <a class="lob-card" href="/dashboard/insurance/sections/commercial"><span class="lob-n">04</span><h3>Business / Commercial</h3><p>Property &amp; business interruption, directors &amp; officers, workers&rsquo; comp, trade credit, errors &amp; omissions, key person.</p><span class="lob-tag live">Live</span></a>
          <a class="lob-card" href="/dashboard/insurance/sections/specialty"><span class="lob-n">05</span><h3>Other / Specialty</h3><p>Crop, livestock, pet, events, title, mortgage guarantee. Catalog until those rates are loaded.</p><span class="lob-tag catalog">Catalog</span></a>
          <a class="lob-card" href="/dashboard/insurance/sections/provider"><span class="lob-n">06</span><h3>By Provider Type</h3><p>Public vs private onboarding, business-to-business reinsurance. Catalog until contracted.</p><span class="lob-tag catalog">Catalog</span></a>
          <a class="lob-card" href="/dashboard/insurance/sections/engineering"><span class="lob-n">07</span><h3>Engineering</h3><p>Contractors&rsquo; all risk, erection all risk, machinery, boiler, delay in start-up.</p><span class="lob-tag live">Live</span></a>
          <a class="lob-card" href="/dashboard/insurance/sections/aviation"><span class="lob-n">08</span><h3>Aviation</h3><p>Hull, liability, and passenger risk.</p><span class="lob-tag live">Live</span></a>
          <a class="lob-card" href="/dashboard/insurance/sections/fidelity"><span class="lob-n">09</span><h3>Fidelity &amp; Burglary</h3><p>Employee fraud and burglary / theft.</p><span class="lob-tag live">Live</span></a>
          <a class="lob-card" href="/dashboard/insurance/sections/catastrophe"><span class="lob-n">10</span><h3>Catastrophe</h3><p>Flood, earthquake, and weather-index covers.</p><span class="lob-tag live">Live</span></a>
          <a class="lob-card" href="/dashboard/insurance/sections/niche-liability"><span class="lob-n">11</span><h3>Niche Liability</h3><p>Umbrella, pollution, kidnap &amp; ransom, political risk, terrorism.</p><span class="lob-tag live">Live</span></a>
          <a class="lob-card" href="/dashboard/insurance/sections/warranty-financial-emerging"><span class="lob-n">12</span><h3>Warranty / Financial / Emerging</h3><p>Surety, credit life, gadget, micro, usage-based (price from how you drive), personal cyber.</p><span class="lob-tag live">Live</span></a>
        </div>
        <div class="feature-grid reveal" style="margin-top:1.6rem">
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-landmark"/></svg></span><h3>Mortgage</h3><p>Income, assets, and the property that backs the loan. Fairness rules for closing costs, credit pricing, and reporting are built in.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-banknote"/></svg></span><h3>Lending</h3><p>Consumer and business loans. Credit scoring, a price that can move, equal treatment, and a written reason if you say no.</p></div>
        </div>
      </section>"""

    ratemaking = """      <section id="ratemaking">
        <div class="reveal">
          <p class="section-label">Ratemaking &amp; Pricing</p>
          <h2>Rates built like an actuary builds them</h2>
          <p class="section-desc">Ratemaking means turning past claims into future prices. Rytera uses the three textbook methods &mdash; <strong>pure premium</strong> (expected claims), <strong>loss ratio</strong> (claims vs premium), and <strong>judgment</strong> &mdash; and checks every rate is <strong>enough to pay claims</strong>, <strong>not excessive</strong>, and <strong>not unfair</strong>. It also models money set aside for claims still open, investment income on that money, and expenses split fairly across lines.</p>
        </div>
        <div class="feature-grid">
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-layers"/></svg></span><h3>Base-rate build-up</h3><p>The three-step process: future claims (pure premium) + future expenses (expense loading) = base rate, then load for contingencies and profit.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-chart"/></svg></span><h3>Loss ratio method</h3><p>Projected loss ratio (trend &times; loss development) vs permissible loss ratio to compute the indicated rate change.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-scale"/></svg></span><h3>Statutory review</h3><p>Every rate is verified adequate, not excessive, and free of unfairly discriminatory classification before it is offered.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-book"/></svg></span><h3>Industry starting rates</h3><p>ISO, AAIS, NCCI, and Surety Association publish loss costs &mdash; a starting price for claims. You add your own expenses and profit. We do not skip that and invent a number.</p></div>
        </div>
        <div class="cta" style="margin-top:1.5rem">
          <a class="btn btn-primary" href="/dashboard">
            Open ratemaking dashboard
            <svg class="ico sm" aria-hidden="true"><use href="#i-arrow-right"/></svg>
          </a>
        </div>
      </section>"""

    return (
        sub_page_hero(
            "Underwriting",
            "Built for the desks that decide",
            "Line underwriters run the files. Staff underwriters set the rules. Both get a ranked queue, a memo they can sign, and prices from rates you actually filed &mdash; insurance, mortgage, and lending.",
            secondary="/platform",
            secondary_label="Explore the platform",
        )
        + "\n\n"
        + audience
        + "\n\n"
        + desks
        + "\n\n"
        + verticals
        + "\n\n"
        + book
        + "\n\n"
        + ratemaking
        + "\n\n"
        + page_close()
    )


def integrations_main() -> str:
    modes = """      <section id="modes">
        <div class="reveal">
          <p class="section-label">How connectors run</p>
          <h2>Live, simulated, or auto &mdash; never fabricated</h2>
          <p class="section-desc"><strong>Live</strong> means your real accounts. <strong>Simulated</strong> means honest demo data, labeled as demo. <strong>Auto</strong> uses live when keys exist and flags the gap instead of guessing a clean history. <a href="#plain">What oracles and IMAP mean.</a></p>
        </div>
        <div class="feature-grid reveal">
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-cable"/></svg></span><h3>Live</h3><p>Real drops wired to your accounts &mdash; email, a secure folder, a cloud bucket, or a local folder. SharePoint, Drive, industry mailboxes, and Applied Epic wait until you contract them. Claim-history checks stay dark without keys.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-sliders"/></svg></span><h3>Simulated</h3><p>Honest demo data when keys aren&rsquo;t connected &mdash; nothing fabricated, nothing mislabeled as real history.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-refresh"/></svg></span><h3>Auto</h3><p>Uses live feeds whenever keys are present. Otherwise you see the gap. We never invent a clean loss run.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-gauge"/></svg></span><h3>Health monitoring</h3><p>Every connector reports status. You see live / simulated / auto at a glance and get alerted before a feed goes stale.</p></div>
        </div>
      </section>"""

    integ = """      <section id="integrations">
        <div class="reveal">
          <p class="section-label">Integrations</p>
          <h2>Connects to the systems you already use</h2>
          <p class="section-desc">Filter by category. <strong>Oracles</strong> means outside data checks (prior claims, catastrophe). <strong>Policy &amp; CRM</strong> means the system that issues the policy and the system that holds the customer. Every adapter supports live, simulated, and auto &mdash; never a fake green light.</p>
        </div>
        <div class="filter-bar reveal">
          <button class="filter-btn active" data-filter="all">
            <svg class="ico sm"><use href="#i-sliders"/></svg> All
          </button>
          <button class="filter-btn" data-filter="oracles">Outside data</button>
          <button class="filter-btn" data-filter="policy">Policy &amp; CRM</button>
          <button class="filter-btn" data-filter="ops">Enterprise ops</button>
          <button class="filter-btn" data-filter="sources">Doc sources</button>
        </div>
        <div class="integration-grid reveal" id="integration-grid"></div>
      </section>"""

    return (
        sub_page_hero(
            "Integrations",
            "Connects to the systems you already use",
            "One Connect &amp; pull hub meets the file where it already lives &mdash; email, folders, the policy system, CRM, and outside data checks. Each connection is live, simulated, or auto. Never fabricated.",
            secondary="/dashboard",
            secondary_label="Open the live dashboard",
        )
        + "\n\n"
        + integ
        + "\n\n"
        + modes
        + "\n\n"
        + marquee_section()
        + "\n\n"
        + page_close()
    )


def company_main() -> str:
    about = """      <section id="about">
        <div class="reveal">
          <p class="section-label">About Rytera</p>
          <h2>We build underwriting software for underwriters</h2>
          <p class="section-desc">Rytera Inc. builds underwriting software for underwriters &mdash; at insurance companies, MGAs (teams allowed to write on a company&rsquo;s behalf), mortgage lenders, and commercial lenders.</p>
        </div>
        <div class="feature-grid reveal">
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-users"/></svg></span><h3>Who we build for</h3><p>Commercial &amp; personal lines carriers, MGAs and program administrators, mortgage lenders, and commercial lenders &mdash; one platform for every desk.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-refresh"/></svg></span><h3>The pilot model</h3><p>Practice first, issue last. Measure accuracy on your real book before the policy system turns on &mdash; with a clean cutover when you&rsquo;re ready.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-shield-check"/></svg></span><h3>Security &amp; compliance</h3><p>Files stored locked. Only the right people in your company can see a file. Names come off before any AI sees a page. Every decision ships in a sealed pack an examiner can open.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-mail"/></svg></span><h3>Get in touch</h3><p>Book a walkthrough or email <a class="contact-email" href="mailto:hello@ryterainc.com">hello@ryterainc.com</a> &mdash; our team responds within one business day.</p></div>
        </div>
      </section>"""

    faq = """      <section id="faq">
        <div class="reveal">
          <p class="section-label">FAQ</p>
          <h2>Frequently asked questions</h2>
          <p class="section-desc">Search or expand any question below.</p>
        </div>
        <input type="search" class="faq-search reveal" id="faq-search" placeholder="Search questions&hellip;" aria-label="Search FAQ" />
        <div class="faq reveal" id="faq-list"></div>
      </section>"""

    return (
        sub_page_hero(
            "Company",
            "Rytera Inc.",
            "We build underwriting software for the people who say yes or no &mdash; a person stays in charge, ordinary software does most of the work, and you can hand the paper trail to a regulator.",
            primary="book",
            secondary="/dashboard",
            secondary_label="Open the live dashboard",
        )
        + "\n\n"
        + about
        + "\n\n"
        + faq
        + "\n\n"
        + page_close()
    )


# ---------------------------------------------------------------------------
# Extract shared CSS / JS from the legacy single-page file
# ---------------------------------------------------------------------------


def extract_shared() -> tuple[str, str]:
    script_dir = Path(__file__).resolve().parent
    css = (script_dir / "landing.css").read_text(encoding="utf-8")
    js = (script_dir / "landing.js").read_text(encoding="utf-8")
    return css, js


def main() -> None:
    css, js = extract_shared()

    pages = {
        "index.html": page(
            "Rytera - Stop hunting PDFs. Start underwriting.",
            "Rytera for underwriters who are tired of hunting PDFs. We read the pile. You still sign. We never invent a price.",
            "",
            "You didn't take this job to hunt PDFs. We read the pile. You still sign. Practice first. No invented prices.",
            home_main(),
        ),
        "platform.html": page(
            "Rytera - One workbench for every file",
            "From a messy pile to a memo you can sign. Rytera reads, checks, and prices. You still decide.",
            "platform",
            "From a messy pile to a memo you can sign. You still decide.",
            platform_main(),
        ),
        "technology.html": page(
            "Rytera - Rules first. AI last.",
            "Most steps are ordinary software. A language model is the last resort, counted, and never used to invent a fact. Files stay locked. A person still signs.",
            "technology",
            "Ordinary software first. AI last. Always counted. A paper trail you can hand to a regulator.",
            technology_main(),
        ),
        "underwriting.html": page(
            "Rytera - Built for the desks that decide",
            "Line underwriters run the files. Staff underwriters set the rules. Ranked queue, a memo you can sign, prices from rates you actually filed.",
            "underwriting",
            "Built for every desk that says yes or no to risk — insurance, mortgage, and lending.",
            underwriting_main(),
        ),
        "integrations.html": page(
            "Rytera - Connects to the systems you already use",
            "Meet the file where it already lives: email, folders, the policy system, and outside data checks. Live, simulated, or auto — never fabricated.",
            "integrations",
            "Connects to the systems you already use — live, simulated, or auto. Never a fake green light.",
            integrations_main(),
        ),
        "company.html": page(
            "Rytera - About, FAQ & Contact",
            "Rytera Inc. builds underwriting software for underwriters. Practice first. A person still signs. FAQ and how to reach the team.",
            "company",
            "About Rytera Inc., practice-first pilots, FAQ, and how to book a walkthrough.",
            company_main(),
        ),
        "pricing.html": page(
            "Rytera - Pricing that only charges when the data is real",
            "Pilot is free and honest. Desk and above stop unless live outside data, your filed rates, and bind without re-typing are in place.",
            "pricing",
            "You will not buy fake outside data, a demo rate book sold as yours, or a bind you still have to type in by hand.",
            pricing_main(),
        ),
    }

    (LANDING / "landing.css").write_text(css, encoding="utf-8")
    (LANDING / "landing.js").write_text(js, encoding="utf-8")
    for name, html in pages.items():
        (LANDING / name).write_text(html, encoding="utf-8")

    print("wrote", len(pages) + 2, "files to", LANDING)
    for name in list(pages) + ["landing.css", "landing.js"]:
        print("  -", name)


if __name__ == "__main__":
    main()
