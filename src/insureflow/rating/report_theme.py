"""Shared Rytera branding for every generated document (quote, report, memo).

Single source of truth for the decision-color palette and the wordmark
treatment so the quote PDF, the full report PDF, and the on-screen dashboard
never disagree on what a DECLINE looks like versus a plain critical finding.
"""

from __future__ import annotations

# Brand palette — mirrors the frontend's `brand` token (frontend/tailwind.config.js)
# so the PDF and the dashboard read as the same product.
BRAND_INK = "#0f172a"
BRAND_ACCENT = "#5b8def"
BRAND_ACCENT_LIGHT = "#8bb0f7"

# Decision colors. DECLINE is deliberately a much darker, more saturated red
# than a "critical" finding badge (#dc2626-family) — a decline must read as
# categorically more severe than any single finding, not the same hue.
DECISION_COLORS: dict[str, str] = {
    "ACCEPT": "#15803d",
    "CONDITIONAL_ACCEPT": "#b45309",
    "REFER": "#0369a1",
    "DECLINE": "#7f1d1d",
}
DECISION_COLORS_DEFAULT = "#334155"

# Severity palette, kept distinct from DECISION_COLORS so a DECLINE badge
# never collides visually with a CRITICAL finding chip.
SEVERITY_COLORS: dict[str, str] = {
    "CRITICAL": "#dc2626",
    "HIGH": "#ea580c",
    "MODERATE": "#b45309",
    "LOW": "#15803d",
}


def decision_color(decision: str) -> str:
    return DECISION_COLORS.get((decision or "").upper(), DECISION_COLORS_DEFAULT)


# Single source of truth for every generated document's font stack.
#
# These documents are rendered by WeasyPrint (Pango/fontconfig), not a
# browser — "-apple-system", "BlinkMacSystemFont", "Segoe UI", and "SF Mono"
# are browser/OS integration keywords that mean nothing to Pango. It silently
# skips each one it can't resolve and falls through the stack; in the
# production container (python:3.12-slim, see Dockerfile) none of those
# names exist and no font package is guaranteed installed, so fontconfig can
# end up substituting a *different* fallback font per glyph within the same
# line — particularly for the em/en-dashes (—/–), middot (·), and bullet
# characters used throughout these documents. Different font files have
# different ascent/descent/baseline metrics at the same declared font-size,
# so that per-glyph substitution is what reads as "characters sitting above
# or below their line." Naming one real, broadly-available family first
# (installed explicitly via `fonts-dejavu-core` in the Dockerfile) makes
# every glyph in a paragraph resolve from the same font file.
PDF_FONT_STACK = "'DejaVu Sans', 'Liberation Sans', Arial, sans-serif"
PDF_MONO_FONT_STACK = "'DejaVu Sans Mono', 'Liberation Mono', Consolas, monospace"


def wordmark_html(size_px: int = 20) -> str:
    """Text-lockup wordmark — no logo asset exists in the repo, so this is a
    deliberately simple, consistent typographic treatment rather than a
    fabricated logo image. Colored via CSS classes (``.wordmark``/``.wm-accent``)
    so screen (dark) and print (light) themes can each supply their own
    color without touching this markup — see WORDMARK_CSS.
    """
    return f'<span class="wordmark" style="font-size:{size_px}px;">Ryt<span class="wm-accent">era</span></span>'


# Shared CSS for the wordmark — same rules dropped into every document's
# <style> block (both the screen/dark theme and the @media print override).
WORDMARK_CSS_DARK = (
    ".wordmark { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; "
    "font-weight: 800; letter-spacing: -0.02em; color: #f8fafc; }"
    f" .wordmark .wm-accent {{ color: {BRAND_ACCENT_LIGHT}; }}"
)
WORDMARK_CSS_PRINT = (
    ".wordmark { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; "
    f"font-weight: 800; letter-spacing: -0.02em; color: {BRAND_INK} !important; }}"
    f" .wordmark .wm-accent {{ color: {BRAND_ACCENT} !important; }}"
)
