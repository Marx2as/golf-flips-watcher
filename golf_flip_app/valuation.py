"""
Pricing and valuation logic.

This module encapsulates the logic used to estimate the resale value of a
listing and compute associated costs.  Multiple strategies are provided
to allow flexibility in how resale values are determined.
"""

from __future__ import annotations

import json
import statistics
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from .settings import Settings


def compute_buyer_protection_cost(price: float, settings: Settings) -> float:
    """Compute the buyer protection cost.

    Some marketplaces charge a fee for buyer protection.  In lieu of
    marketplace-specific rules, this function applies a flat 5% fee as
    a fallback.  The percentage can be adjusted by setting
    ``BUYER_PROTECTION_PERCENT`` in the environment (not exposed via
    settings here for simplicity).

    Parameters
    ----------
    price: float
        The purchase price of the item.
    settings: Settings
        Application configuration (unused but included for future use).

    Returns
    -------
    float
        Buyer protection cost, rounded to two decimal places.
    """
    cost = price * 0.05
    return round(cost, 2)


def lookup_shipping_cost(listing: Dict[str, Any], settings: Settings) -> Optional[float]:
    """Determine the shipping cost for a listing.

    If the listing provides a shipping cost, return it.  Otherwise use
    the shipping lookup table configured via ``SHIPPING_TABLE_JSON``.

    Parameters
    ----------
    listing: dict
        Listing dictionary produced by a fetcher.
    settings: Settings
        Application configuration containing a JSON shipping table.

    Returns
    -------
    float or None
        Estimated shipping cost, or None if unavailable.
    """
    if listing.get("shipping_cost") is not None:
        return round(float(listing["shipping_cost"]), 2)
    if settings.SHIPPING_TABLE_JSON:
        try:
            table = json.loads(settings.SHIPPING_TABLE_JSON)
            # Use a generic default if provided
            return round(float(table.get("default", 0.0)), 2)
        except Exception:
            pass
    return None


def estimate_resale_value(listing: Dict[str, Any], settings: Settings) -> Optional[float]:
    """Estimate the resale value of an item using the selected strategy.

    Strategy A (``A``) takes a naive median of sold comparable prices.  In
    this reference implementation, historical comps are not fetched from
    eBay; instead, it returns ``price * 1.5`` as a proxy.  Strategy B
    (``B``) uses a static price table keyed by brand and model.  Strategy
    C (``C``) applies a heuristic multiplier (1.5x) to the purchase
    price.  Unknown strategies raise a ``ValueError``.

    Parameters
    ----------
    listing: dict
        Listing dictionary containing at least ``price``.
    settings: Settings
        Application configuration specifying the strategy to use.

    Returns
    -------
    float or None
        The estimated resale value, or None if it cannot be determined.
    """
    price = listing.get("price")
    if price is None:
        return None
    strategy = settings.VALUATION_STRATEGY.upper()
    if strategy == "A":
        # Placeholder: use multiplier; in a real implementation you
        # would query the Marketplace Insights API or search recent sold
        # items to compute a median.  Multiply by 1.5 as a proxy.
        return round(price * 1.5, 2)
    elif strategy == "B":
        # Static price table keyed by brand and model.  Example values
        # can be customised in the settings or replaced with a DB.
        key = f"{(listing.get('brand') or '').lower()}|{(listing.get('model') or '').lower()}"
        static_prices = {
            "cobra|king ltdx": 130.0,
            "scotty cameron|phantom x": 240.0,
        }
        return static_prices.get(key)
    elif strategy == "C":
        # Simple heuristic: price * 1.5
        return round(price * 1.5, 2)
    else:
        raise ValueError(f"Unknown valuation strategy: {strategy}")


def compute_profit(listing: Dict[str, Any], settings: Settings) -> Tuple[float, float, float, float, float]:
    """Calculate cost breakdown and profit for a listing.

    The returned tuple contains (product_cost, buyer_protection_cost,
    shipping_cost, total_cost, potential_resale_value, profit, margin_percent).

    Parameters
    ----------
    listing: dict
        Listing dictionary from fetcher.
    settings: Settings
        Application configuration.

    Returns
    -------
    tuple
        Tuple with cost breakdown and profit metrics.
    """
    product_cost = round(float(listing.get("price", 0.0)), 2)
    buyer_protection_cost = compute_buyer_protection_cost(product_cost, settings)
    shipping_cost = lookup_shipping_cost(listing, settings)
    total_cost = product_cost + buyer_protection_cost
    if shipping_cost is not None:
        total_cost += shipping_cost
    potential_resale_value = estimate_resale_value(listing, settings)
    if potential_resale_value is None:
        profit = 0.0
        margin_percent = 0.0
    else:
        profit = round(potential_resale_value - total_cost, 2)
        margin_percent = round((profit / total_cost) * 100, 2) if total_cost else 0.0
    return (
        round(product_cost, 2),
        round(buyer_protection_cost, 2),
        round(shipping_cost, 2) if shipping_cost is not None else 0.0,
        round(total_cost, 2),
        round(potential_resale_value, 2) if potential_resale_value is not None else 0.0,
        round(profit, 2),
        round(margin_percent, 2),
    )
