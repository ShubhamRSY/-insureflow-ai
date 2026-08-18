from __future__ import annotations

import logging
from typing import Any

from insureflow.regulatory.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class SerffCollector(BaseCollector):
    """SERFF Filing System collector — contract-gated.

    When SERFF API is not available (no contract), returns mock data
    based on publicly known filing activity patterns.
    """

    def collect(self) -> list[dict[str, Any]]:
        """Poll SERFF for filing activity.

        If API key is configured, calls SERFF API.
        Otherwise, returns mock/placeholder data indicating SERFF
        integration requires a contract.
        """
        api_key = self.config.get("api_key", "")
        if not api_key:
            return self._mock_data()
        return self._api_collect(api_key)

    def _api_collect(self, api_key: str) -> list[dict[str, Any]]:
        """Real SERFF API collection (requires contract)."""
        logger.info("SERFF API collection not yet implemented — requires contract")
        return []

    def _mock_data(self) -> list[dict[str, Any]]:
        """Return mock data indicating SERFF is not connected."""
        return [
            {
                "source": "serff",
                "title": "SERFF Integration — Contract Required",
                "url": "https://naic.org/serff/",
                "published": "",
                "raw": {
                    "status": "contract_required",
                    "message": "SERFF API access requires a contract. Email api@naic.org to request access.",
                    "mock": True,
                },
            }
        ]
