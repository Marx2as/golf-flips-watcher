"""
Vinted marketplace fetcher.

Vinted does not expose a public, stable API.  Community members have
reverse-engineered certain endpoints, but these are unofficial and
subject to change without notice.  This module provides a minimal
fetcher that queries the current JSON endpoints used by the Vinted
website.  Use at your own risk and disable via ``ENABLE_VINTED`` if
these calls stop working.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import requests

from .settings import Settings

logger = logging.getLogger(__name__)


class VintedFetcher:
    """Client for fetching new listings from Vinted.

    The Vinted website exposes an internal JSON API for its catalogue.  This
    client constructs requests to that API and parses the response into a
    simplified dictionary.  Because this endpoint is unofficial, it may
    break at any time.  Set ``ENABLE_VINTED=False`` in your environment
    to disable this fetcher.
    """

    BASE_URL_TEMPLATE = "https://www.vinted.{region}/api/v2/catalog/items"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()

    def fetch_listings(self, keywords: List[str], max_price: Optional[float] = None) -> List[Dict[str, Any]]:
        """Fetch the newest listings from Vinted matching the keywords.

        Parameters
        ----------
        keywords: List[str]
            Terms to search for.  They are combined with spaces (AND semantics).
        max_price: float, optional
            Maximum price filter.  Only items priced at or below this value
            will be returned.

        Returns
        -------
        List[Dict[str, Any]]
            A list of simplified listing dictionaries.
        """
        if not self.settings.ENABLE_VINTED:
            logger.info("Skipping Vinted fetch – disabled via configuration")
            return []
        region = self.settings.VINTED_REGION.lower().strip()
        base_url = self.BASE_URL_TEMPLATE.format(region=region)
        query = " ".join(keywords)
        params: Dict[str, Any] = {
            "search_text": query,
            "page": 1,
            "per_page": 50,
            "order": "newest_first",
        }
        if max_price is not None:
            params["price_to"] = int(max_price)

        try:
            response = self.session.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.error("Error querying Vinted API: %s", exc)
            return []

        items: List[Dict[str, Any]] = []
        for item in data.get("items", []):
            try:
                listing = self._simplify_item(item)
                items.append(listing)
            except Exception as exc:
                logger.debug("Skipping Vinted item due to parse error: %s", exc)
        return items

    def _simplify_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant fields from a Vinted item record."""
        price_cents = item.get("price", {}).get("numeric")
        shipping_cost_cents = None
        # Vinted may return shipping info nested under service info; use fallback
        shipping_options = item.get("service_fee", {})
        if shipping_options and isinstance(shipping_options, dict):
            shipping_cost_cents = shipping_options.get("amount")
        return {
            "marketplace": "vinted",
            "listing_id": str(item.get("id")),
            "title": item.get("title"),
            "url": f"https://www.vinted.{self.settings.VINTED_REGION}/items/{item.get('id')}",
            "brand": item.get("brand_title"),
            "model": item.get("model"),
            "condition": item.get("status"),
            "price": float(price_cents) if price_cents is not None else None,
            "currency": item.get("currency", "EUR"),
            "shipping_cost": float(shipping_cost_cents) if shipping_cost_cents is not None else None,
            "location": item.get("city", {}).get("title"),
        }
