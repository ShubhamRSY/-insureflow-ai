"""Commercial Lines — dedicated per-product logic paths.

Per-product rating and underwriting decisions for the live commercial
specialty/property/casualty products are owned by
``insureflow.commercial.lobs.<product>`` (dispatched from
``insureflow.rating.engine``), the same pattern used by
``insureflow.life.lobs`` and ``insureflow.health.lobs``.
"""

from __future__ import annotations
