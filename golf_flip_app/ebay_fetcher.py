"""
eBay marketplace fetcher.

This module provides functionality to query the eBay Browse API for new
listings matching a set of keywords and filters.  It supports both
application key (AppID) access and OAuth client credentials flows.  The
fetcher yields a list of simplified listing dictionaries that are
suitable for further processing by the scoring and notification
pipeline.

The code here intentionally avoids making direct calls when API
credentials are missing.  Instead, it returns an empty list so that
tests and dry runs can proceed without external dependencies.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import requests

from .settings import Settings

logger = logging.getLogger(__name__)


class EbayFetcher:
    """Client for fetching new listings from eBay via the Browse API."""

    SEARCH_ENDPOINT = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    ITEM_ENDPOINT = "https://api.ebay.com/buy/browse/v1/item"
    TOKEN_ENDPOINT = "https://api.ebay.com/identity/v1/oauth2/token"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()
        self._access_token: Optional[str] = None

    def _get_access_token(self) -> Optional[str]:
        """Obtain an OAuth access token using the client credentials flow.

        Returns ``None`` if client credentials are not configured.  The token
        is cached on the instance for reuse.
        """
        if self._access_token:
            return self._access_token

        client_id = self.settings.EBAY_CLIENT_ID
        client_secret = self.settings.EBAY_CLIENT_SECRET
        if not client_id or not client_secret:
            return None
        # Perform client credentials request
        try:
            response = self.session.post(
                self.TOKEN_ENDPOINT,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "client_credentials",
                    "scope": "https://api.ebay.com/oauth/api_scope",
                },
                auth=(client_id, client_secret),
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            self._access_token = data.get("access_token")
            return self._access_token
        except Exception as exc:
            logger.warning("Failed to obtain eBay access token: %s", exc)
            return None

    def _build_headers(self) -> Dict[str, str]:
        """Construct request headers for the Browse API."""
        headers: Dict[str, str] = {
            "User-Agent": "golf-flip-bot/1.0",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB",
        }
        # Use OAuth if available; otherwise pass AppID via header
        token = self._get_access_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        elif self.settings.EBAY_APP_ID:
            headers["X-EBAY-C-APP-ID"] = self.settings.EBAY_APP_ID
        return headers

    def fetch_listings(self, keywords: List[str], max_price: Optional[float] = None) -> List[Dict[str, Any]]:
        """Search the eBay Browse API for items matching the given keywords.

        Parameters
        ----------
        keywords: List[str]
            A list of search terms.  They will be combined with OR semantics.
        max_price: float, optional
            Maximum price filter.  Only items priced at or below this value
            (in the marketplace's default currency) will be returned.

        Returns
        -------
        List[Dict[str, Any]]
            A list of dictionaries containing simplified listing data.
        """
        # Do not attempt to fetch if no credentials are provided
        if not (self.settings.EBAY_APP_ID or (self.settings.EBAY_CLIENT_ID and self.settings.EBAY_CLIENT_SECRET)):
            logger.info("Skipping eBay fetch – no API credentials configured")
            return []

        query = "(" + ", ".join(keywords) + ")"
        params: Dict[str, Any] = {
            "q": query,
            "category_ids": "115280",  # Golf Clubs & Equipment
            "limit": "50",
            "sort": "newlyListed",
        }
        # Apply price filter if specified
        filters: List[str] = []
        if max_price is not None:
            filters.append(f"price:[..{max_price}]")
        # Only buy-it-now listings (fixed price)
        filters.append("buyingOptions:{FIXED_PRICE}")
        if filters:
            params["filter"] = " and ".join(filters)

        headers = self._build_headers()

        try:
            response = self.session.get(self.SEARCH_ENDPOINT, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.error("Error querying eBay API: %s", exc)
            return []

        items: List[Dict[str, Any]] = []
        for item in data.get("itemSummaries", []):
            try:
                listing = self._simplify_item(item)
                items.append(listing)
            except Exception as exc:
                logger.debug("Skipping item due to parse error: %s", exc)
        return items

    def _simplify_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant fields from a Browse API item summary."""
        price_info = item.get("price", {})
        shipping_options = item.get("shippingOptions", [])
        shipping_cost = None
        if shipping_options:
            # Grab the first available shipping cost
            shipping = shipping_options[0].get("shippingCost", {})
            shipping_cost = float(shipping.get("value")) if shipping.get("value") else None
        return {
            "marketplace": "ebay",
            "listing_id": item.get("itemId"),
            "title": item.get("title"),
            "url": item.get("itemWebUrl"),
            "brand": self._get_attribute(item, "Brand"),
            "model": self._get_attribute(item, "Model"),
            "condition": item.get("condition"),
            "price": float(price_info.get("value")) if price_info.get("value") else None,
            "currency": price_info.get("currency"),
            "shipping_cost": shipping_cost,
            "location": item.get("itemLocation", {}).get("postalCode"),
        }

    @staticmethod
    def _get_attribute(item: Dict[str, Any], name: str) -> Optional[str]:
        """Extract a specific item attribute from the item summary."""
        aspects = item.get("itemSpecifics", {}).get("nameValueList", [])
        for aspect in aspects:
            if aspect.get("name").lower() == name.lower():
                values = aspect.get("value", [])
                return values[0] if values else None
        return None
