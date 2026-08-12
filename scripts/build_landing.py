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
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M7 4h10l-6 16"/></svg>
        </span>
        <span class="brand-name">Rytera<sup>&trade;</sup></span>
      </a>"""

NAV_LINKS = [
    ("/", "Home"),
    ("/platform", "Platform"),
    ("/technology", "Technology"),
    ("/underwriting", "Underwriting"),
    ("/integrations", "Integrations"),
    ("/company", "Company"),
]

NAV_ANCHORS = "\n".join(f'        <a href="{href}" data-nav>{label}</a>' for href, label in NAV_LINKS)
NAV_ANCHORS_MOBILE = "\n".join(f'      <a href="{href}" data-nav>{label}</a>' for href, label in NAV_LINKS)

HEADER = """    <header id="header">
      <div class="nav-inner">
""" + BRAND + """
        <nav class="nav-desktop" aria-label="Main">
""" + NAV_ANCHORS + """
        </nav>
        <div class="nav-actions">
          <a class="nav-dash" href="/dashboard">Dashboard</a>
          <button type="button" class="btn btn-primary btn-sm" id="open-demo-nav">Book a demo</button>
        </div>
        <button class="menu-btn" id="menu-btn" aria-label="Open menu" aria-expanded="false">
          <svg class="ico" aria-hidden="true"><use href="#i-menu"/></svg>
        </button>
      </div>
    </header>
    <nav class="mobile-nav" id="mobile-nav" aria-label="Mobile">
""" + NAV_ANCHORS_MOBILE + """
      <a href="/dashboard">Dashboard</a>
      <button type="button" class="btn btn-primary" id="open-demo-mobile">Book a demo</button>
    </nav>"""

FOOTER = """    <footer>
      <div class="footer-grid">
        <div class="brand" aria-label="Rytera">
          <span class="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M7 4h10l-6 16"/></svg>
          </span>
          <span class="brand-name">Rytera<sup>&trade;</sup></span>
        </div>
        <nav class="footer-links" aria-label="Footer">
""" + "\n".join(f'          <a href="{href}">{label}</a>' for href, label in NAV_LINKS) + """
          <a href="/dashboard">Dashboard</a>
          <a href="/health">System status</a>
        </nav>
        <div>
          <div style="margin-bottom:.25rem">AI-native underwriting for carriers, MGAs &amp; aggregators.</div>
          <div>&copy; 2026 Rytera, Inc. All rights reserved.</div>
        </div>
      </div>
    </footer>"""

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
              <option value="Personal lines">Personal lines</option>
              <option value="Mortgage">Mortgage lending</option>
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
        <p class="form-note">Prefer email? <a href="mailto:hello@rytera.ai">hello@rytera.ai</a> &middot; or jump straight to the <a href="/dashboard">live dashboard</a></p>
      </div>
      <div class="modal-success" id="modal-success">
        <span class="ok-ico"><svg class="ico"><use href="#i-check-circle"/></svg></span>
        <h3>Request received</h3>
        <p>Thanks &mdash; our team will reach out within one business day to schedule your walkthrough.</p>
        <a class="btn btn-ghost" href="/dashboard">Explore the dashboard now</a>
      </div>
    </div>
  </div>"""


def head(title: str, desc: str, canonical: str, og_desc: str) -> str:
    return (
        "  <meta charset=\"UTF-8\" />\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n"
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
        '  {\n'
        '    "@context": "https://schema.org",\n'
        '    "@type": "Organization",\n'
        '    "name": "Rytera",\n'
        '    "url": "https://ryterainc.com/",\n'
        '    "logo": "https://ryterainc.com/icon-512.png",\n'
        '    "description": "AI underwriting platform for commercial & personal lines insurance, mortgage, and lending.",\n'
        '    "email": "hello@rytera.ai"\n'
        '  }\n'
        '  </script>\n'
        '  <link rel="preconnect" href="https://fonts.googleapis.com" />\n'
        '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />\n'
        '  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Sora:wght@400;500;600;700;800&display=swap" rel="stylesheet" />\n'
        '  <link rel="stylesheet" href="/static/landing.css" />\n'
    )


def page(title: str, desc: str, canonical: str, og_desc: str, main_html: str) -> str:
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        + head(title, desc, canonical, og_desc)
        + "</head>\n<body>\n"
        + SPRITE
        + "\n"
        + BG
        + "\n  <div class=\"page\">\n"
        + HEADER
        + "\n\n    <main>\n"
        + main_html
        + "\n    </main>\n"
        + FOOTER
        + "\n  </div>\n\n"
        + MODAL
        + "\n  <script src=\"/static/landing.js\" defer></script>\n</body>\n</html>\n"
    )


# ---------------------------------------------------------------------------
# Shared section builders
# ---------------------------------------------------------------------------

def sub_page_hero(label: str, h1: str, lead: str, primary: str = "book", primary_label: str = "Book a demo",
                  secondary: str | None = None, secondary_label: str | None = None) -> str:
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
        "      <section class=\"page-hero\">\n"
        "        <div class=\"reveal\">\n"
        f"          <p class=\"section-label\">{label}</p>\n"
        f"          <h1>{h1}</h1>\n"
        f"          <p class=\"lead\">{lead}</p>\n"
        + cta
        + "\n        </div>\n"
        "      </section>"
    )


def contact_section() -> str:
    return """      <section id="contact">
        <div class="contact-box reveal">
          <p class="section-label" style="justify-content:center;margin-left:auto;margin-right:auto;">Ready when you are</p>
          <h2>See your book move through Rytera</h2>
          <p>Walk through the submission journey, multi-agent pipeline, and live dashboard on a 30-minute call. Start with a shadow pilot &mdash; bind stays off until your team approves the cutover.</p>
          <div class="cta" style="justify-content:center;">
            <button type="button" class="btn btn-primary" id="open-demo-contact">Book a demo</button>
            <a class="btn btn-ghost" href="/dashboard">Open the live dashboard</a>
          </div>
          <p style="margin-top:1.5rem;margin-bottom:0;font-size:.875rem">
            Prefer email? <a class="contact-email" href="mailto:hello@rytera.ai">hello@rytera.ai</a>
          </p>
        </div>
      </section>"""


