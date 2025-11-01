"""
FastAPI application exposing health check and manual triggers.

The API provides endpoints for health monitoring and a dry-run route that
emits a sample notification using hard-coded test data.  The dry-run
endpoint facilitates local validation of formatting and cost logic
without contacting external services.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from .settings import get_settings, Settings
from .valuation import compute_profit
from .whatsapp import format_message, WhatsAppNotifier

app = FastAPI(title="Golf Flip Monitor")


@app.get("/health")
async def health() -> Dict[str, str]:
    """Return a simple health indicator."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/dry-run")
async def dry_run(settings: Settings = Depends(get_settings)) -> JSONResponse:
    """Perform a dry-run using hard coded sample listings.

    This endpoint demonstrates message formatting and cost calculations.
    It returns the message text and payload for the first profitable item.
    """
    samples: List[Dict[str, Any]] = [
        {
            "marketplace": "ebay",
            "listing_id": "dry1",
            "title": "Cobra King LTDx driver 9 deg with HC",
            "url": "https://example.com/item1",
            "brand": "Cobra",
            "model": "King LTDx",
            "condition": "excellent",
            "price": 80.0,
            "currency": "GBP",
            "shipping_cost": 4.0,
        },
        {
            "marketplace": "ebay",
            "listing_id": "dry2",
            "title": "Scotty Cameron Phantom X putter",
            "url": "https://example.com/item2",
            "brand": "Scotty Cameron",
            "model": "Phantom X",
            "condition": "very good",
            "price": 200.0,
            "currency": "GBP",
            "shipping_cost": 5.0,
        },
        {
            "marketplace": "vinted",
            "listing_id": "dry3",
            "title": "Junior set 7 piece",
            "url": "https://example.com/item3",
            "brand": None,
            "model": None,
            "condition": "good",
            "price": 35.0,
            "currency": "GBP",
            "shipping_cost": 4.0,
        },
    ]
    notifier = WhatsAppNotifier(settings)
    results = []
    for listing in samples:
        (
            product_cost,
            buyer_protection_cost,
            shipping_cost,
            total_cost,
            potential_resale_value,
            profit,
            margin_percent,
        ) = compute_profit(listing, settings)
        message = format_message(
            listing,
            (
                product_cost,
                buyer_protection_cost,
                shipping_cost,
                total_cost,
                potential_resale_value,
                profit,
                margin_percent,
            ),
            settings,
        )
        payload = {
            "marketplace": listing["marketplace"],
            "listing_id": listing["listing_id"],
            "title": listing["title"],
            "url": listing["url"],
            "brand": listing.get("brand"),
            "model": listing.get("model"),
            "condition": listing.get("condition"),
            "product_cost": product_cost,
            "buyer_protection_cost": buyer_protection_cost,
            "shipping_cost": shipping_cost,
            "total_cost": total_cost,
            "potential_resale_value": potential_resale_value,
            "profit": profit,
            "margin_percent": margin_percent,
            "currency": settings.CURRENCY,
            "timestamp_utc": datetime.utcnow().isoformat(),
        }
        results.append({"message": message, "payload": payload})
        # Only show the first profitable message example
        if profit >= settings.PROFIT_MIN and margin_percent >= settings.MARGIN_MIN_PERCENT:
            break
    # Return the first result or empty list if none
    if results:
        return JSONResponse(content=results[0])
    return JSONResponse(content={"message": "No profitable listings in dry run"})
