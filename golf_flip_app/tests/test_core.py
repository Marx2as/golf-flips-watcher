"""
Unit tests for cost and profit computation and message formatting.

These tests exercise the valuation logic and the notifier formatting
helpers to ensure values are calculated correctly and messages are
assembled as expected.
"""

from __future__ import annotations

import re

from golf_flip_app.settings import Settings
from golf_flip_app.valuation import compute_profit
from golf_flip_app.whatsapp import format_message


def test_compute_profit_heuristic() -> None:
    settings = Settings(PROFIT_MIN=10, MARGIN_MIN_PERCENT=20, VALUATION_STRATEGY="C")
    listing = {
        "price": 100.0,
        "shipping_cost": 5.0,
    }
    (
        product_cost,
        buyer_protection_cost,
        shipping_cost,
        total_cost,
        potential_resale_value,
        profit,
        margin_percent,
    ) = compute_profit(listing, settings)
    # Heuristic strategy multiplies price by 1.5
    assert potential_resale_value == 150.0
    assert product_cost == 100.0
    assert buyer_protection_cost == 5.0  # 5% of 100
    assert shipping_cost == 5.0
    assert total_cost == 110.0
    assert profit == 40.0
    assert margin_percent == 36.36


def test_format_message_structure() -> None:
    settings = Settings(CURRENCY="GBP", PROFIT_MIN=10)
    listing = {
        "title": "Test Club",
        "url": "http://example.com",
        "condition": "excellent",
    }
    breakdown = (100.0, 5.0, 5.0, 110.0, 150.0, 40.0, 36.36)
    message = format_message(listing, breakdown, settings)
    # Check key sections exist
    assert "Title: Test Club" in message
    assert "Link: http://example.com" in message
    assert "Condition: excellent" in message
    assert re.search(r"Product: £100.00", message)
    assert re.search(r"Profit: £40.00", message)
    # Should include looks good indicator
    assert "🟢" in message