def hero_home() -> str:
    return """      <section class="hero" id="top">
        <div class="hero-grid">
          <div class="reveal">
            <div class="hero-badge">
              <span class="dot"></span>
              Rytera &middot; AI-native underwriting workbench
            </div>
            <h1>Bind-ready decisions <span class="gradient">in minutes, not days</span></h1>
            <p class="lead">
              Rytera takes the messy submissions that slow underwriting down &mdash; ACORD, broker PDFs, loss runs, W-2s &mdash; and
              turns them into a <strong>bind-ready underwriting memo</strong> with quote, audit trail, and licensed
              sign-off. One platform for <strong>line and staff underwriters</strong> across commercial &amp; personal
              lines, mortgage, and lending.
            </p>
            <div class="cta">
              <button type="button" class="btn btn-primary" id="open-demo-hero">
                Book a demo
                <svg class="ico sm" aria-hidden="true"><use href="#i-arrow-right"/></svg>
              </button>
              <a class="btn btn-ghost" href="#how-it-works">See how it works</a>
            </div>
            <div class="hero-audience" aria-label="Built for">
              <span class="audience-pill"><svg class="ico sm"><use href="#i-building"/></svg> Carriers</span>
              <span class="audience-pill"><svg class="ico sm"><use href="#i-layers"/></svg> MGAs &amp; program administrators</span>
              <span class="audience-pill"><svg class="ico sm"><use href="#i-home"/></svg> Personal lines</span>
              <span class="audience-pill"><svg class="ico sm"><use href="#i-banknote"/></svg> Mortgage &amp; commercial lenders</span>
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
                  <span class="side-item brand-tag"><span>Pacific Coast Underwriters<br/>Shadow pilot &middot; bind off</span></span>
                </div>
                <div class="mock-main">
                  <div class="m-head">
                    <span class="m-title">Submission #1052 &middot; <span>Pacific Coast Supply Co</span></span>
                    <span class="m-badge">Bind-ready</span>
                  </div>
                  <div class="m-stages">
                    <span class="m-stage done"><svg class="ico"><use href="#i-check"/></svg> Triage 84</span>
                    <span class="m-stage done"><svg class="ico"><use href="#i-check"/></svg> Appetite</span>
                    <span class="m-stage done"><svg class="ico"><use href="#i-check"/></svg> COPE B</span>
                    <span class="m-stage done"><svg class="ico"><use href="#i-check"/></svg> Agents</span>
                    <span class="m-stage done"><svg class="ico"><use href="#i-check"/></svg> UW memo</span>
                    <span class="m-stage pending">Sign-off</span>
                  </div>
                  <div class="m-progress">
                    <div class="m-prog-label"><span>Document ingestion</span><span>14 / 16 parsed</span></div>
                    <div class="m-bar"><span></span></div>
                  </div>
                  <div class="m-grid">
                    <div class="m-cell"><span class="k">COPE grade</span><span class="v">Preferred</span></div>
                    <div class="m-cell"><span class="k">Recommendation</span><span class="v accept">ACCEPT</span></div>
                    <div class="m-cell"><span class="k">Indicated premium</span><span class="v">$46,890</span></div>
                    <div class="m-cell"><span class="k">Vertical</span><span class="v">Commercial lines</span></div>
                  </div>
                  <div class="m-foot">
                    <span class="m-audit"><svg class="ico"><use href="#i-shield-check"/></svg> Encrypted audit &middot; SHA-256 manifest</span>
                    <span class="m-zta"><svg class="ico"><use href="#i-zap"/></svg> zta: 7 deterministic &middot; 1 LLM</span>
                  </div>
                </div>
              </div>
            </div>
            <div class="float-chip fc-1" aria-hidden="true">
              <span class="fc-ico"><svg class="ico"><use href="#i-file-check"/></svg></span>
              <span><span class="fc-t" style="display:block">Audit bundle ready</span><span class="fc-s">SHA-256 manifest &middot; examiner-ready</span></span>
            </div>
            <div class="float-chip fc-2" aria-hidden="true">
              <span class="fc-ico sky"><svg class="ico"><use href="#i-zap"/></svg></span>
              <span><span class="fc-t" style="display:block">Zero-token first</span><span class="fc-s">7 of 8 stages, no LLM call</span></span>
            </div>
            <div class="float-chip fc-3" aria-hidden="true">
              <span class="fc-ico violet"><svg class="ico"><use href="#i-shield"/></svg></span>
              <span><span class="fc-t" style="display:block">Licensed UW sign-off</span><span class="fc-s">Human decides &middot; every override traceable</span></span>
            </div>
          </div>
        </div>
        <div class="trust-strip reveal" aria-label="Security and compliance">
          <span class="trust-item"><svg class="ico sm"><use href="#i-check"/></svg> JWT + RBAC, org-scoped</span>
          <span class="trust-item"><svg class="ico sm"><use href="#i-check"/></svg> Line + staff UW desks</span>
          <span class="trust-item"><svg class="ico sm"><use href="#i-check"/></svg> Fernet encryption at rest</span>
          <span class="trust-item"><svg class="ico sm"><use href="#i-check"/></svg> Automated PII redaction</span>
          <span class="trust-item"><svg class="ico sm"><use href="#i-check"/></svg> SHA-256 audit ZIPs</span>
          <span class="trust-item"><svg class="ico sm"><use href="#i-check"/></svg> No LLM key required</span>
        </div>
        <div class="stats reveal" aria-label="Platform highlights">
          <div class="stat"><span class="num" data-target="4">0</span><span>Underwriting verticals</span></div>
          <div class="stat"><span class="num" data-target="24">0</span><span>Enterprise connectors</span></div>
          <div class="stat"><span class="num" data-target="145">0</span><span>Document types supported</span></div>
          <div class="stat"><span class="num" data-target="1400" data-suffix="+">0</span><span>Automated tests in CI</span></div>
        </div>
      </section>"""


def marquee_section() -> str:
    return """      <section id="marquee" style="padding-top:0;padding-bottom:3.5rem;border-bottom:none;">
        <p class="section-label reveal" style="justify-content:center;margin-left:auto;margin-right:auto;">Pulls from the systems you already use</p>
        <div class="marquee-wrap reveal" aria-hidden="true">
          <div class="marquee-track" id="marquee-track"></div>
        </div>
      </section>"""


def pipeline_section() -> str:
    return """      <section id="how-it-works">
        <div class="reveal">
          <p class="section-label">How it works</p>
          <h2>From intake to bind-ready decision</h2>
          <p class="section-desc">Click each stage to explore what happens inside the pipeline &mdash; no black boxes.</p>
        </div>
        <div class="pipeline-wrap reveal">
          <div class="pipeline-steps" role="tablist" aria-label="Pipeline stages">
            <button class="pipeline-step active" data-step="0" role="tab" aria-selected="true">
              <span class="step-num" aria-hidden="true">01</span>
              <span class="step-icon"><svg class="ico" aria-hidden="true"><use href="#i-search"/></svg></span>
              <span class="step-body"><strong>Triage</strong><span>Qualify the submission fast</span></span>
            </button>
            <button class="pipeline-step" data-step="1" role="tab" aria-selected="false">
              <span class="step-num" aria-hidden="true">02</span>
              <span class="step-icon"><svg class="ico" aria-hidden="true"><use href="#i-scale"/></svg></span>
              <span class="step-body"><strong>Risk &amp; Price</strong><span>Verify, analyze &amp; price</span></span>
            </button>
            <button class="pipeline-step" data-step="2" role="tab" aria-selected="false">
              <span class="step-num" aria-hidden="true">03</span>
              <span class="step-icon"><svg class="ico" aria-hidden="true"><use href="#i-file-check"/></svg></span>
              <span class="step-body"><strong>Decision</strong><span>UW memo &amp; deep dive</span></span>
            </button>
          </div>
          <div class="pipeline-panel" id="pipeline-panel" role="tabpanel"></div>
        </div>
      </section>"""


def testimonials_section() -> str:
    return """      <section id="testimonials">
        <div class="reveal">
          <p class="section-label">Trusted by underwriting teams</p>
          <h2>Underwriters work the exceptions, not the stack</h2>
          <p class="section-desc">Anonymized feedback from shadow pilots and pre-pilot working sessions.</p>
        </div>
        <div class="testimonial-grid reveal">
          <div class="testimonial-card">
            <div class="testimonial-stars">
              <svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg>
            </div>
            <p class="quote">The queue ranks our book before we open a single file. We stopped hunting through shared drives and started underwriting.</p>
            <div class="who">
              <span class="avatar av-1" aria-hidden="true">HU</span>
              <div class="who-text"><strong>Head of Underwriting</strong><span>MGA &middot; shadow pilot</span></div>
            </div>
          </div>
          <div class="testimonial-card">
            <div class="testimonial-stars">
              <svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg>
            </div>
            <p class="quote">Audit packages used to take days to assemble. Now every decision ships with its own SHA-256 manifest and full trace.</p>
            <div class="who">
              <span class="avatar av-2" aria-hidden="true">CL</span>
              <div class="who-text"><strong>Compliance Lead</strong><span>Carrier &middot; shadow pilot</span></div>
            </div>
          </div>
          <div class="testimonial-card">
            <div class="testimonial-stars">
              <svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg><svg class="ico"><use href="#i-star"/></svg>
            </div>
            <p class="quote">Shadow mode let us prove value without touching policy admin. Bind stayed off until our team approved the cutover.</p>
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
    value = """      <section id="what-you-get">
        <div class="reveal">
          <p class="section-label">What you get</p>
          <h2>One platform, three promises</h2>
          <p class="section-desc">Rytera is a workbench, not a pile of parsers. Here is what that means on the ground.</p>
        </div>
        <div class="feature-grid reveal">
          <div class="feature-card">
            <span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-file-check"/></svg></span>
            <h3>Bind-ready memos</h3>
            <p>ACORD, broker PDFs, loss runs, and W-2s become a bind-ready underwriting memo with quote, audit trail, and licensed sign-off.</p>
            <a class="card-link" href="/platform">Explore the platform <svg class="ico sm" aria-hidden="true"><use href="#i-arrow-right"/></svg></a>
          </div>
          <div class="feature-card">
            <span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-zap"/></svg></span>
            <h3>Token-light by design</h3>
            <p>~90% of pipeline tasks resolve deterministically &mdash; no LLM call, no token bill. The calls that do happen are budgeted and reported.</p>
            <a class="card-link" href="/technology">See the technology <svg class="ico sm" aria-hidden="true"><use href="#i-arrow-right"/></svg></a>
          </div>
          <div class="feature-card">
            <span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-briefcase"/></svg></span>
            <h3>Built for every desk</h3>
            <p>Line and staff underwriters across commercial lines, personal lines, mortgage, and lending &mdash; one workbench for every yes or no.</p>
            <a class="card-link" href="/underwriting">Meet your desks <svg class="ico sm" aria-hidden="true"><use href="#i-arrow-right"/></svg></a>
          </div>
        </div>
      </section>"""

    how = pipeline_section()
    how = how + """
        <div class="cta reveal">
          <a class="btn btn-primary" href="/technology">
            Deep dive into the pipeline
            <svg class="ico sm" aria-hidden="true"><use href="#i-arrow-right"/></svg>
          </a>
        </div>"""

    return (
        hero_home()
        + "\n\n"
        + marquee_section()
        + "\n\n"
        + value
        + "\n\n"
        + how
        + "\n\n"
        + testimonials_section()
        + "\n\n"
        + contact_section()
    )


def platform_main() -> str:
    compare = """      <section id="ai-native">
        <div class="reveal">
          <p class="section-label">The problem &amp; the fix</p>
          <h2>Built for decisions, not document storage</h2>
          <p class="section-desc">Legacy workbenches were built to hold files. Underwriting was left to do the hard part &mdash; reading them all. Rytera flips the order: the platform does the reading, scoring, and pricing, so your team makes the decisions.</p>
        </div>
        <div class="compare reveal">
          <div class="compare-col">
            <div class="compare-head legacy"><svg class="ico" aria-hidden="true"><use href="#i-x-circle"/></svg> Legacy Workbench</div>
            <ul class="compare-list">
              <li>Intake from a fax queue or a shared drive</li>
              <li>Manual triage &mdash; underwriters hunt for red flags</li>
              <li>Re-keying data across screens and systems</li>
              <li>Decisions after hours of document review</li>
              <li>Appetite and exposure checked in the underwriter's head</li>
              <li>No audit trail of why a file was declined</li>
            </ul>
          </div>
          <div class="compare-col">
            <div class="compare-head ai"><svg class="ico" aria-hidden="true"><use href="#i-check-circle"/></svg> Rytera AI-native</div>
            <ul class="compare-list">
              <li>Intake from 24 connectors &mdash; email, S3, SharePoint, SFTP</li>
              <li>Context-aware triage that prioritizes by appetite, impact, and exposure</li>
              <li>Documents parsed, reconciled, and deduplicated automatically</li>
              <li>Bind-ready UW memo in minutes &mdash; not hours</li>
              <li>Appetite filters, COPE, and exposure scored before a human opens the file</li>
              <li>Encrypted audit trail behind every decision</li>
            </ul>
          </div>
        </div>
      </section>"""

    agentic = """      <section id="agentic">
        <div class="reveal">
          <p class="section-label">The agentic AI platform</p>
          <h2>Replace the legacy workbench</h2>
          <p class="section-desc">A 3-phase funnel &mdash; Triage &rarr; Risk &amp; Price &rarr; Decision &mdash; plus a deep dive that re-runs oracles, portfolio, reinsurance, and fraud ML on demand. Your underwriters work the exceptions, not the stack.</p>
        </div>
        <div class="agent-grid reveal">
          <div class="agent-card">
            <span class="ac-ico"><svg class="ico" aria-hidden="true"><use href="#i-gauge"/></svg></span>
            <h3>Real-time steering</h3>
            <p>Live submission queue ranked by appetite fit, impact, and exposure &mdash; underwriters see the highest-value files first and steer the book in real time.</p>
          </div>
          <div class="agent-card">
            <span class="ac-ico"><svg class="ico" aria-hidden="true"><use href="#i-list-checks"/></svg></span>
            <h3>Context-aware AI</h3>
            <p>Prioritization built for appetite, impact, and exposure &mdash; not a generic score. Appetite filters, coastal CAT, NCCI class codes, and loss ratios fire before a human opens the file.</p>
          </div>
          <div class="agent-card">
            <span class="ac-ico"><svg class="ico" aria-hidden="true"><use href="#i-shield-check"/></svg></span>
            <h3>Human-in-the-loop</h3>
            <p>Licensed UW sign-off, authority matrix tiers, and referral queues. AI proposes, underwriters dispose &mdash; every override traceable.</p>
          </div>
          <div class="agent-card">
            <span class="ac-ico"><svg class="ico" aria-hidden="true"><use href="#i-refresh"/></svg></span>
            <h3>Grows with you</h3>
            <p>Shadow pilot &rarr; live oracle feeds &rarr; policy admin integration. Bind stays off until your team approves the cutover.</p>
          </div>
        </div>
      </section>"""

    tabs = """      <section id="features">
        <div class="reveal">
          <p class="section-label">Deep-dive underwriting</p>
          <h2>Vertical by vertical, further than a shared dashboard</h2>
          <p class="section-desc">
            Each vertical ships specialist agents, filing-grade rating, and regulatory checks tuned to its own workflow. Select a vertical to explore its deep dive, or see the shared <strong>Connect &amp; pull</strong> intake that powers all four.
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
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-file-text"/></svg></span><h3>Document ingestion</h3><p>ACORD XML, broker slips, loss runs, SOV, inspections &mdash; auto-classified, parsed, and PII-screened for pilots.</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-bot"/></svg></span><h3>Specialist agents</h3><p>A focused 3-phase funnel &mdash; Triage &rarr; Risk &amp; Price &rarr; Decision &mdash; with deep-dive analysis on demand.</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-banknote"/></svg></span><h3>Premium &amp; ready bind</h3><p>ACCEPT / CONDITIONAL_ACCEPT / REFER / DECLINE with indicated premium. Ready mode enables PAS bind after licensed UW sign-off when Guidewire is configured.</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-search"/></svg></span><h3>Submission journey</h3><p>Full pipeline panel per job &mdash; COPE, live oracles, provenance, pricing build-up, and encrypted audit trail.</p></div>
          </div>
        </div>
        <div class="tab-panel reveal" id="tab-personal" role="tabpanel">
          <div class="feature-grid">
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-home"/></svg></span><h3>Homeowners</h3><p>HO-3 applications, dwelling coverage, CLUE checks, and inspection-based risk scoring with filing-grade rate manuals.</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-car"/></svg></span><h3>Personal auto</h3><p>Applications, MVRs, and vehicle declarations &mdash; driver &amp; vehicle risk scoring with state rate manual build-up.</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-heart-pulse"/></svg></span><h3>Term life</h3><p>Applications, paramedical exams, and medical underwriting &mdash; mortality scoring with life rate and medical guides.</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-file-check"/></svg></span><h3>Filing-grade rating</h3><p>Homeowners, auto, and life rating engines driven by tracked rate manuals and state filing books.</p></div>
          </div>
        </div>
        <div class="tab-panel reveal" id="tab-mortgage" role="tabpanel">
          <div class="feature-grid">
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-inbox"/></svg></span><h3>30+ document types</h3><p>W-2, 1040, credit reports, appraisals, bank statements, rent rolls.</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-chart"/></svg></span><h3>Income &amp; collateral</h3><p>Specialist agents for income, credit, assets, and collateral verification.</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-lock"/></svg></span><h3>Rate lock &amp; compliance</h3><p>Approve / Refer / Suspend / Deny with TRID, Reg Z, and HMDA checks.</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-zap"/></svg></span><h3>Async processing</h3><p>Celery workers with org-scoped jobs and HMAC-signed webhooks for LOS integration.</p></div>
          </div>
        </div>
        <div class="tab-panel reveal" id="tab-lending" role="tabpanel">
          <div class="feature-grid">
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-building"/></svg></span><h3>Consumer &amp; commercial</h3><p>Business and consumer loan applications with unified decisioning.</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-pie"/></svg></span><h3>Credit &amp; pricing</h3><p>Credit risk engine, compliance rules, and dynamic pricing in one pipeline.</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-scale"/></svg></span><h3>Regulatory compliance</h3><p>Reg B, ECOA, adverse action notices, and collateral verification.</p></div>
            <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-shield-check"/></svg></span><h3>Shared security</h3><p>JWT auth, org-scoped isolation, and encrypted audit trail across all verticals.</p></div>
          </div>
        </div>
      </section>"""

    bento = """      <section id="capabilities">
        <div class="reveal">
          <p class="section-label">Platform capabilities</p>
          <h2>Controls, intake, and audit you can defend</h2>
          <p class="section-desc">
            Production underwriting needs more than a model score. Rytera ships governance, redaction, connectors,
            triage, and examiner-ready audit as first-class product &mdash; not bolt-ons.
          </p>
        </div>
        <div class="bento reveal">
          <div class="bento-card wide ac-blue">
            <p class="bento-kicker"><svg class="ico"><use href="#i-shield-check"/></svg> Governance</p>
            <h3>Human-in-the-loop by design</h3>
            <p>Licensed UW sign-off, checkpoint resolution, authority matrix tiers, and referral queues &mdash; AI assists, humans decide. Shadow pilots keep bind off until your team is ready.</p>
          </div>
          <div class="bento-card ac-green">
            <p class="bento-kicker"><svg class="ico"><use href="#i-lock"/></svg> Privacy</p>
            <h3>PII redaction</h3>
            <p>Automated SSN, EIN, and DOB detection with document redaction before packages enter the pilot lane.</p>
          </div>
          <div class="bento-card ac-sky">
            <p class="bento-kicker"><svg class="ico"><use href="#i-cable"/></svg> Intake</p>
            <h3>24 connectors</h3>
            <p>S3, SharePoint, Applied Epic, real IMAP email, SFTP, and more &mdash; live when configured, honest simulated otherwise. One Connect &amp; pull hub powers insurance, mortgage, and lending intake.</p>
          </div>
          <div class="bento-card ac-violet">
            <p class="bento-kicker"><svg class="ico"><use href="#i-list-checks"/></svg> Operations</p>
            <h3>Queue triage</h3>
            <p>Prioritized submission queue with fit scores and journey strips so UW time goes to the right files first.</p>
          </div>
          <div class="bento-card wide ac-green">
            <p class="bento-kicker"><svg class="ico"><use href="#i-file-check"/></svg> Compliance</p>
            <h3>Encrypted audit bundles</h3>
            <p>SHA-256 manifest ZIP exports for regulatory examiner review &mdash; every decision, override, and oracle call traceable.</p>
          </div>
          <div class="bento-card ac-amber">
            <p class="bento-kicker"><svg class="ico"><use href="#i-database"/></svg> Oracles</p>
            <h3>Live loss history</h3>
            <p>CLUE, A-PLUS, NCCI, and CAT feeds in auto mode &mdash; no fake clean history when keys are missing.</p>
          </div>
          <div class="bento-card ac-blue">
            <p class="bento-kicker"><svg class="ico"><use href="#i-server"/></svg> Reliability</p>
            <h3>Durable job stores</h3>
            <p>Redis or file-backed jobs survive restarts &mdash; no silent in-memory loss in pilot or bank mode.</p>
          </div>
          <div class="bento-card ac-violet">
            <p class="bento-kicker"><svg class="ico"><use href="#i-refresh"/></svg> Renewals</p>
            <h3>Renewal &amp; premium audit</h3>
            <p>Pre-renewal tracking, premium audit, and loss feedback loops keep the book healthy between policy cycles.</p>
          </div>
          <div class="bento-card ac-amber">
            <p class="bento-kicker"><svg class="ico"><use href="#i-pie"/></svg> Portfolio</p>
            <h3>Book &amp; concentration</h3>
            <p>Portfolio exposure, concentration buckets, and top lines of business &mdash; with market-cycle phase adjustments built in.</p>
          </div>
          <div class="bento-card ac-sky">
            <p class="bento-kicker"><svg class="ico"><use href="#i-gauge"/></svg> Model intelligence</p>
            <h3>LLM performance &amp; price benchmark</h3>
            <p>Continuous benchmarking &mdash; TTFT, output speed, reasoning tokens, and blended 7:2:1 per-token cost &mdash; gated by quality thresholds and tracked on the eval dashboard.</p>
          </div>
        </div>
      </section>"""

    return (
        sub_page_hero(
            "The platform",
            "One workbench for every submission",
            "From messy intake to a bind-ready memo &mdash; Rytera replaces the legacy workbench with an AI-native pipeline your underwriters actually review, not a pile of parsed PDFs.",
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
        + bento
        + "\n\n"
        + contact_section()
    )


def technology_main() -> str:
    zta = """      <section id="zta">
        <div class="reveal">
          <p class="section-label">Zero Token Architecture</p>
          <h2>Efficiency you can measure</h2>
          <p class="section-desc">
            Most AI underwriting tools burn tokens on everything. Rytera asks: <em>can code, rules, or a trained model
            solve this deterministically?</em> Most of underwriting can &mdash; so you get faster, cheaper, fully reproducible
            decisions, and every LLM call that does happen is budgeted, tracked, and reported in each job's
            <strong>zta_report</strong>.
          </p>
        </div>
        <div class="zta-ladder reveal">
          <div class="zta-step L1">
            <div class="step-top">
              <span class="step-ico"><svg class="ico" aria-hidden="true"><use href="#i-cpu"/></svg></span>
              <span class="step-num">Layer 1</span>
            </div>
            <h3>Deterministic code</h3>
            <p>Parsers, provenance, reconciliation, COPE, rating engines, and compliance rules solve everything they can &mdash; with zero tokens and full reproducibility.</p>
            <span class="tokens zero"><svg class="ico" aria-hidden="true"><use href="#i-check"/></svg> 0 tokens &middot; 100% reproducible</span>
          </div>
          <div class="zta-flow" aria-hidden="true"><svg class="ico"><use href="#i-arrow-right"/></svg></div>
          <div class="zta-step L2">
            <div class="step-top">
              <span class="step-ico"><svg class="ico" aria-hidden="true"><use href="#i-bot"/></svg></span>
              <span class="step-num">Layer 2</span>
            </div>
            <h3>Trained ML</h3>
            <p>Eight gradient-boosted models score loss, fraud, churn, premium, portfolio risk, and default &mdash; deterministic predictions, no prompt involved.</p>
            <span class="tokens zero"><svg class="ico" aria-hidden="true"><use href="#i-check"/></svg> 0 tokens &middot; deterministic</span>
          </div>
          <div class="zta-flow" aria-hidden="true"><svg class="ico"><use href="#i-arrow-right"/></svg></div>
          <div class="zta-step L3">
            <div class="step-top">
              <span class="step-ico"><svg class="ico" aria-hidden="true"><use href="#i-zap"/></svg></span>
              <span class="step-num">Layer 3</span>
            </div>
            <h3>LLM &mdash; only when needed</h3>
            <p>Reasoning tasks that genuinely need it, gated by per-job budgets and coverage thresholds &mdash; never for work code can already solve.</p>
            <span class="tokens one"><svg class="ico" aria-hidden="true"><use href="#i-sliders"/></svg> budgeted &middot; accounted</span>
          </div>
        </div>
        <div class="zta-stats reveal">
          <div class="zta-stat">
            <span class="zstat-ico green"><svg class="ico" aria-hidden="true"><use href="#i-cpu"/></svg></span>
            <div class="body"><span class="num">~90%</span><p>of typical pipeline tasks resolve deterministically</p></div>
          </div>
          <div class="zta-stat">
            <span class="zstat-ico blue"><svg class="ico" aria-hidden="true"><use href="#i-database"/></svg></span>
            <div class="body"><span class="num">0</span><p>tokens for ACORD parsing, rating, reconciliation</p></div>
          </div>
          <div class="zta-stat">
            <span class="zstat-ico violet"><svg class="ico" aria-hidden="true"><use href="#i-bot"/></svg></span>
            <div class="body"><span class="num" data-target="8">0</span><p>trained ML models in the model registry</p></div>
          </div>
        </div>
      </section>"""

    security = """      <section id="security">
        <div class="reveal">
          <p class="section-label">Security &amp; audit</p>
          <h2>Every decision defensible</h2>
          <p class="section-desc">Encryption, access control, and examiner-ready audit are engineered into the pipeline &mdash; not bolted on after.</p>
        </div>
        <div class="feature-grid reveal">
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-lock"/></svg></span><h3>Encryption at rest</h3><p>Fernet-encrypted job stores with org-scoped isolation, and automated SSN / EIN / DOB redaction before packages enter the pilot lane.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-key"/></svg></span><h3>Access control</h3><p>JWT auth with RBAC tiers and per-org data isolation on every job, decision, and audit record.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-file-check"/></svg></span><h3>Examiner-ready audit</h3><p>Every decision, override, and oracle call ships in a SHA-256 manifest ZIP built for regulatory review.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-shield-check"/></svg></span><h3>Human-in-the-loop</h3><p>Licensed UW sign-off, authority-matrix tiers, and referral queues. AI proposes; underwriters dispose; every override is traceable.</p></div>
        </div>
        <div class="trust-strip reveal" aria-label="Security and compliance">
          <span class="trust-item"><svg class="ico sm"><use href="#i-check"/></svg> JWT + RBAC, org-scoped</span>
          <span class="trust-item"><svg class="ico sm"><use href="#i-check"/></svg> Fernet encryption at rest</span>
          <span class="trust-item"><svg class="ico sm"><use href="#i-check"/></svg> Automated PII redaction</span>
          <span class="trust-item"><svg class="ico sm"><use href="#i-check"/></svg> SHA-256 audit ZIPs</span>
          <span class="trust-item"><svg class="ico sm"><use href="#i-check"/></svg> No LLM key required</span>
        </div>
      </section>"""

    return (
        sub_page_hero(
            "Technology",
            "Deterministic first. Token-light always.",
            "Rytera is built on Zero Token Architecture: code and trained ML solve what they can, LLMs are invoked only when reasoning genuinely requires it, and every token is accounted for.",
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
        + contact_section()
    )


def underwriting_main() -> str:
    audience = """      <section id="audience">
        <div class="reveal">
          <p class="section-label">Who it's for</p>
          <h2>Built for every desk that says yes or no to risk</h2>
          <p class="section-desc">
            Whether you quote a single account or steer a national book, Rytera fits the way your desk already works &mdash;
            from branch line underwriters to home-office staff underwriters, and across every vertical.
          </p>
        </div>
        <div class="audience-grid reveal">
          <div class="audience-card ac-blue">
            <span class="ac-ico"><svg class="ico" aria-hidden="true"><use href="#i-building"/></svg></span>
            <h3>Commercial carriers &amp; MGAs</h3>
            <p class="who">Line and staff underwriters running commercial books.</p>
            <p>Get a live ranked submission queue, bind-ready memos, and licensed sign-off &mdash; GL, property, and specialty lines.</p>
          </div>
          <div class="audience-card ac-green">
            <span class="ac-ico"><svg class="ico" aria-hidden="true"><use href="#i-home"/></svg></span>
            <h3>Personal lines carriers</h3>
            <p class="who">Homeowners, auto, and term-life underwriting teams.</p>
            <p>Get filing-grade rating from tracked rate manuals, CLUE / MVR checks, and compliant state rate build-ups.</p>
          </div>
          <div class="audience-card ac-sky">
            <span class="ac-ico"><svg class="ico" aria-hidden="true"><use href="#i-inbox"/></svg></span>
            <h3>Mortgage lenders</h3>
            <p class="who">Underwriters and processing teams.</p>
            <p>Get income, asset, and collateral verification across 30+ document types &mdash; with TRID, Reg Z, and HMDA checks built in.</p>
          </div>
          <div class="audience-card ac-violet">
            <span class="ac-ico"><svg class="ico" aria-hidden="true"><use href="#i-banknote"/></svg></span>
            <h3>Commercial lenders</h3>
            <p class="who">Credit and loan underwriting desks.</p>
            <p>Get consumer and business loan decisioning with a credit risk engine, dynamic pricing, and Reg B / ECOA compliance.</p>
          </div>
          <div class="audience-card ac-amber">
            <span class="ac-ico"><svg class="ico" aria-hidden="true"><use href="#i-layers"/></svg></span>
            <h3>Program administrators &amp; aggregators</h3>
            <p class="who">MGAs running books on behalf of carriers.</p>
            <p>Get appetite steering across a portfolio, shadow pilots with bind off, and a clean cutover when you're ready.</p>
          </div>
        </div>
      </section>"""

    desks = """      <section id="uw-desks">
        <div class="reveal">
          <p class="section-label">Underwriting desks</p>
          <h2>Built for line and staff underwriters</h2>
          <p class="section-desc">
            Carriers distinguish branch line underwriters who run the process from home-office staff
            underwriters who set policy. Rytera covers both desks &mdash; and the overlap on large or unusual accounts.
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
              <li>Submission journey through triage, rating, memo, and licensed sign-off</li>
            </ul>
          </div>
          <div class="feature-card">
            <span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-landmark"/></svg></span>
            <h3>Staff underwriter desk</h3>
            <p>Home-office underwriters make and implement underwriting policy.</p>
            <ul>
              <li>Market research, coverage development, and rating-plan reviews (ISO / AAIS / NCCI)</li>
              <li>UW guides, policy statements, and branch file audits</li>
              <li>Experience evaluation and technical training for line underwriters</li>
            </ul>
          </div>
        </div>
      </section>"""

    ratemaking = """      <section id="ratemaking">
        <div class="reveal">
          <p class="section-label">Ratemaking &amp; Pricing</p>
          <h2>Rates built like an actuary builds them</h2>
          <p class="section-desc">Ratemaking turns past loss statistics into future rates. Rytera prices with the three textbook methods &mdash; <strong>pure premium</strong>, <strong>loss ratio</strong>, and <strong>judgment</strong> &mdash; and checks every rate against the statutory goals of <strong>adequate</strong>, <strong>not excessive</strong>, and <strong>not unfairly discriminatory</strong>, plus the five ideal rate characteristics. It also models <strong>loss reserve estimation</strong>, <strong>investment income</strong> on reserves, and <strong>projected expenses</strong> with proper general-administrative allocation across lines.</p>
        </div>
        <div class="feature-grid">
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-layers"/></svg></span><h3>Base-rate build-up</h3><p>The three-step process: future claims (pure premium) + future expenses (expense loading) = base rate, then load for contingencies and profit.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-chart"/></svg></span><h3>Loss ratio method</h3><p>Projected loss ratio (trend &times; loss development) vs permissible loss ratio to compute the indicated rate change.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-scale"/></svg></span><h3>Statutory review</h3><p>Every rate is verified adequate, not excessive, and free of unfairly discriminatory classification before it is offered.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-book"/></svg></span><h3>Advisory loss costs</h3><p>ISO, AAIS, NCCI, and Surety Association loss costs &mdash; carriers add their own expense and profit factors.</p></div>
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
            "Line underwriters run the process. Staff underwriters set the policy. Rytera gives both a live ranked queue, bind-ready memos, and filing-grade rating &mdash; across insurance, mortgage, and lending.",
            secondary="/platform",
            secondary_label="Explore the platform",
        )
        + "\n\n"
        + audience
        + "\n\n"
        + desks
        + "\n\n"
        + ratemaking
        + "\n\n"
        + contact_section()
    )


def integrations_main() -> str:
    modes = """      <section id="modes">
        <div class="reveal">
          <p class="section-label">How connectors run</p>
          <h2>Live, simulated, or auto &mdash; never fabricated</h2>
          <p class="section-desc">Every adapter supports three honest modes. Auto uses live feeds when keys are present and flags gaps instead of guessing clean data.</p>
        </div>
        <div class="feature-grid reveal">
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-cable"/></svg></span><h3>Live</h3><p>Real connectors wired to your accounts &mdash; IMAP email, SFTP, S3, SharePoint, Applied Epic, and the loss-history oracles.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-sliders"/></svg></span><h3>Simulated</h3><p>Honest demo data when keys aren't connected &mdash; nothing fabricated, nothing mislabeled as real history.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-refresh"/></svg></span><h3>Auto</h3><p>Uses live feeds whenever keys are present; otherwise surfaces gaps for resolution instead of inventing clean loss history.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-gauge"/></svg></span><h3>Health monitoring</h3><p>Every adapter reports status. Pilots see live / simulated / auto at a glance and get alerted before a feed goes stale.</p></div>
        </div>
      </section>"""

    integ = """      <section id="integrations">
        <div class="reveal">
          <p class="section-label">Integrations</p>
          <h2>Connects to the systems you already use</h2>
          <p class="section-desc">Filter by category. Every adapter supports live, simulated, and auto modes with health monitoring.</p>
        </div>
        <div class="filter-bar reveal">
          <button class="filter-btn active" data-filter="all">
            <svg class="ico sm"><use href="#i-sliders"/></svg> All
          </button>
          <button class="filter-btn" data-filter="oracles">Oracles</button>
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
            "One Connect &amp; pull hub feeds insurance, mortgage, and lending intake &mdash; policy admin, CRM, oracles, and document sources, each with live, simulated, and auto modes.",
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
        + contact_section()
    )


def company_main() -> str:
    about = """      <section id="about">
        <div class="reveal">
          <p class="section-label">About Rytera</p>
          <h2>We build underwriting software for underwriters</h2>
          <p class="section-desc">Rytera, Inc. is an AI-native underwriting platform for carriers, MGAs, and aggregators across insurance, mortgage, and lending.</p>
        </div>
        <div class="feature-grid reveal">
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-users"/></svg></span><h3>Who we build for</h3><p>Commercial &amp; personal lines carriers, MGAs and program administrators, mortgage lenders, and commercial lenders &mdash; one platform for every desk.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-refresh"/></svg></span><h3>The pilot model</h3><p>Shadow first, bind last. Measure accuracy on your real book before any policy admin integration turns on &mdash; with a clean cutover when you're ready.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-shield-check"/></svg></span><h3>Security &amp; compliance</h3><p>Fernet encryption, JWT + RBAC, org-scoped isolation, automated PII redaction, and a SHA-256 audit bundle behind every decision.</p></div>
          <div class="feature-card"><span class="icon"><svg class="ico" aria-hidden="true"><use href="#i-mail"/></svg></span><h3>Get in touch</h3><p>Book a walkthrough or email <a class="contact-email" href="mailto:hello@rytera.ai">hello@rytera.ai</a> &mdash; our team responds within one business day.</p></div>
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
            "Rytera, Inc.",
            "We build AI-native underwriting for carriers, MGAs, and aggregators &mdash; with human-in-the-loop governance, zero-token efficiency, and audit you can hand to a regulator.",
            primary="book",
            secondary="/dashboard",
            secondary_label="Open the live dashboard",
        )
        + "\n\n"
        + about
        + "\n\n"
        + faq
        + "\n\n"
        + contact_section()
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
            "Rytera - AI-Native Underwriting for Carriers, MGAs & Aggregators",
            "Rytera turns messy submissions - ACORD, broker PDFs, loss runs, W-2s - into bind-ready underwriting memos with quote, audit trail, and licensed sign-off. One agentic platform for line and staff underwriters.",
            "",
            "Bind-ready decisions in minutes, not days. One agentic platform for line and staff underwriters across insurance, mortgage, and lending.",
            home_main(),
        ),
        "platform.html": page(
            "Rytera - The AI-Native Platform",
            "From messy intake to a bind-ready memo. Rytera's AI-native pipeline triages, verifies, and prices submissions - Triage, Risk & Price, Decision - with human-in-the-loop sign-off.",
            "platform",
            "Replace the legacy workbench: an AI-native pipeline that triages, verifies, and prices submissions into bind-ready UW memos.",
            platform_main(),
        ),
        "technology.html": page(
            "Rytera - Zero Token Architecture, Security & Audit",
            "Zero Token Architecture: deterministic code and trained ML solve most of underwriting before any LLM call. Every token budgeted, tracked, and reported. Encrypted audit bundles and RBAC.",
            "technology",
            "Deterministic first, token-light always. ZTA keeps decisions fast, cheap, reproducible - with audit bundles a regulator can review.",
            technology_main(),
        ),
        "underwriting.html": page(
            "Rytera - Built for Line & Staff Underwriters",
            "Line and staff underwriting desks for commercial lines, personal lines, mortgage, and lending. Live ranked queue, bind-ready memos, and filing-grade ratemaking.",
            "underwriting",
            "Built for every desk that says yes or no to risk - line and staff underwriters across insurance, mortgage, and lending.",
            underwriting_main(),
        ),
        "integrations.html": page(
            "Rytera - Integrations & Connectors",
            "24 connectors: policy admin, CRM, oracles, and document sources - Guidewire, Duck Creek, Applied Epic, CLUE, A-PLUS, NCCI, S3, SharePoint, and more. Live, simulated, and auto modes.",
            "integrations",
            "Connects to the systems you already use - policy admin, CRM, oracles, and document sources in live, simulated, or auto modes.",
            integrations_main(),
        ),
        "company.html": page(
            "Rytera - About, FAQ & Contact",
            "Rytera, Inc. - AI-native underwriting for carriers, MGAs, and aggregators. Frequently asked questions, our pilot model, and how to reach the team.",
            "company",
            "About Rytera, Inc., our shadow-first pilot model, FAQ, and how to book a walkthrough.",
            company_main(),
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
